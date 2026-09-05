import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from meltdown.agents import LangChainPolicy
from meltdown.models import AgentIntent
from meltdown.projection import build_debrief
from meltdown.scenario import new_game


class ScriptedModel:
    """Replace only the external structured-model boundary."""

    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []

    def with_structured_output(self, schema, **kwargs):
        def invoke(messages):
            self.messages.append(deepcopy(messages))
            response = next(self.responses)
            if isinstance(response, Exception):
                raise response
            try:
                parsed, error = schema.model_validate(response), None
            except ValueError as exc:
                parsed, error = None, exc
            return {
                "raw": SimpleNamespace(usage_metadata={"input_tokens": 100, "output_tokens": 30}),
                "parsed": parsed,
                "parsing_error": error,
            }

        return SimpleNamespace(invoke=invoke)


def make_policy(monkeypatch, responses):
    model = ScriptedModel(responses)
    monkeypatch.setattr("langchain.chat_models.init_chat_model", lambda *a, **k: model)
    records = []
    return LangChainPolicy("openai:gpt-5.4-nano", on_result=records.append), model, records


@pytest.mark.parametrize("invalid", [
    {"action": "audit"},  # Missing required expression.
    {"action": "invented", "speech": "Proceed.", "reason": "Ready."},
    {"action": "wait", "fact_ids": ["private-fact"]},
    {"action": "message", "recipient": "client", "speech": "Hello.", "reason": "Update."},
])
def test_invalid_decision_is_corrected_once_and_both_calls_are_metered(monkeypatch, invalid):
    policy, model, records = make_policy(monkeypatch, [invalid, {"action": "wait"}])
    result = policy.decide({"actor": "client", "allowed_actions": ["wait", "message"], "facts": {}})
    assert result == AgentIntent(action="wait")
    assert len(model.messages) == len(records) == 2
    assert model.messages[0] != model.messages[1]
    assert sum(record["usage"]["output_tokens"] for record in records) == 60


def test_second_invalid_decision_still_fails_without_a_third_call(monkeypatch):
    policy, model, _ = make_policy(monkeypatch, [{"action": "audit"}] * 3)
    with pytest.raises(ValueError):
        policy.decide({"allowed_actions": ["audit"], "facts": {}})
    assert len(model.messages) == 2


@pytest.mark.parametrize("error", [TimeoutError("provider unavailable"), ValueError("provider config")])
def test_provider_failures_do_not_trigger_output_correction(monkeypatch, error):
    policy, model, _ = make_policy(monkeypatch, [error, {"action": "wait"}])
    with pytest.raises(type(error), match=str(error)):
        policy.decide({"allowed_actions": ["wait"], "facts": {}})
    assert len(model.messages) == 1


def test_interpreter_receives_bounded_public_context_without_private_state(monkeypatch):
    policy, model, _ = make_policy(monkeypatch, [
        {"summary": "Continue", "actions": [], "confidence": "clear"},
    ])
    game = new_game("context")
    template = game["events"][0]
    game["events"] = [
        {**template, "id": f"public-{i}", "title": f"Update {i}"} for i in range(12)
    ] + [{**template, "id": "secret-event", "title": "SECRET", "audience": ["client"]}]
    before = deepcopy(game)
    policy.interpret(game, "Continue with that")
    payload = json.loads(model.messages[0][-1][1])
    state = payload["game_state"]
    assert state["turn"] == 0
    assert state["security"]["status"] == "unknown"
    assert state["metrics"]["budget"] == 100
    assert [event["id"] for event in state["recent_events"]] == [f"public-{i}" for i in range(4, 12)]
    serialized = json.dumps(payload)
    assert "SECRET" not in serialized and "private_goal" not in serialized
    assert "demo_acceptable" not in serialized
    assert "fix" not in [task["id"] for task in state["tasks"]]
    assert game == before


def test_interpreter_corrects_an_unavailable_action_before_starting_a_turn(monkeypatch):
    policy, model, _ = make_policy(monkeypatch, [
        {"summary": "Release now", "actions": ["release"], "confidence": "clear"},
        {"summary": "The audit succeeded", "actions": ["audit"], "confidence": "clear"},
    ])
    game = new_game("command-repair")
    result = policy.interpret(game, "Investigate the defect")
    assert result.actions == ["audit"]
    assert result.summary == "Selected decision: Audit the defect."
    assert len(model.messages) == 2
    assert game["turn"] == 0


def test_coach_can_choose_late_events_and_repeated_event_types(monkeypatch):
    game = new_game("debrief")
    game["outcome"] = {"title": "Finished"}
    template = game["events"][0]
    game["events"] = [
        {**template, "id": f"e{i}", "type": kind, "title": f"Moment {i}", "causes": []}
        for i, kind in enumerate(["audit", "accept_scope", "accept_delay", "refuse", "refuse"])
    ]
    game["events"].append({**template, "id": "private", "type": "refuse", "audience": ["client"]})
    policy, model, _ = make_policy(monkeypatch, [
        {"event_ids": ["missing"]}, {"event_ids": ["e4", "e3", "e0"]},
    ])
    result = policy.coach(build_debrief(game, all_moments=True))
    assert [m["event_ids"][-1] for m in result["moments"]] == ["e4", "e3", "e0"]
    assert result["moments"][0]["title"] == "Moment 4"
    candidates = json.loads(model.messages[0][-1][1])
    assert len(candidates) == 5
    assert len(build_debrief(game)["moments"]) == 3


def test_coach_rejects_duplicate_references_after_one_correction(monkeypatch):
    policy, model, _ = make_policy(monkeypatch, [{"event_ids": ["e1", "e1"]}] * 3)
    debrief = {"moments": [{"event_ids": ["e1"], "title": "Fact", "analysis": "Recorded"}]}
    with pytest.raises(ValueError, match="references"):
        policy.coach(debrief)
    assert len(model.messages) == 2


def test_corrected_agent_response_completes_one_turn_without_duplicate_costs(monkeypatch, tmp_path):
    from meltdown.models import TurnRequest
    from meltdown.service import GameService

    policy, model, records = make_policy(monkeypatch, [{"action": "audit"}] + [{"action": "wait"}] * 4)
    service = GameService(tmp_path / "correction.sqlite", policy=policy)
    try:
        game = service.create()
        request = TurnRequest(request_id="one-turn", expected_version=0, actions=[])
        result = service.advance(game["id"], request)
        assert result["turn"] == 1
        assert result["metrics"]["budget"] == 88
        assert result["last_run"]["agent_calls"] == 4
        assert len(model.messages) == len(records) == 5
        assert service.advance(game["id"], request) == result
        assert len(model.messages) == 5
    finally:
        service.close()


def test_finished_game_sends_all_eligible_events_to_coach(tmp_path):
    from meltdown.models import TurnRequest
    from meltdown.service import GameService
    from tests.fakes import TestPolicy

    class SelectingPolicy(TestPolicy):
        def coach(self, debrief):
            self.candidates = debrief["moments"]
            return {**debrief, "moments": self.candidates[-3:], "source": "llm"}

    policy = SelectingPolicy()
    service = GameService(tmp_path / "all-moments.sqlite", policy=policy)
    try:
        game = service.create()
        for actions in [
            ["audit", "prioritize_fix"], ["clarify", "communicate"],
            ["reduce_scope", "rest"], [], [], ["release"],
        ]:
            game = service.advance(game["id"], TurnRequest(
                request_id=f"turn-{game['turn']}", expected_version=game["version"], actions=actions,
            ))
        assert game["status"] == "finished"
        eligible = {"audit", "accept_scope", "accept_delay", "refuse", "release",
                    "accept_feature", "uncertain_commitment"}
        expected_ids = [event["id"] for event in game["events"] if event["type"] in eligible]
        assert len(expected_ids) > 3
        assert [moment["event_ids"][-1] for moment in policy.candidates] == expected_ids
        assert len(game["debrief"]["moments"]) == 3
        assert game["debrief"]["moments"][-1]["event_ids"][-1] == expected_ids[-1]
    finally:
        service.close()
