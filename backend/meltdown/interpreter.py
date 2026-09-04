import re

from .engine import prepare_turn
from .models import CommandInterpretation, TurnRequest
from .scenario import ACTIONS


ACTION_PATTERNS = {
    "audit": [
        r"\b(?:audit|investigat\w*|assess|check)\b.{0,45}\b(?:defect|risk|vulnerab\w*|security|issue)\b",
    ],
    "prioritize_fix": [
        r"\b(?:prioriti[sz]\w*|focus|put|assign|work)\b.{0,50}\b(?:security\s+)?fix\b",
        r"\bfix\b.{0,25}\b(?:first|priority)\b",
    ],
    "clarify": [
        r"\b(?:clarif\w*|ask|understand|find\s+out)\b.{0,50}\b(?:client|need|deadline|demo)\b",
    ],
    "communicate": [
        r"\b(?:share|send|give|communicat\w*|inform)\b.{0,50}\b(?:status|update|client|progress)\b",
        r"\bstatus\s+update\b",
    ],
    "reduce_scope": [
        r"\b(?:reduce|smaller|cut|limit\w*)\b.{0,45}\b(?:scope|demo|delivery|feature)\b",
    ],
    "request_delay": [r"\b(?:request\s+)?(?:delay|extension|postpone\w*|new\s+deadline)\b"],
    "accept_feature": [
        r"\b(?:accept|commit|build|add|include)\w*\b.{0,45}\b(?:extra\s+)?feature\b",
    ],
    "prioritize_core": [
        r"\b(?:prioriti[sz]\w*|focus|resume|assign)\b.{0,45}\bcore(?:\s+delivery)?\b",
    ],
    "rest": [
        r"\b(?:rest|reduce|lighten|ease)\w*\b.{0,45}\b(?:team|workload|pressure)\b",
        r"\bgive\b.{0,20}\bteam\b.{0,20}\bbreak\b",
    ],
    "reinforce": [
        r"\b(?:bring|hire|add|get)\b.{0,40}\b(?:support|help|developer|engineer|capacity)\b",
    ],
    "validate_release": [
        r"\b(?:verify|validate|check|approve)\w*\b.{0,45}\b(?:fix|release|security)\b",
    ],
    "release": [r"\b(?:release|ship|deliver|deploy)\b.{0,35}\b(?:version|product|scope|now)?\b"],
}

WAIT_PATTERNS = [
    r"\b(?:wait|continue|proceed)\b.{0,45}\b(?:current|without|progress|work|action)\b",
    r"\bdo\s+nothing\b",
]


def _rules_interpretation(game, command):
    text = " ".join(command.lower().split())
    matches = []
    for action, patterns in ACTION_PATTERNS.items():
        starts = [match.start() for pattern in patterns if (match := re.search(pattern, text))]
        if starts:
            matches.append((min(starts), action))
    matches.sort()
    actions = [action for _, action in matches]
    if len(actions) > 2:
        return CommandInterpretation(
            summary="I found more than two decisions in that instruction.",
            actions=actions[:2],
            confidence="ambiguous",
            reason="Please limit the instruction to two management decisions for this round.",
        )
    if not actions:
        if any(re.search(pattern, text) for pattern in WAIT_PATTERNS):
            return CommandInterpretation(
                summary="Continue without issuing a new management action.",
                actions=[],
                confidence="clear",
            )
        return CommandInterpretation(
            summary="I could not map that instruction to the current project controls.",
            actions=[],
            confidence="ambiguous",
            reason="Rephrase it with the outcome, person, or project decision you want.",
        )
    summary = " + ".join(ACTIONS[action][0] for action in actions)
    result = CommandInterpretation(summary=summary, actions=actions, confidence="clear")
    try:
        prepare_turn(
            game,
            TurnRequest(request_id="interpretation", expected_version=game["version"], actions=actions),
        )
    except ValueError as exc:
        return result.model_copy(update={"confidence": "ambiguous", "reason": str(exc)})
    return result


def _validated_model_interpretation(game, command, policy):
    result = CommandInterpretation.model_validate(policy.interpret(game, command))
    if any(action not in ACTIONS for action in result.actions):
        raise ValueError("The model returned an unknown action.")
    if result.confidence == "clear":
        prepare_turn(
            game,
            TurnRequest(
                request_id="model-interpretation",
                expected_version=game["version"],
                actions=result.actions,
            ),
        )
    return result


def interpret_command(game, command, policy):
    if getattr(policy, "mode", "rules") == "llm" and hasattr(policy, "interpret"):
        try:
            return _validated_model_interpretation(game, command, policy)
        except Exception:
            pass
    return _rules_interpretation(game, command)
