import json
import time
import pytest
from meltdown.models import CommandRequest, ConfirmationRequest, RetryRequest, TurnRequest
from meltdown.service import GameService
from tests.fakes import TestPolicy, expressed


def turn(service, game, actions, request_id=None):
    return service.advance(
        game["id"],
        TurnRequest(
            request_id=request_id or f"r{game['version']}", expected_version=game["version"], actions=actions
        ),
    )


def wait_service_phase(service, game_id, phase):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        game = service.get(game_id)
        if game["active_run"] and game["active_run"]["phase"] == phase:
            return game
        time.sleep(0.01)
    raise AssertionError(f"Game did not reach {phase}")


def test_rounds_are_bounded_and_time_advances_once(tmp_path):
    service = GameService(tmp_path / "game.sqlite")
    game = service.create()
    game = turn(service, game, ["audit", "prioritize_fix"])
    assert game["turn"] == 1
    assert 4 <= game["last_run"]["agent_calls"] <= 8
    assert game["last_run"]["rounds"] == 2
    assert any(row["round"] == 2 for row in game["last_run"]["steps"])
    service.close()


def test_retry_is_idempotent_and_conflicting_reuse_is_rejected(tmp_path):
    service = GameService(tmp_path / "game.sqlite")
    game = service.create()
    result = turn(service, game, ["audit"], "retry")
    assert turn(service, game, ["audit"], "retry") == result
    with pytest.raises(ValueError):
        turn(service, game, ["rest"], "retry")
    assert service.get(game["id"])["turn"] == 1
    service.close()


def test_sqlite_restart_preserves_game_and_interrupt(tmp_path):
    path = tmp_path / "game.sqlite"
    service = GameService(path)
    game = turn(service, service.create(), ["audit"])
    service.close()
    restarted = GameService(path)
    assert restarted.get(game["id"]) == game
    next_game = turn(restarted, game, ["prioritize_fix"])
    assert next_game["turn"] == 2
    restarted.close()


class BrokenPolicy(TestPolicy):
    def decide(self, context):
        raise TimeoutError("provider unavailable")


class ExpressiveAuditPolicy(TestPolicy):
    def decide(self, context):
        if context["actor"] == "security" and "audit" in context["allowed_actions"]:
            return expressed(
                "audit",
                speech="I found a critical export vulnerability; release must wait for a verified fix.",
                reason="The defect was unassessed and release safety was unknown.",
                emotion="urgent",
            )
        return super().decide(context)


class PrivateFactEchoPolicy(TestPolicy):
    def __init__(self):
        self.client_context = None

    def decide(self, context):
        if context["actor"] == "client" and "counter" in context["allowed_actions"]:
            self.client_context = context
            private_fact = context["facts"].get("demo_acceptable")
            if private_fact:
                return expressed(
                    "counter",
                    speech=private_fact,
                    reason=context.get("private_goal", "The proposal needs more evidence."),
                    fact_ids=["demo_acceptable"],
                )
            return expressed("counter", speech="I need stronger assurances before agreeing.")
        return super().decide(context)


def test_agent_expression_is_published_without_replacing_engine_facts(tmp_path):
    service = GameService(tmp_path / "expression.sqlite", policy=ExpressiveAuditPolicy())
    result = turn(service, service.create(), ["audit"])
    audit = next(
        event for event in result["events"] if event["type"] == "audit" and event["actor"] == "security"
    )

    assert audit["detail"].startswith("The audit confirms a critical vulnerability")
    assert audit["speech"].startswith("I found a critical export vulnerability")
    assert audit["reason"] == "The defect was unassessed and release safety was unknown."
    assert audit["emotion"] == "urgent"
    service.close()


def test_ordinary_agent_expression_cannot_read_or_disclose_private_context(tmp_path):
    policy = PrivateFactEchoPolicy()
    service = GameService(tmp_path / "private-expression.sqlite", policy=policy)

    result = turn(service, service.create(), ["request_delay"])
    counter = next(
        event for event in result["events"] if event["type"] == "counter" and event["actor"] == "client"
    )

    assert "private_goal" not in policy.client_context
    assert "demo_acceptable" not in policy.client_context["facts"]
    assert "reduced scope" not in counter["speech"].lower()
    assert "demonstration to management" not in json.dumps(result).lower()
    service.close()


def test_failed_agent_does_not_fabricate_a_rules_response(tmp_path):
    service = GameService(tmp_path / "game.sqlite", policy=BrokenPolicy())
    game = service.create()
    with pytest.raises(TimeoutError, match="provider unavailable"):
        turn(service, game, ["audit"])
    assert service.get(game["id"])["turn"] == 0
    service.close()


class FailOncePolicy(TestPolicy):
    def __init__(self):
        self.failed = False

    def decide(self, context):
        if context["actor"] == "security" and not self.failed:
            self.failed = True
            raise TimeoutError("temporary provider failure")
        return super().decide(context)


def test_failed_async_agent_round_resumes_with_the_llm_on_explicit_retry(tmp_path):
    service = GameService(tmp_path / "agent-retry.sqlite", policy=FailOncePolicy())
    game = service.create()
    accepted = service.start_turn(
        game["id"],
        CommandRequest(request_id="agent-retry", expected_version=0, command="Audit the defect"),
    )
    failed = wait_service_phase(service, game["id"], "failed")

    assert failed["turn"] == 0
    service.retry(
        game["id"],
        accepted["active_run"]["id"],
        RetryRequest(request_id="retry-agent-round"),
    )
    completed = wait_service_phase(service, game["id"], "complete")

    assert completed["turn"] == 1
    assert any(event["actor"] == "security" and event["type"] == "audit" for event in completed["events"])
    service.close()


def test_two_strategies_finish_differently_and_debrief_cites_real_events(tmp_path):
    service = GameService(tmp_path / "game.sqlite")
    safe = service.create()
    for actions in [
        ["audit", "prioritize_fix"],
        ["clarify", "communicate"],
        ["reduce_scope", "rest"],
        [],
        [],
        ["release"],
    ]:
        safe = turn(service, safe, actions)
    neglected = service.create()
    for _ in range(6):
        neglected = turn(service, neglected, [])
    assert safe["status"] == neglected["status"] == "finished"
    assert safe["outcome"]["code"] == "delivered"
    assert neglected["outcome"]["code"] != "delivered"
    ids = {event["id"] for event in safe["events"]}
    assert safe["debrief"]["moments"]
    assert all(set(moment["event_ids"]) <= ids for moment in safe["debrief"]["moments"])
    assert "private_goal" not in json.dumps(safe)
    service.close()


def test_delivery_cannot_be_combined_with_an_unfinished_scope_expansion(tmp_path):
    service = GameService(tmp_path / "scope.sqlite")
    game = service.create()
    for actions in [
        ["audit", "prioritize_fix"],
        ["clarify", "communicate"],
        ["reduce_scope", "rest"],
        [],
        [],
    ]:
        game = turn(service, game, actions)
    with pytest.raises(ValueError):
        turn(service, game, ["release", "accept_feature"])
    assert service.get(game["id"])["version"] == 5
    service.close()


def test_delivery_finishes_without_new_agent_activations(tmp_path):
    service = GameService(tmp_path / "terminal.sqlite")
    game = service.create()
    for actions in [
        ["audit", "prioritize_fix"],
        ["clarify", "communicate"],
        ["reduce_scope", "rest"],
        [],
        [],
    ]:
        game = turn(service, game, actions)
    result = turn(service, game, ["release"])
    assert result["status"] == "finished"
    assert result["last_run"]["agent_calls"] == 0
    assert result["last_run"]["rounds"] == 0
    service.close()


class RepeatingDisclosurePolicy(TestPolicy):
    def decide(self, context):
        if context["actor"] == "client" and "reveal_need" in context["allowed_actions"]:
            return expressed("reveal_need")
        if context["actor"] == "sales":
            return expressed("clarify_promise")
        return super().decide(context)


def test_second_round_cannot_reward_an_already_disclosed_fact(tmp_path):
    service = GameService(tmp_path / "disclosure.sqlite", policy=RepeatingDisclosurePolicy())
    game = turn(service, service.create(), ["clarify"])
    assert game["last_run"]["rounds"] == 2
    assert game["metrics"]["trust"] == 62
    assert len([e for e in game["events"] if e["type"] == "reveal_need"]) == 1
    service.close()


def test_public_game_has_no_non_llm_mode_switch(tmp_path):
    service = GameService(tmp_path / "mode.sqlite")
    game = service.create()
    assert "mode" not in game
    service.close()


def test_resume_after_commit_failure_keeps_receipt_and_next_turn(tmp_path, monkeypatch):
    path = tmp_path / "recovery.sqlite"
    service = GameService(path)
    game = service.create()
    original_commit = service.store.commit

    def commit_then_fail(state, request):
        original_commit(state, request)
        raise RuntimeError("simulated crash after canonical commit")

    monkeypatch.setattr(service.store, "commit", commit_then_fail)
    with pytest.raises(RuntimeError):
        turn(service, game, ["audit"], "recover")
    service.close()
    restarted = GameService(path)
    recovered = turn(restarted, game, ["audit"], "recover")
    assert recovered["turn"] == 1
    assert turn(restarted, recovered, ["prioritize_fix"])["turn"] == 2
    restarted.close()


def test_agent_cannot_transmit_another_characters_private_fact(tmp_path):
    class FabricatedDisclosure(TestPolicy):
        def decide(self, context):
            if context["actor"] == "developer":
                return expressed(
                    "message",
                    recipient="client",
                    speech="unauthorized-disclosure",
                    fact_ids=["demo_acceptable"],
                )
            return super().decide(context)

    service = GameService(tmp_path / "private.sqlite", policy=FabricatedDisclosure())
    with pytest.raises(ValueError, match="knowledge"):
        turn(service, service.create(), [])
    service.close()


def test_graph_pauses_for_collected_questions_then_resumes_once(tmp_path):
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command
    import sqlite3

    from meltdown.graph import build_graph
    from meltdown.scenario import new_game
    from meltdown.store import Store

    class QuestionPolicy(TestPolicy):
        def decide(self, context):
            if context["actor"] == "client" and "ask_player" in context["allowed_actions"]:
                return expressed(
                    "ask_player",
                    speech="I need the proposed demonstration scope.",
                    reason="The offer is not concrete enough to accept.",
                    question="What will the smaller demo contain?",
                    question_reason="I need scope clarity.",
                )
            return super().decide(context)

    store = Store(tmp_path / "question-graph.sqlite")
    checkpoint = sqlite3.connect(tmp_path / "question-checkpoint.sqlite", check_same_thread=False)
    graph = build_graph(store, QuestionPolicy(), SqliteSaver(checkpoint))
    game = new_game("question-game")
    game["player_knowledge"].append("demo_acceptable")
    store.create(game)
    config = {"configurable": {"thread_id": game["id"]}, "recursion_limit": 50}
    graph.invoke(
        {"game": game, "packets": {}, "request": {}, "round": 0, "dispatch": [], "started_at": 0},
        config,
    )

    graph.invoke(
        Command(
            resume={
                "request_id": "question-turn",
                "expected_version": 0,
                "actions": ["reduce_scope"],
            }
        ),
        config,
    )
    paused = graph.get_state(config)

    assert paused.next == ("await_answers",)
    assert store.load(game["id"])["turn"] == 0
    question = paused.values["game"]["pending_questions"][0]

    graph.invoke(
        Command(
            resume={
                "request_id": "question-answer",
                "answers": [{"question_id": question["id"], "text": "The secure core workflow."}],
            }
        ),
        config,
    )

    assert store.load(game["id"])["turn"] == 1
    assert store.load(game["id"])["version"] == 1
    checkpoint.close()
    store.close()


def test_ambiguous_async_run_survives_service_restart(tmp_path):
    path = tmp_path / "restart-run.sqlite"
    service = GameService(path)
    game = service.create()
    accepted = service.start_turn(
        game["id"],
        CommandRequest(request_id="ambiguous", expected_version=0, command="Handle it"),
    )
    waiting = wait_service_phase(service, game["id"], "needs_confirmation")
    assert waiting["active_run"]["id"] == accepted["active_run"]["id"]
    service.close()

    restarted = GameService(path)
    waiting = restarted.get(game["id"])
    assert waiting["active_run"]["phase"] == "needs_confirmation"
    restarted.confirm(
        game["id"],
        waiting["active_run"]["id"],
        ConfirmationRequest(request_id="replace", command="Audit the defect"),
    )
    assert wait_service_phase(restarted, game["id"], "complete")["turn"] == 1
    restarted.close()
