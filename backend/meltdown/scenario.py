from copy import deepcopy

ROLES = {
    "developer": {
        "name": "Alex",
        "role": "Lead developer",
        "initials": "AL",
        "color": "#79d5e9",
        "private_goal": "Protect quality and a sustainable workload.",
    },
    "client": {
        "name": "Camille",
        "role": "Client",
        "initials": "CM",
        "color": "#bb9bf7",
        "private_goal": "Deliver a successful demonstration to management and protect credibility.",
    },
    "sales": {
        "name": "Sam",
        "role": "Sales lead",
        "initials": "SM",
        "color": "#ffc77d",
        "private_goal": "Keep the contract and earn recognition for the contribution.",
    },
    "security": {
        "name": "Morgan",
        "role": "Security lead",
        "initials": "MG",
        "color": "#84d8b8",
        "private_goal": "Obtain security approval backed by evidence.",
    },
}
FACTS = {
    "defect": "A defect was found in the export module; an audit is needed to assess its severity.",
    "critical": "The audit confirms a critical vulnerability in the export module. A fix and verification are required before release.",
    "demo_acceptable": "The client deadline is for a demonstration. A reduced scope can work if explicitly agreed.",
    "promise": "The sales lead promised an extra feature before confirming technical capacity.",
    "capacity": "The fix takes two periods. The remaining core delivery takes three periods at normal capacity.",
}
ACTIONS = {
    "audit": (
        "Audit the defect",
        "Assess the risk and obtain technical evidence.",
        6,
        "Technical",
        ["security"],
    ),
    "prioritize_fix": (
        "Prioritize the fix",
        "Assign the developer to the fix. Core delivery will wait.",
        0,
        "Technical",
        ["developer", "security"],
    ),
    "clarify": (
        "Clarify the client’s needs",
        "Find out what is actually needed by the deadline.",
        0,
        "Client relations",
        ["client"],
    ),
    "communicate": (
        "Share a status update",
        "Share known facts and progress with the client.",
        0,
        "Client relations",
        ["client", "sales"],
    ),
    "reduce_scope": (
        "Negotiate a smaller scope",
        "Propose a limited demonstration. Agreement is still needed.",
        0,
        "Client relations",
        ["client", "sales"],
    ),
    "request_delay": (
        "Request an extension",
        "Request a new deadline, backed by the available facts.",
        0,
        "Client relations",
        ["client", "sales"],
    ),
    "accept_feature": (
        "Commit to the extra feature",
        "Commit the project to the extra request (+4 work units).",
        0,
        "Client relations",
        ["developer", "client", "sales"],
    ),
    "prioritize_core": (
        "Prioritize core delivery",
        "Resume core delivery, then the extra feature if committed.",
        0,
        "Technical",
        ["developer"],
    ),
    "rest": (
        "Reduce the workload",
        "Protect the team this turn; core delivery progresses more slowly.",
        0,
        "Team",
        ["developer"],
    ),
    "reinforce": (
        "Bring in support",
        "Buy one extra unit of capacity for this turn.",
        12,
        "Team",
        ["developer"],
    ),
    "validate_release": (
        "Verify the fix",
        "Have the completed fix checked before release.",
        0,
        "Technical",
        ["security"],
    ),
    "release": (
        "Release the version",
        "Deliver the agreed scope after the required checks.",
        0,
        "Technical",
        list(ROLES),
    ),
}


def new_game(game_id):
    return {
        "id": game_id,
        "version": 0,
        "turn": 0,
        "max_turns": 6,
        "status": "active",
        "metrics": {"budget": 100, "trust": 58, "morale": 68, "progress": 50},
        "tasks": {
            "core": {"title": "Core delivery", "remaining": 6, "total": 12},
            "fix": {"title": "Security fix", "remaining": 2, "total": 2},
            "feature": {"title": "Extra feature", "remaining": 4, "total": 4},
        },
        "agents": {
            key: {
                **deepcopy(role),
                "stress": stress,
                "trust": 55,
                "knowledge": knowledge,
                "activity": activity,
            }
            for key, role, stress, knowledge, activity in [
                (
                    "developer",
                    ROLES["developer"],
                    46,
                    ["defect", "capacity"],
                    "A defect to investigate and a delivery to finish.",
                ),
                (
                    "client",
                    ROLES["client"],
                    37,
                    ["demo_acceptable", "promise"],
                    "Waiting for confirmation of scope and deadline.",
                ),
                (
                    "sales",
                    ROLES["sales"],
                    40,
                    ["promise"],
                    "The extra feature has already been announced.",
                ),
                (
                    "security",
                    ROLES["security"],
                    28,
                    ["defect"],
                    "The technical warning still needs investigation.",
                ),
            ]
        },
        "player_knowledge": ["defect", "promise"],
        "risk_known": False,
        "verified": False,
        "priority": "core",
        "scope": "unagreed",
        "feature_committed": False,
        "delay_agreed": False,
        "released": False,
        "pending_messages": [],
        "pending_questions": [],
        "answer_followup": False,
        "proposals": [],
        "actions": [],
        "events": [
            {
                "id": "e0",
                "turn": 0,
                "round": 0,
                "actor": "director",
                "type": "briefing",
                "title": "You take command",
                "detail": "Delivery is expected in three days. A technical warning needs investigation and an extra feature has been promised. Management wants to keep the deadline.",
                "effects": {},
                "causes": [],
                "audience": ["player"],
            }
        ],
        "last_run": {"rounds": 0, "agent_calls": 0, "duration_ms": 0, "steps": []},
        "outcome": None,
        "debrief": None,
        "action_event_ids": [],
        "work_blocked": False,
    }


def action_reason(game, action):
    if game["status"] != "active":
        return "This game is over."
    if action not in ACTIONS:
        return "Unknown decision."
    if game["metrics"]["budget"] < ACTIONS[action][2]:
        return "Insufficient budget."
    if action == "audit" and game["risk_known"]:
        return "The audit is already available."
    if action == "prioritize_fix" and game["tasks"]["fix"]["remaining"] == 0:
        return "The fix is complete."
    if action == "clarify" and "demo_acceptable" in game["player_knowledge"]:
        return "The business need has already been clarified."
    if action == "reduce_scope" and "demo_acceptable" not in game["player_knowledge"]:
        return "Clarify the client’s needs first."
    if action == "reduce_scope" and game["scope"] == "partial":
        return "A reduced scope has already been agreed."
    if action == "accept_feature" and game["feature_committed"]:
        return "The extra feature is already committed."
    if action == "request_delay" and game["delay_agreed"]:
        return "The extension has already been agreed."
    if action == "validate_release" and (game["tasks"]["fix"]["remaining"] > 0 or not game["risk_known"]):
        return "An audit and a completed fix are required."
    if action == "validate_release" and game["verified"]:
        return "The fix has already been verified."
    if action == "release":
        if not game["verified"]:
            return "Security approval is required."
        if game["scope"] == "unagreed":
            return "Client agreement on the scope is required."
        if game["tasks"]["core"]["remaining"] > 0 or (
            game["scope"] == "full" and game["tasks"]["feature"]["remaining"] > 0
        ):
            return "The agreed scope is not complete."
    return None


def allowed_intents(game, actor, round_number, *, allow_questions=True):
    allowed = ["wait", "message"]
    if actor == "developer":
        allowed.append("warn")
        if not game["work_blocked"]:
            allowed.append("work")
        if game["agents"][actor]["stress"] >= 80 and not game["work_blocked"]:
            allowed.append("refuse")
    elif actor == "security":
        if not game["risk_known"]:
            allowed.append("audit")
        if game["risk_known"] and not game["verified"] and game["tasks"]["fix"]["remaining"] == 0:
            allowed.append("verify")
    elif actor == "client":
        if "clarify" in game["actions"] and "demo_acceptable" not in game["player_knowledge"]:
            allowed.append("reveal_need")
        if "reduce_scope" in game["proposals"] and game["scope"] != "partial":
            allowed += ["accept_scope", "counter", "reject"]
        if "request_delay" in game["proposals"] and not game["delay_agreed"]:
            allowed += ["accept_delay", "counter", "reject"]
        if "communicate" in game["actions"] and round_number == 1:
            allowed.append("acknowledge")
        if allow_questions and game["proposals"]:
            allowed.append("ask_player")
    elif actor == "sales":
        allowed.append("clarify_promise")
    return allowed


INTENT_DESCRIPTIONS = {
    "wait": "No new intervention; already assigned work still progresses.",
    "message": "Send a useful message as yourself to another character or the player.",
    "audit": "Investigate the known defect and establish its severity.",
    "verify": "Verify the completed, audited fix and grant security approval.",
    "work": "Acknowledge and continue assigned work within available capacity.",
    "refuse": "Pause work this turn because your workload is unsustainable.",
    "warn": "Flag competing priorities or unsustainable workload to the player.",
    "reveal_need": "Answer the clarification request: disclose your actual demonstration needs.",
    "accept_scope": "Accept the proposed smaller demonstration if it meets your known business need.",
    "accept_delay": "Accept a proposed extension if the known evidence and trust justify it.",
    "counter": "Withhold agreement and ask for assurances when the proposal is not convincing.",
    "reject": "Reject the proposed scope or deadline change.",
    "acknowledge": "Acknowledge the status update and improve trust through transparency.",
    "clarify_promise": "Explain your earlier extra-feature promise and align commitments with the client.",
    "ask_player": "Ask the player one concise question when their answer is needed before deciding.",
}


def observation(game, actor, round_number, inbox=None, *, allow_questions=True):
    agent = game["agents"][actor]
    context = {
        "actor": actor,
        "name": agent["name"],
        "role": agent["role"],
        "turn": game["turn"] + 1,
        "round": round_number,
        "stress": agent["stress"],
        "trust": agent["trust"],
        # Only player-visible facts enter the generative expression boundary. Hidden
        # facts still shape the engine's available actions and canonical outcomes.
        "facts": {
            key: FACTS[key]
            for key in agent["knowledge"]
            if key in game["player_knowledge"]
        },
        "memory": [event["title"] for event in game["events"] if actor in event["audience"]][-8:],
        "inbox": deepcopy(inbox or []),
        "allowed_actions": allowed_intents(
            game, actor, round_number, allow_questions=allow_questions
        ),
        "directives": [action for action in game["actions"] if actor in ACTIONS[action][4]],
        "progress": game["metrics"]["progress"],
    }
    context["action_options"] = {action: INTENT_DESCRIPTIONS[action] for action in context["allowed_actions"]}
    if actor in ("client", "sales"):
        terms = {
            "reduce_scope": "Offer awaiting your agreement: deliver a limited demonstration, removing the extra feature and two core work units from this delivery. The client’s demonstration need remains the goal.",
            "request_delay": "Offer awaiting your agreement: postpone delivery beyond the original deadline. Review remaining work at the end of the six turns.",
        }
        context["proposals"] = [{"id": key, "terms": terms[key]} for key in game["proposals"]]
    if actor in ("developer", "security"):
        context["work"] = {
            "priority": game["priority"],
            "fix_remaining": game["tasks"]["fix"]["remaining"],
            "core_remaining": game["tasks"]["core"]["remaining"],
            "remaining_unit": "work units, not periods",
            "normal_core_units_per_period": 2,
            "normal_fix_units_per_period": 1,
            "security_verified": game["verified"],
        }
    if actor == "client":
        context["client_trust"] = game["metrics"]["trust"]
    return context
