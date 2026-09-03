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
    "investigate": "Comparer ce parcours à une partie où l’audit est demandé dès le premier tour.",
    "capacity": "Tester une autre répartition de la capacité entre correction, socle et repos.",
    "negotiate": "Explorer une clarification du besoin avant de confirmer un périmètre.",
    "communicate": "Comparer l’effet d’un point de situation plus précoce sur la négociation.",
}


def build_debrief(game):
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
        if e["type"] in candidate_types and e["type"] not in seen:
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
        "summary": f"Après {game['turn']} tours : avancement {game['metrics']['progress']} %, budget {game['metrics']['budget']}/100, confiance client {game['metrics']['trust']}/100 et moral {game['metrics']['morale']}/100. Les moments ci-dessous proviennent des événements enregistrés. Les alternatives sont des pistes à tester, pas des résultats simulés.",
        "moments": candidates[:3],
        "source": "rules",
    }


def public_view(game):
    if game["verified"]:
        security = {"status": "safe", "label": "Validée", "detail": "Correction vérifiée dans le scénario"}
    elif game["risk_known"]:
        security = {
            "status": "critical",
            "label": "Risque critique",
            "detail": "Correction et validation nécessaires",
        }
    else:
        security = {
            "status": "unknown",
            "label": "À évaluer",
            "detail": "Un signal technique reste à qualifier",
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
                "status": "Terminé"
                if task["remaining"] == 0
                else "Priorité active"
                if active
                else "En attente",
            }
        )
    characters = [
        {
            "id": key,
            **{
                field: game["agents"][key][field]
                for field in ("name", "role", "initials", "color", "stress", "trust", "activity")
            },
            "status": "Sous pression" if game["agents"][key]["stress"] > 70 else "En poste",
        }
        for key in ROLES
    ]
    return {
        "id": game["id"],
        "version": game["version"],
        "turn": game["turn"],
        "max_turns": 6,
        "status": game["status"],
        "mode": game["mode"],
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
