import pytest

from meltdown.interpreter import interpret_command
from meltdown.models import CommandInterpretation
from meltdown.scenario import new_game


class StaticInterpreter:
    def __init__(self, result):
        self.result = result

    def interpret(self, game, command):
        return self.result


def test_llm_interpreter_preserves_valid_structured_decisions():
    expected = CommandInterpretation(
        summary="Audit the defect, then prioritize the fix.",
        actions=["audit", "prioritize_fix"],
        confidence="clear",
    )

    result = interpret_command(new_game("g"), "Please handle the security issue", StaticInterpreter(expected))

    assert result.actions == expected.actions
    assert result.confidence == "clear"
    assert result.summary == "Selected decisions: Audit the defect; Prioritize the fix."


def test_llm_interpreter_does_not_publish_model_summary_as_engine_fact():
    result = CommandInterpretation(
        summary="The audit succeeded and the vulnerability is fixed.",
        actions=["audit"],
        confidence="clear",
    )

    interpreted = interpret_command(new_game("g"), "Audit the defect", StaticInterpreter(result))

    assert interpreted.summary == "Selected decision: Audit the defect."
    assert "succeeded" not in interpreted.summary


def test_llm_interpreter_can_request_clarification_without_advancing():
    expected = CommandInterpretation(
        summary="The requested outcome is unclear.",
        actions=[],
        confidence="ambiguous",
        reason="Specify whether you want an audit or a scope change.",
    )

    result = interpret_command(new_game("g"), "Handle it", StaticInterpreter(expected))

    assert result == expected


def test_llm_interpreter_can_explicitly_continue_without_a_new_action():
    expected = CommandInterpretation(
        summary="Continue the current work.",
        actions=[],
        confidence="clear",
    )

    result = interpret_command(new_game("g"), "Continue", StaticInterpreter(expected))

    assert result.actions == []
    assert result.confidence == "clear"
    assert result.summary == "Continue without a new management decision."


def test_llm_interpreter_rejects_an_unavailable_clear_action():
    game = new_game("g")
    game["risk_known"] = True
    result = CommandInterpretation(summary="Audit again.", actions=["audit"], confidence="clear")

    with pytest.raises(ValueError, match="already"):
        interpret_command(game, "Audit the security defect", StaticInterpreter(result))


def test_provider_failure_is_not_replaced_by_a_rules_interpretation():
    class BrokenInterpreter:
        def interpret(self, game, command):
            raise TimeoutError("provider unavailable")

    with pytest.raises(TimeoutError, match="provider unavailable"):
        interpret_command(new_game("g"), "Request an extension", BrokenInterpreter())
