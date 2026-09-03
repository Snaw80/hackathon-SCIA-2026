import json
import pytest
from meltdown.models import TurnRequest
from meltdown.service import GameService
from meltdown.agents import RulesPolicy


def turn(service, game, actions, request_id=None):
    return service.advance(game["id"], TurnRequest(request_id=request_id or f"r{game['version']}", expected_version=game["version"], actions=actions))


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
    for actions in [["audit", "prioritize_fix"], ["clarify", "communicate"], ["reduce_scope", "rest"], [], [], ["release"]]:
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
