from meltdown.agents import RulesPolicy
from meltdown.interpreter import interpret_command
from meltdown.scenario import new_game


def test_rules_interpreter_maps_two_management_intents_in_spoken_order():
    result = interpret_command(
        new_game("g"),
        "Audit the defect and put Alex on the security fix",
        RulesPolicy(),
    )

    assert result.actions == ["audit", "prioritize_fix"]
    assert result.confidence == "clear"
    assert "Audit the defect" in result.summary
    assert "Prioritize the fix" in result.summary


def test_rules_interpreter_returns_ambiguity_instead_of_guessing():
    result = interpret_command(new_game("g"), "Do something clever", RulesPolicy())

    assert result.actions == []
    assert result.confidence == "ambiguous"
    assert result.reason


def test_rules_interpreter_recognizes_an_explicit_wait_as_no_action():
    result = interpret_command(new_game("g"), "Continue and let the current work progress", RulesPolicy())

    assert result.actions == []
    assert result.confidence == "clear"


def test_interpreter_does_not_silently_execute_an_unavailable_action():
    game = new_game("g")
    game["risk_known"] = True
    result = interpret_command(game, "Audit the security defect", RulesPolicy())

    assert result.confidence == "ambiguous"
    assert "already" in result.reason.lower()


def test_provider_failure_uses_the_deterministic_interpreter():
    class BrokenInterpreter(RulesPolicy):
        mode = "llm"

        def interpret(self, game, command):
            raise TimeoutError("provider unavailable")

    result = interpret_command(new_game("g"), "Request an extension", BrokenInterpreter())

    assert result.actions == ["request_delay"]
    assert result.confidence == "clear"
