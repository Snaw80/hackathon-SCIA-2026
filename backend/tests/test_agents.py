from types import SimpleNamespace
import pytest
from meltdown.agents import LangChainPolicy
from meltdown.models import AgentIntent


def test_llm_configuration_caps_calls_and_uses_structured_output(monkeypatch):
    from langchain import chat_models

    calls = {}

    class FakeModel:
        def with_structured_output(self, schema, **kwargs):
            calls["schema_options"] = kwargs
            return self

    def init(name, **kwargs):
        calls.update(name=name, options=kwargs)
        return FakeModel()

    monkeypatch.setattr(chat_models, "init_chat_model", init)
    monkeypatch.setenv("MELTDOWN_MAX_OUTPUT_TOKENS", "384")
    monkeypatch.setenv("MELTDOWN_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("MELTDOWN_REASONING_EFFORT", "none")
    LangChainPolicy("openai:gpt-5.4-nano")
    assert calls["options"]["max_tokens"] == 384
    assert calls["options"]["max_retries"] == 0
    assert calls["options"]["reasoning_effort"] == "none"
    assert calls["schema_options"]["include_raw"] is True


def test_llm_parsing_failure_reports_usage_before_fallback():
    policy = object.__new__(LangChainPolicy)
    records = []
    policy.on_result = records.append

    class FailedOutput:
        def invoke(self, messages):
            return {
                "raw": SimpleNamespace(usage_metadata={"input_tokens": 23, "output_tokens": 384}),
                "parsed": None,
                "parsing_error": ValueError("bad structured output"),
            }

    with pytest.raises(ValueError):
        policy._invoke(FailedOutput(), [("human", "test")])
    assert records[0]["usage"]["output_tokens"] == 384
    assert records[0]["parsed"] is False


def test_llm_rejects_fabricated_facts_even_with_valid_schema():
    policy = object.__new__(LangChainPolicy)
    policy.structured = None
    policy._invoke = lambda *args: AgentIntent(action="message", fact_ids=["secret"])
    with pytest.raises(ValueError, match="knowledge"):
        policy.decide({"allowed_actions": ["message"], "facts": {}})


def test_llm_rejects_self_messages():
    policy = object.__new__(LangChainPolicy)
    policy.structured = None
    policy._invoke = lambda *args: AgentIntent(action="message", recipient="client", message="Hello")
    with pytest.raises(ValueError, match="itself"):
        policy.decide({"actor": "client", "allowed_actions": ["message"], "facts": {}})


def test_scope_proposal_terms_are_visible_only_to_negotiators():
    from meltdown.engine import prepare_turn
    from meltdown.models import TurnRequest
    from meltdown.scenario import new_game, observation

    game = new_game("terms")
    game["player_knowledge"].append("demo_acceptable")
    game = prepare_turn(game, TurnRequest(request_id="terms", expected_version=0, actions=["reduce_scope"]))
    terms = observation(game, "client", 1)["proposals"][0]["terms"]
    assert "extra feature" in terms and "two core work units" in terms
    assert "proposals" not in observation(game, "developer", 1)


def test_coach_receives_one_unambiguous_id_per_moment():
    from meltdown.agents import CoachSelection
    import json

    policy = object.__new__(LangChainPolicy)
    policy.model = SimpleNamespace(with_structured_output=lambda *a, **k: None)

    def select(runnable, messages):
        candidates = json.loads(messages[-1][1])
        assert candidates == [{"event_id": "e3", "title": "Accepted", "analysis": "Scope was accepted."}]
        return CoachSelection(event_ids=["e3"])

    policy._invoke = select
    debrief = {
        "moments": [
            {
                "event_ids": ["e1", "e3"],
                "title": "Accepted",
                "analysis": "Scope was accepted.",
                "alternative": "Try another approach.",
            }
        ]
    }
    assert policy.coach(debrief)["source"] == "llm"


def test_technical_observation_distinguishes_units_from_time_and_carries_signoff():
    from meltdown.scenario import new_game, observation

    game = new_game("units")
    game["verified"] = True
    work = observation(game, "developer", 1)["work"]
    assert work["core_remaining"] / work["normal_core_units_per_period"] == 3
    assert work["fix_remaining"] / work["normal_fix_units_per_period"] == 2
    assert work["remaining_unit"] == "work units, not periods"
    assert work["security_verified"] is True
    assert "work" not in observation(game, "client", 1)


def test_automated_tests_default_to_rules_and_block_provider_http():
    import httpx
    from meltdown.agents import configured_policy, RulesPolicy

    assert isinstance(configured_policy(), RulesPolicy)
    with pytest.raises(AssertionError, match="External HTTP"):
        httpx.get("https://api.openai.com/v1/models")


def test_rules_client_asks_for_assurance_before_deciding_on_a_low_trust_offer():
    from meltdown.agents import RulesPolicy
    from meltdown.scenario import new_game, observation

    game = new_game("question")
    game["actions"] = ["request_delay"]
    game["proposals"] = ["request_delay"]
    game["metrics"]["trust"] = 40
    context = observation(game, "client", 1)

    intent = RulesPolicy().decide(context)

    assert intent.action == "ask_player"
    assert intent.question
    assert intent.question_reason
