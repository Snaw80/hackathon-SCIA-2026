from meltdown.models import AgentIntent, CommandInterpretation


def expressed(action, *, recipient="player", fact_ids=None, **kwargs):
    if action == "wait":
        return AgentIntent(action=action, **kwargs)
    return AgentIntent(
        action=action,
        speech=kwargs.pop("speech", f"I am responding with {action.replace('_', ' ')}."),
        reason=kwargs.pop("reason", "This response follows the current project state."),
        emotion=kwargs.pop("emotion", "calm"),
        recipient=recipient,
        fact_ids=fact_ids or [],
        **kwargs,
    )


class TestPolicy:
    """Deterministic test double for the mandatory external LLM boundary."""

    __test__ = False
    name = "test:scripted-llm"

    def decide(self, context):
        actor, allowed = context["actor"], context["allowed_actions"]
        directives = context["directives"]
        action = "wait"
        if actor == "security":
            if "audit" in allowed and ("audit" in directives or context["turn"] >= 3):
                action = "audit"
            elif "verify" in allowed:
                action = "verify"
        elif actor == "developer":
            if "refuse" in allowed and "rest" not in directives:
                action = "refuse"
            elif (
                context["round"] == 2
                and "critical" in context["facts"]
                and context["work"]["priority"] != "fix"
            ):
                action = "warn"
            elif "work" in allowed:
                action = "work"
        elif actor == "client":
            if "reveal_need" in allowed and context["round"] == 1:
                action = "reveal_need"
            elif "ask_player" in allowed and context["client_trust"] < 45:
                return expressed(
                    "ask_player",
                    speech="I need a concrete assurance before I can agree.",
                    reason="Client trust is too low to accept the proposal immediately.",
                    emotion="concerned",
                    question="What concrete assurance can you give me before I accept this change?",
                    question_reason="Trust is low and I need a clear commitment before changing the agreement.",
                )
            elif "accept_scope" in allowed:
                action = "accept_scope" if context["client_trust"] >= 35 else "counter"
            elif "accept_delay" in allowed:
                action = (
                    "accept_delay"
                    if context["client_trust"] >= 45 and "critical" in context["facts"]
                    else "counter"
                )
            elif "acknowledge" in allowed:
                action = "acknowledge"
        elif actor == "sales" and context["inbox"]:
            action = "clarify_promise"
        return expressed(action)

    def interpret(self, game, command):
        text = command.lower()
        if "handle it" in text or "clever" in text:
            return CommandInterpretation(
                summary="The requested management decision is unclear.",
                confidence="ambiguous",
                reason="Name the project outcome or action you want.",
            )
        ordered = []
        patterns = [
            ("audit", ("audit", "investigate")),
            ("prioritize_fix", ("prioritize the security fix", "prioritize the fix")),
            ("clarify", ("clarify",)),
            ("communicate", ("status update", "share a status")),
            ("reduce_scope", ("reduce the delivery scope", "reduce scope")),
            ("rest", ("reduce the team workload", "team workload", "rest")),
            ("request_delay", ("extension",)),
            ("release", ("release",)),
        ]
        for action, needles in patterns:
            positions = [text.index(needle) for needle in needles if needle in text]
            if positions:
                ordered.append((min(positions), action))
        actions = [action for _, action in sorted(ordered)][:2]
        if not actions and any(word in text for word in ("continue", "wait")):
            return CommandInterpretation(
                summary="Continue without a new management decision.",
                actions=[],
                confidence="clear",
            )
        return CommandInterpretation(
            summary="; ".join(action.replace("_", " ").title() for action in actions),
            actions=actions,
            confidence="clear" if actions else "ambiguous",
            reason=None if actions else "Name a valid project decision.",
        )

    def coach(self, debrief):
        return {**debrief, "source": "llm"}
