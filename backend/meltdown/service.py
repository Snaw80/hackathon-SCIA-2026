from pathlib import Path
import sqlite3
import threading
from uuid import uuid4
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from .agents import configured_policy
from .engine import prepare_turn
from .graph import build_graph
from .projection import public_view
from .scenario import new_game
from .store import Store


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

    def config(self, game_id):
        return {"configurable": {"thread_id": game_id}, "recursion_limit": 50}

    def create(self):
        with self.lock:
            game = new_game(str(uuid4()), self.policy.mode)
            self.store.create(game)
            self.graph.invoke(
                {"game": game, "packets": {}, "request": {}, "round": 0, "dispatch": [], "started_at": 0},
                self.config(game["id"]),
            )
            return public_view(game)

    def get(self, game_id):
        with self.lock:
            return public_view(self.store.load(game_id))

    def advance(self, game_id, request):
        with self.lock:
            current = self.store.load(game_id)
            data = request.model_dump()
            if (receipt := self.store.receipt(game_id, data)) is not None:
                return receipt
            if current["mode"] != self.policy.mode:
                raise ValueError(
                    "Le mode des agents a changé. Démarrez une nouvelle partie pour utiliser ce mode."
                )
            config = self.config(game_id)
            snapshot = self.graph.get_state(config)
            # Resume interrupted infrastructure work before accepting a new decision.
            waiting = any(task.interrupts for task in snapshot.tasks)
            if snapshot.next and not waiting:
                self.graph.invoke(None, config)
                current = self.store.load(game_id)
                if (receipt := self.store.receipt(game_id, data)) is not None:
                    return receipt
            prepare_turn(current, request)  # Validate before consuming the human interrupt.
            self.graph.invoke(Command(resume=data), config)
            result = self.store.receipt(game_id, data)
            if result is None:
                raise RuntimeError("Turn did not produce a committed result")
            return result

    def close(self):
        self.store.close()
        self.checkpoint_conn.close()
