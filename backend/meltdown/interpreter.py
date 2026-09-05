from .engine import prepare_turn
from .models import CommandInterpretation, TurnRequest
from .scenario import ACTIONS


def canonical_summary(actions):
    if not actions:
        return "Continue without a new management decision."
    titles = "; ".join(ACTIONS[action][0] for action in actions)
    label = "Selected decision" if len(actions) == 1 else "Selected decisions"
    return f"{label}: {titles}."


def interpret_command(game, command, policy):
    result = CommandInterpretation.model_validate(policy.interpret(game, command))
    if any(action not in ACTIONS for action in result.actions):
        raise ValueError("The model returned an unknown action.")
    if result.confidence == "clear":
        # Action IDs are validated engine data; model-authored prose must not be
        # persisted as factual engine narration.
        result = result.model_copy(update={"summary": canonical_summary(result.actions)})
        prepare_turn(
            game,
            TurnRequest(
                request_id="model-interpretation",
                expected_version=game["version"],
                actions=result.actions,
            ),
        )
    return result
