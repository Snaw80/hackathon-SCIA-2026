from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sqlite3
import threading
from uuid import uuid4
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from .agents import configured_policy
from .engine import prepare_turn
from .graph import build_graph
from .interpreter import interpret_command
from .models import AnswerRequest, ConfirmationRequest, RetryRequest
from .projection import public_run, public_view
from .scenario import new_game
from .store import Store, fingerprint


class GameService:
    """Single-process local service; serialize mutations including model rounds."""

    def __init__(self, db_path, policy=None):
        self.store = Store(db_path)
        self.policy = policy if policy is not None else configured_policy()
        self.checkpoint_conn = sqlite3.connect(
            str(Path(db_path).with_suffix(".checkpoints.sqlite")), check_same_thread=False, timeout=30
        )
        self.graph = build_graph(self.store, self.policy, SqliteSaver(self.checkpoint_conn))
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="meltdown-turn")
        self.scheduled = set()

    def config(self, game_id):
        return {"configurable": {"thread_id": game_id}, "recursion_limit": 50}

    def create(self):
        with self.lock:
            game = new_game(str(uuid4()))
            self.store.create(game)
            self.graph.invoke(
                {"game": game, "packets": {}, "request": {}, "round": 0, "dispatch": [], "started_at": 0},
                self.config(game["id"]),
            )
            return self._view(game)

    def get(self, game_id):
        return self._view(self.store.load(game_id))

    def _view(self, game):
        result = public_view(game)
        result["active_run"] = public_run(self.store.latest_run(game["id"]))
        return result

    def _schedule(self, run_id):
        with self.lock:
            if run_id in self.scheduled:
                return
            self.scheduled.add(run_id)
        future = self.executor.submit(self._execute_run, run_id)
        future.add_done_callback(lambda _: self._unschedule(run_id))

    def _unschedule(self, run_id):
        with self.lock:
            self.scheduled.discard(run_id)

    def start_turn(self, game_id, request):
        data = request.model_dump()
        with self.lock:
            game = self.store.load(game_id)
            if self.store.run_for_request(game_id, data):
                return self._view(game)
            latest = self.store.latest_run(game_id)
            if latest and latest["phase"] != "complete":
                raise ValueError("This game already has an active round.")
            if game["version"] != request.expected_version:
                raise ValueError("This game has advanced. The latest version has been reloaded.")
            if game["status"] != "active":
                raise ValueError("This game is over.")
            run = self.store.create_run(
                {
                    "id": str(uuid4()),
                    "game_id": game_id,
                    "request": data,
                    "phase": "interpreting",
                    "resume_phase": "interpreting",
                    "command": request.command,
                    "interpretation": None,
                    "active_agents": [],
                    "progress": [],
                    "questions": [],
                    "answers": None,
                    "boundary_requests": {},
                    "error": None,
                },
                data,
            )
            response = self._view(game)
            response["active_run"] = public_run(run)
        self._schedule(run["id"])
        return response

    def confirm(self, game_id, run_id, request: ConfirmationRequest):
        with self.lock:
            run = self.store.load_run(run_id)
            if run["game_id"] != game_id:
                raise KeyError(run_id)
            data = request.model_dump()
            if self._boundary_duplicate(run, data):
                return self._view(self.store.load(game_id))
            if run["phase"] != "needs_confirmation":
                raise ValueError("This round is not waiting for command confirmation.")
            if request.command:
                run["command"] = request.command
                run["interpretation"] = None
                run["phase"] = "interpreting"
                run["resume_phase"] = "interpreting"
            else:
                if not run["interpretation"] or not run["interpretation"]["actions"]:
                    raise ValueError("Edit the instruction so it maps to a valid project decision.")
                run["interpretation"]["confidence"] = "clear"
                run["phase"] = "round_active"
                run["resume_phase"] = "round_active"
            run["error"] = None
            self._remember_boundary(run, data)
            run = self.store.save_run(run)
            response = self._view(self.store.load(game_id))
            response["active_run"] = public_run(run)
        self._schedule(run_id)
        return response

    def answer(self, game_id, run_id, request: AnswerRequest):
        with self.lock:
            run = self.store.load_run(run_id)
            if run["game_id"] != game_id:
                raise KeyError(run_id)
            data = request.model_dump()
            if self._boundary_duplicate(run, data):
                return self._view(self.store.load(game_id))
            if run["phase"] != "awaiting_answers":
                raise ValueError("This round is not waiting for agent answers.")
            pending_ids = {question["id"] for question in run["questions"]}
            supplied_ids = {answer.question_id for answer in request.answers}
            if supplied_ids != pending_ids:
                raise ValueError("Submit one answer for every pending agent question.")
            run["answers"] = request.model_dump()
            run["phase"] = "resolving"
            run["resume_phase"] = "resolving"
            run["error"] = None
            self._remember_boundary(run, data)
            run = self.store.save_run(run)
            response = self._view(self.store.load(game_id))
            response["active_run"] = public_run(run)
        self._schedule(run_id)
        return response

    def retry(self, game_id, run_id, request: RetryRequest):
        with self.lock:
            run = self.store.load_run(run_id)
            if run["game_id"] != game_id:
                raise KeyError(run_id)
            data = request.model_dump()
            if self._boundary_duplicate(run, data):
                return self._view(self.store.load(game_id))
            if run["phase"] != "failed":
                raise ValueError("Only a failed round can be retried.")
            run["phase"] = run["resume_phase"]
            run["error"] = None
            self._remember_boundary(run, data)
            run = self.store.save_run(run)
            response = self._view(self.store.load(game_id))
            response["active_run"] = public_run(run)
        self._schedule(run_id)
        return response

    def _boundary_duplicate(self, run, data):
        previous = run.get("boundary_requests", {}).get(data["request_id"])
        if previous is None:
            return False
        if previous != fingerprint(data):
            raise ValueError("This request ID has already been used for another round response.")
        return True

    def _remember_boundary(self, run, data):
        run.setdefault("boundary_requests", {})[data["request_id"]] = fingerprint(data)

    def _save_progress(self, run, label, *, phase=None, active_agents=None):
        run = deepcopy(run)
        if phase:
            run["phase"] = phase
            run["resume_phase"] = phase
        if active_agents is not None:
            run["active_agents"] = active_agents
        run["progress"].append({"label": label, "status": "complete"})
        return self.store.save_run(run)

    def _execute_run(self, run_id):
        run = self.store.load_run(run_id)
        try:
            game = self.store.load(run["game_id"])
            if run["phase"] == "interpreting":
                interpretation = interpret_command(game, run["command"], self.policy)
                run["interpretation"] = interpretation.model_dump()
                run = self._save_progress(run, "Command interpreted")
                if interpretation.confidence == "ambiguous":
                    run["phase"] = "needs_confirmation"
                    run["resume_phase"] = "interpreting"
                    self.store.save_run(run)
                    return
                run["phase"] = "round_active"
                run["resume_phase"] = "round_active"
            if run["phase"] == "round_active":
                actions = run["interpretation"]["actions"]
                turn_request = {
                    "request_id": run["request"]["request_id"],
                    "expected_version": run["request"]["expected_version"],
                    "actions": actions,
                    "command": run["command"],
                    "interpretation": run["interpretation"]["summary"],
                }
                run = self._save_progress(
                    run,
                    "Agents are responding",
                    phase="round_active",
                    active_agents=["developer", "client", "sales", "security"],
                )
                self.graph.invoke(Command(resume=turn_request), self.config(run["game_id"]))
            elif run["phase"] == "resolving":
                run = self._save_progress(
                    run,
                    "Player answers delivered",
                    phase="resolving",
                    active_agents=[question["actor"] for question in run["questions"]],
                )
                self.graph.invoke(Command(resume=run["answers"]), self.config(run["game_id"]))
            canonical_request = {
                "request_id": run["request"]["request_id"],
                "expected_version": run["request"]["expected_version"],
                "actions": run["interpretation"]["actions"],
                "command": run["command"],
                "interpretation": run["interpretation"]["summary"],
            }
            if self.store.receipt(run["game_id"], canonical_request) is not None:
                run = self._save_progress(run, "Round complete", phase="complete", active_agents=[])
                run["questions"] = []
                self.store.save_run(run)
                return
            snapshot = self.graph.get_state(self.config(run["game_id"]))
            questions = deepcopy(snapshot.values["game"].get("pending_questions", []))
            if questions:
                run["phase"] = "awaiting_answers"
                run["resume_phase"] = "resolving"
                run["questions"] = questions
                run["active_agents"] = []
                run["progress"].append({"label": "Agent questions collected", "status": "complete"})
                self.store.save_run(run)
                return
            raise RuntimeError("Round stopped without a completion or player-input boundary.")
        except Exception as exc:
            run = self.store.load_run(run_id)
            run["phase"] = "failed"
            run["error"] = "The round stopped before completion. Retry to resume safely."
            run["internal_error"] = type(exc).__name__
            self.store.save_run(run)

    def advance(self, game_id, request):
        with self.lock:
            current = self.store.load(game_id)
            data = request.model_dump()
            if (receipt := self.store.receipt(game_id, data)) is not None:
                receipt["active_run"] = public_run(self.store.latest_run(game_id))
                return receipt
            config = self.config(game_id)
            snapshot = self.graph.get_state(config)
            # Resume interrupted infrastructure work before accepting a new decision.
            waiting = any(task.interrupts for task in snapshot.tasks)
            if snapshot.next and not waiting:
                self.graph.invoke(None, config)
                current = self.store.load(game_id)
                if (receipt := self.store.receipt(game_id, data)) is not None:
                    receipt["active_run"] = public_run(self.store.latest_run(game_id))
                    return receipt
            prepare_turn(current, request)  # Validate before consuming the human interrupt.
            self.graph.invoke(Command(resume=data), config)
            result = self.store.receipt(game_id, data)
            if result is None:
                raise RuntimeError("Turn did not produce a committed result")
            result["active_run"] = public_run(self.store.latest_run(game_id))
            return result

    def close(self):
        self.executor.shutdown(wait=True, cancel_futures=False)
        self.store.close()
        self.checkpoint_conn.close()
