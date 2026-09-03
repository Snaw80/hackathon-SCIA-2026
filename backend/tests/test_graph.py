import json
import pytest
from meltdown.models import TurnRequest
from meltdown.service import GameService
from meltdown.agents import RulesPolicy


def turn(service, game, actions, request_id=None):
    return service.advance(
        game["id"],
        TurnRequest(
            request_id=request_id or f"r{game['version']}", expected_version=game["version"], actions=actions
        ),
    )


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


class BrokenPolicy(RulesPolicy):
    def decide(self, context):
        raise TimeoutError("provider unavailable")


def test_failed_agent_uses_visible_fallback_without_losing_turn(tmp_path):
    service = GameService(tmp_path / "game.sqlite", policy=BrokenPolicy())
    game = turn(service, service.create(), ["audit"])
    assert game["turn"] == 1
    assert game["last_run"]["fallbacks"] >= 4
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


class RepeatingDisclosurePolicy(RulesPolicy):
    def decide(self, context):
        from meltdown.models import AgentIntent

        if context["actor"] == "client" and "reveal_need" in context["allowed_actions"]:
            return AgentIntent(action="reveal_need")
        if context["actor"] == "sales":
            return AgentIntent(action="clarify_promise")
        return super().decide(context)


def test_second_round_cannot_reward_an_already_disclosed_fact(tmp_path):
    service = GameService(tmp_path / "disclosure.sqlite", policy=RepeatingDisclosurePolicy())
    game = turn(service, service.create(), ["clarify"])
    assert game["last_run"]["rounds"] == 2
    assert game["metrics"]["trust"] == 62
    assert len([e for e in game["events"] if e["type"] == "reveal_need"]) == 1
    service.close()


def test_game_cannot_silently_switch_agent_mode_on_restart(tmp_path):
    class AnotherMode(RulesPolicy):
        mode = "llm"

    path = tmp_path / "mode.sqlite"
    service = GameService(path)
    game = service.create()
    service.close()
    restarted = GameService(path, policy=AnotherMode())
    with pytest.raises(ValueError, match="mode"):
        turn(restarted, game, [])
    assert restarted.get(game["id"])["turn"] == 0
    restarted.close()


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
    class FabricatedDisclosure(RulesPolicy):
        def decide(self, context):
            from meltdown.models import AgentIntent

            if context["actor"] == "developer":
                return AgentIntent(
                    action="message",
                    recipient="client",
                    message="unauthorized-disclosure",
                    fact_ids=["demo_acceptable"],
                )
            return super().decide(context)

    service = GameService(tmp_path / "private.sqlite", policy=FabricatedDisclosure())
    result = turn(service, service.create(), [])
    assert result["last_run"]["fallbacks"] == 1
    assert "unauthorized-disclosure" not in json.dumps(result)
    service.close()
