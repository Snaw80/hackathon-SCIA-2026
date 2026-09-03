import copy
import pytest
from pydantic import ValidationError
from meltdown.models import TurnRequest
from meltdown.scenario import new_game, observation
from meltdown.engine import prepare_turn, finalize_turn
from meltdown.projection import public_view


def test_rejects_more_than_two_management_actions():
    with pytest.raises(ValidationError):
        TurnRequest(request_id="r", expected_version=0, actions=["audit", "clarify", "rest"])


def test_private_client_fact_never_enters_developer_context_or_public_snapshot():
    game = new_game("test")
    developer = observation(game, "developer", 1)
    assert "demo_acceptable" not in str(developer)
    assert "demo_acceptable" not in str(public_view(game))
    assert "demo_acceptable" in str(observation(game, "client", 1))


def test_invalid_action_does_not_mutate_committed_game():
    game = new_game("test")
    before = copy.deepcopy(game)
    with pytest.raises(ValueError):
        prepare_turn(game, TurnRequest(request_id="r", expected_version=0, actions=["release"]))
    assert game == before


def test_finalize_advances_one_period_and_work_once():
    game = new_game("test")
    game = prepare_turn(game, TurnRequest(request_id="r", expected_version=0, actions=["prioritize_fix"]))
    finished = finalize_turn(game)
    assert finished["turn"] == 1
    assert finished["version"] == 1
    assert finished["tasks"]["fix"]["remaining"] == 1
    assert finished["metrics"]["budget"] == 88
