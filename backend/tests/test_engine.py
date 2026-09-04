import copy
import pytest
from pydantic import ValidationError
from meltdown.models import AnswerRequest, TurnRequest
from meltdown.scenario import new_game, observation
from meltdown.engine import apply_player_answers, prepare_turn, finalize_turn
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


def test_same_work_suspension_does_not_apply_morale_penalty_twice():
    from meltdown.engine import resolve_intents

    game = new_game("test")
    game["agents"]["developer"]["stress"] = 90
    packet = {"developer": {"intent": {"action": "refuse"}, "causes": []}}
    first = resolve_intents(game, packet, 1)
    second = resolve_intents(first, packet, 2)
    assert first["work_blocked"]
    assert second["metrics"]["morale"] == first["metrics"]["morale"]


def test_audit_does_not_attribute_its_result_to_an_unrelated_client_decision():
    from meltdown.engine import resolve_intents

    game = prepare_turn(
        new_game("test"), TurnRequest(request_id="causes", expected_version=0, actions=["audit", "clarify"])
    )
    audit_id = next(e["id"] for e in game["events"] if e["actor"] == "player" and e["type"] == "audit")
    result = resolve_intents(game, {"security": {"intent": {"action": "audit"}, "causes": []}}, 1)
    audit_result = next(e for e in result["events"] if e["actor"] == "security" and e["type"] == "audit")
    assert audit_result["causes"] == [audit_id]


def test_question_intent_is_collected_once_at_the_round_boundary():
    from meltdown.engine import resolve_intents

    game = new_game("questions")
    game["actions"] = ["reduce_scope"]
    game["proposals"] = ["reduce_scope"]
    packet = {
        "client": {
            "intent": {
                "action": "ask_player",
                "question": "What proof can you share for the smaller demo?",
                "question_reason": "I need enough assurance to agree to the scope.",
            },
            "causes": [],
        }
    }

    first = resolve_intents(game, packet, 1)
    second = resolve_intents(first, packet, 1)

    assert len(second["pending_questions"]) == 1
    assert second["pending_questions"][0]["actor"] == "client"
    assert second["pending_questions"][0]["question"].startswith("What proof")


def test_player_answers_are_delivered_only_to_requesting_agents():
    game = new_game("answers")
    game["pending_questions"] = [
        {
            "id": "q-client",
            "actor": "client",
            "question": "What will the demo contain?",
            "reason": "I need scope clarity.",
            "turn": 1,
            "round": 1,
        }
    ]

    resumed, dispatch = apply_player_answers(
        game,
        AnswerRequest(
            request_id="answer-1",
            answers=[{"question_id": "q-client", "text": "The secure core workflow."}],
        ),
        round_number=2,
    )

    assert [item["context"]["actor"] for item in dispatch] == ["client"]
    assert dispatch[0]["context"]["inbox"][0]["text"] == "The secure core workflow."
    assert "ask_player" not in dispatch[0]["context"]["allowed_actions"]
    assert resumed["pending_questions"] == []
    assert resumed["answer_followup"] is True
    assert resumed["events"][-1]["type"] == "player_answer"
