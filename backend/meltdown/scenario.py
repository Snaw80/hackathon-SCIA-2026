from copy import deepcopy

ROLES = {
    "developer": {
        "name": "Alex",
        "role": "Lead developer",
        "initials": "AL",
        "color": "#79d5e9",
        "private_goal": "Préserver la qualité et une charge de travail tenable.",
    },
    "client": {
        "name": "Camille",
        "role": "Cliente",
        "initials": "CM",
        "color": "#bb9bf7",
        "private_goal": "Réussir la démonstration à sa direction sans perdre sa crédibilité.",
    },
    "sales": {
        "name": "Sam",
        "role": "Commercial",
        "initials": "SM",
        "color": "#ffc77d",
        "private_goal": "Conserver le contrat et faire reconnaître sa contribution.",
    },
    "security": {
        "name": "Morgan",
        "role": "Responsable sécurité",
        "initials": "MG",
        "color": "#84d8b8",
        "private_goal": "Obtenir une validation de sécurité fondée sur des preuves.",
    },
}
FACTS = {
    "defect": "Un défaut a été repéré dans le module d’export ; sa gravité demande un audit.",
    "critical": "L’audit confirme une faille critique dans le module d’export. La correction et sa validation sont nécessaires avant livraison.",
    "demo_acceptable": "L’échéance du client concerne une démonstration. Un périmètre réduit peut convenir s’il est explicitement négocié.",
    "promise": "Le commercial a promis une fonctionnalité supplémentaire avant de confirmer la capacité technique.",
    "capacity": "Le correctif demande deux périodes. Le socle restant demande trois périodes de travail normal.",
}
ACTIONS = {
    "audit": (
        "Auditer le défaut",
        "Qualifier le risque et obtenir une preuve technique.",
        6,
        "Technique",
        ["security"],
    ),
    "prioritize_fix": (
        "Prioriser le correctif",
        "Affecter le développeur à la correction. Le socle attendra.",
        0,
        "Technique",
        ["developer", "security"],
    ),
    "clarify": (
        "Clarifier le besoin client",
        "Comprendre ce qui est réellement attendu à l’échéance.",
        0,
        "Relation client",
        ["client"],
    ),
    "communicate": (
        "Partager un point de situation",
        "Communiquer les faits connus et l’avancement au client.",
        0,
        "Relation client",
        ["client", "sales"],
    ),
    "reduce_scope": (
        "Négocier un périmètre réduit",
        "Proposer une démonstration limitée. L’accord reste à obtenir.",
        0,
        "Relation client",
        ["client", "sales"],
    ),
    "request_delay": (
        "Demander un report",
        "Demander une nouvelle échéance, avec les faits disponibles.",
        0,
        "Relation client",
        ["client", "sales"],
    ),
    "accept_feature": (
        "Accepter la fonctionnalité",
        "Engager le projet sur la demande supplémentaire (+4 unités).",
        0,
        "Relation client",
        ["developer", "client", "sales"],
    ),
    "prioritize_core": (
        "Prioriser la livraison",
        "Reprendre le socle, puis la fonctionnalité si elle est engagée.",
        0,
        "Technique",
        ["developer"],
    ),
    "rest": (
        "Réduire la charge",
        "Protéger l’équipe ce tour ; la progression du socle est réduite.",
        0,
        "Équipe",
        ["developer"],
    ),
    "reinforce": (
        "Mobiliser du renfort",
        "Acheter une unité de capacité supplémentaire pour ce tour.",
        12,
        "Équipe",
        ["developer"],
    ),
    "validate_release": (
        "Valider la correction",
        "Faire vérifier un correctif terminé avant la livraison.",
        0,
        "Technique",
        ["security"],
    ),
    "release": (
        "Livrer la version",
        "Livrer le périmètre convenu après les validations nécessaires.",
        0,
        "Technique",
        list(ROLES),
    ),
}


def new_game(game_id, mode="rules"):
    return {
        "id": game_id,
        "version": 0,
        "turn": 0,
        "max_turns": 6,
        "status": "active",
        "mode": mode,
        "metrics": {"budget": 100, "trust": 58, "morale": 68, "progress": 50},
        "tasks": {
            "core": {"title": "Socle de la livraison", "remaining": 6, "total": 12},
            "fix": {"title": "Correctif de sécurité", "remaining": 2, "total": 2},
            "feature": {"title": "Fonctionnalité supplémentaire", "remaining": 4, "total": 4},
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
                    "Un défaut à examiner, une livraison à terminer.",
                ),
                (
                    "client",
                    ROLES["client"],
                    37,
                    ["demo_acceptable", "promise"],
                    "Attend une confirmation du périmètre et de la date.",
                ),
                (
                    "sales",
                    ROLES["sales"],
                    40,
                    ["promise"],
                    "La fonctionnalité supplémentaire a déjà été annoncée.",
                ),
                (
                    "security",
                    ROLES["security"],
                    28,
                    ["defect"],
                    "L’alerte technique doit encore être qualifiée.",
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
        "proposals": [],
        "actions": [],
        "events": [
            {
                "id": "e0",
                "turn": 0,
                "round": 0,
                "actor": "director",
                "type": "briefing",
                "title": "Vous prenez les commandes",
                "detail": "La livraison est attendue dans trois jours. Une alerte technique reste à qualifier et une fonctionnalité a été promise. La direction souhaite maintenir l’échéance.",
                "effects": {},
                "causes": [],
                "audience": ["player"],
            }
        ],
        "last_run": {"rounds": 0, "agent_calls": 0, "fallbacks": 0, "duration_ms": 0, "steps": []},
        "outcome": None,
        "debrief": None,
        "action_event_ids": [],
        "work_blocked": False,
    }


def action_reason(game, action):
    if game["status"] != "active":
        return "La partie est terminée."
    if action not in ACTIONS:
        return "Décision inconnue."
    if game["metrics"]["budget"] < ACTIONS[action][2]:
        return "Budget insuffisant."
    if action == "audit" and game["risk_known"]:
        return "L’audit est déjà disponible."
    if action == "prioritize_fix" and game["tasks"]["fix"]["remaining"] == 0:
        return "Le correctif est terminé."
    if action == "clarify" and "demo_acceptable" in game["player_knowledge"]:
        return "Le besoin métier a déjà été clarifié."
    if action == "reduce_scope" and "demo_acceptable" not in game["player_knowledge"]:
        return "Clarifiez d’abord le besoin du client."
    if action == "reduce_scope" and game["scope"] == "partial":
        return "Un périmètre réduit a déjà été accepté."
    if action == "accept_feature" and game["feature_committed"]:
        return "La fonctionnalité est déjà engagée."
    if action == "request_delay" and game["delay_agreed"]:
        return "Le report a déjà été accepté."
    if action == "validate_release" and (game["tasks"]["fix"]["remaining"] > 0 or not game["risk_known"]):
        return "Un audit et un correctif terminé sont nécessaires."
    if action == "validate_release" and game["verified"]:
        return "La correction est déjà validée."
    if action == "release":
        if not game["verified"]:
            return "La validation de sécurité est nécessaire."
        if game["scope"] == "unagreed":
            return "Un accord client sur le périmètre est nécessaire."
        if game["tasks"]["core"]["remaining"] > 0 or (
            game["scope"] == "full" and game["tasks"]["feature"]["remaining"] > 0
        ):
            return "Le périmètre convenu n’est pas terminé."
    return None


def allowed_intents(game, actor, round_number):
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
    elif actor == "sales":
        allowed.append("clarify_promise")
    return allowed


def observation(game, actor, round_number, inbox=None):
    agent = game["agents"][actor]
    context = {
        "actor": actor,
        "name": agent["name"],
        "role": agent["role"],
        "private_goal": agent["private_goal"],
        "turn": game["turn"] + 1,
        "round": round_number,
        "stress": agent["stress"],
        "trust": agent["trust"],
        "facts": {key: FACTS[key] for key in agent["knowledge"]},
        "memory": [event["title"] for event in game["events"] if actor in event["audience"]][-8:],
        "inbox": deepcopy(inbox or []),
        "allowed_actions": allowed_intents(game, actor, round_number),
        "directives": [action for action in game["actions"] if actor in ACTIONS[action][4]],
        "progress": game["metrics"]["progress"],
    }
    if actor in ("developer", "security"):
        context["work"] = {
            "priority": game["priority"],
            "fix_remaining": game["tasks"]["fix"]["remaining"],
            "core_remaining": game["tasks"]["core"]["remaining"],
        }
    if actor == "client":
        context["client_trust"] = game["metrics"]["trust"]
    return context
