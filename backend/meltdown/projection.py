from copy import deepcopy
from .scenario import ACTIONS, ROLES, action_reason


def public_events(game):
    visible = [e for e in game["events"] if "player" in e["audience"]]
    ids = {e["id"] for e in visible}
    return [
        {
            **{k: deepcopy(v) for k, v in e.items() if k != "audience"},
            "causes": [i for i in e["causes"] if i in ids],
        }
        for e in visible
    ]


ALTERNATIVES = {
    "investigate": "Compare this run with a game where the audit is requested on the first turn.",
    "capacity": "Try a different allocation of capacity between the fix, core delivery, and rest.",
    "negotiate": "Explore clarifying the need before committing to a scope.",
    "communicate": "Compare how an earlier status update affects the negotiation.",
}


def build_debrief(game, *, all_moments=False):
    visible = public_events(game)
    candidate_types = {
        "audit": "investigate",
        "accept_scope": "negotiate",
        "accept_delay": "communicate",
        "refuse": "capacity",
        "release": "capacity",
        "accept_feature": "negotiate",
        "uncertain_commitment": "communicate",
    }
    candidates = []
    seen = set()
    for e in visible:
        if e["type"] in candidate_types and (all_moments or e["type"] not in seen):
            seen.add(e["type"])
            candidates.append(
                {
                    "title": e["title"],
                    "analysis": e["detail"],
                    "event_ids": [*e["causes"], e["id"]],
                    "alternative": ALTERNATIVES[candidate_types[e["type"]]],
                }
            )
    if not candidates:
        e = visible[-1]
        candidates = [
            {
                "title": e["title"],
                "analysis": e["detail"],
                "event_ids": [e["id"]],
                "alternative": ALTERNATIVES["investigate"],
            }
        ]
    return {
        "headline": game["outcome"]["title"],
        "summary": f"After {game['turn']} turns: progress {game['metrics']['progress']} %, budget {game['metrics']['budget']}/100, client trust {game['metrics']['trust']}/100 and morale {game['metrics']['morale']}/100. The moments below come from recorded events. Alternatives are suggestions to try, not simulated outcomes.",
        "moments": candidates if all_moments else candidates[:3],
        "source": "rules",
    }


def public_view(game):
    if game["verified"]:
        security = {"status": "safe", "label": "Verified", "detail": "Fix verified within the scenario"}
    elif game["risk_known"]:
        security = {
            "status": "critical",
            "label": "Critical risk",
            "detail": "Fix and verification required",
        }
    else:
        security = {
            "status": "unknown",
            "label": "Needs assessment",
            "detail": "A technical warning needs investigation",
        }
    tasks = []
    for key, task in game["tasks"].items():
        if key == "fix" and not game["risk_known"]:
            continue
        if key == "feature" and not game["feature_committed"]:
            continue
        active = key == game["priority"] or (key == "core" and game["tasks"]["fix"]["remaining"] == 0)
        tasks.append(
            {
                "id": key,
                **deepcopy(task),
                "status": "Complete"
                if task["remaining"] == 0
                else "Active priority"
                if active
                else "Waiting",
            }
        )
    characters = [
        {
            "id": key,
            **{
                field: game["agents"][key][field]
                for field in ("name", "role", "initials", "color", "stress", "trust", "activity")
            },
            "status": "Under pressure" if game["agents"][key]["stress"] > 70 else "On duty",
        }
        for key in ROLES
    ]
    return {
        "id": game["id"],
        "version": game["version"],
        "turn": game["turn"],
        "max_turns": 6,
        "status": game["status"],
        "metrics": deepcopy(game["metrics"]),
        "security": security,
        "agents": characters,
        "tasks": tasks,
        "actions": [
            {
                "id": key,
                "title": info[0],
                "description": info[1],
                "cost": info[2],
                "category": info[3],
                "disabled": bool(action_reason(game, key)),
                "reason": action_reason(game, key),
            }
            for key, info in ACTIONS.items()
        ],
        "events": public_events(game),
        "last_run": deepcopy(game["last_run"]),
        "outcome": deepcopy(game["outcome"]),
        "debrief": deepcopy(game["debrief"]),
    }


def public_run(run):
    if run is None:
        return None
    return {
        key: deepcopy(run.get(key))
        for key in (
            "id",
            "phase",
            "command",
            "interpretation",
            "active_agents",
            "progress",
            "questions",
            "error",
            "created_at",
            "updated_at",
        )
    }
