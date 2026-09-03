from copy import deepcopy
from .models import AgentIntent, TurnRequest
from .scenario import ACTIONS, FACTS, action_reason, allowed_intents


def event(game, actor, kind, title, detail, *, effects=None, causes=None, audience=None, round_number=0):
    item = {
        "id": f"e{len(game['events'])}",
        "turn": game["turn"] + 1,
        "round": round_number,
        "actor": actor,
        "type": kind,
        "title": title,
        "detail": detail,
        "effects": effects or {},
        "causes": list(causes or []),
        "audience": audience or ["player"],
    }
    game["events"].append(item)
    return item


def adjust(game, key, amount):
    before = game["metrics"][key]
    game["metrics"][key] = max(0, min(100, before + amount))
    return game["metrics"][key] - before


def prepare_turn(original, request: TurnRequest):
    if original["version"] != request.expected_version:
        raise ValueError("Cette partie a avancé. La dernière version a été rechargée.")
    if original["status"] != "active":
        raise ValueError("Cette partie est terminée.")
    for action in request.actions:
        if reason := action_reason(original, action):
            raise ValueError(reason)
    if sum(ACTIONS[a][2] for a in request.actions) > original["metrics"]["budget"]:
        raise ValueError("Le budget ne couvre pas ces deux décisions.")
    if {"prioritize_fix", "prioritize_core"} <= set(request.actions):
        raise ValueError("Le développeur ne peut pas recevoir deux priorités concurrentes.")
    if {"reduce_scope", "accept_feature"} <= set(request.actions):
        raise ValueError("Choisissez un seul engagement de périmètre.")
    game = deepcopy(original)
    game["actions"] = list(request.actions)
    game["action_event_ids"] = []
    game["proposals"] = [a for a in request.actions if a in ("reduce_scope", "request_delay")]
    game["work_blocked"] = False
    game["last_run"] = {"rounds": 0, "agent_calls": 0, "fallbacks": 0, "duration_ms": 0, "steps": []}
    for action in request.actions:
        title, description, cost, _, recipients = ACTIONS[action]
        effects = {"budget": adjust(game, "budget", -cost)} if cost else {}
        e = event(
            game,
            "player",
            action,
            title,
            description,
            effects=effects,
            causes=[],
            audience=["player", *recipients],
        )
        game["action_event_ids"].append(e["id"])
        if action == "prioritize_fix":
            game["priority"] = "fix"
        elif action == "prioritize_core":
            game["priority"] = "core"
        elif action == "rest":
            game["agents"]["developer"]["stress"] = max(0, game["agents"]["developer"]["stress"] - 23)
            adjust(game, "morale", 10)
        elif action == "communicate":
            for recipient in ("client", "sales"):
                for fact in game["player_knowledge"]:
                    if fact not in game["agents"][recipient]["knowledge"]:
                        game["agents"][recipient]["knowledge"].append(fact)
        elif action == "accept_feature":
            game["feature_committed"] = True
            game["scope"] = "full"
            adjust(game, "trust", 7)
        elif action == "release":
            game["released"] = True
    if game["released"] and (reason := action_reason(game, "release")):
        raise ValueError(reason)
    return game


def queue_message(game, actor, recipient, text, fact_ids, cause, round_number):
    if recipient == actor:
        return
    if recipient == "player":
        for fact in fact_ids:
            if fact not in game["player_knowledge"]:
                game["player_knowledge"].append(fact)
        return
    game["pending_messages"].append(
        {
            "id": f"m-{cause['id']}-{recipient}",
            "from": actor,
            "to": recipient,
            "text": text,
            "fact_ids": fact_ids,
            "cause": cause["id"],
            "turn": game["turn"] + 1,
            "round": round_number,
        }
    )


def resolve_intents(original, packets, round_number):
    game = deepcopy(original)
    # Stable order: evidence first, then capacity, then commitments.
    for actor in ("security", "developer", "client", "sales"):
        if actor not in packets:
            continue
        packet = packets[actor]
        intent = AgentIntent.model_validate(packet["intent"])
        triggers = {
            "audit": {"audit"},
            "verify": {"validate_release"},
            "work": {"prioritize_fix", "prioritize_core", "rest", "reinforce", "accept_feature"},
            "refuse": {"accept_feature", "prioritize_fix", "prioritize_core"},
            "warn": {"prioritize_fix", "prioritize_core", "accept_feature"},
            "reveal_need": {"clarify"},
            "accept_scope": {"reduce_scope"},
            "accept_delay": {"request_delay"},
            "acknowledge": {"communicate"},
            "counter": {"reduce_scope", "request_delay"},
            "reject": {"reduce_scope", "request_delay"},
        }.get(intent.action, set())
        direct_causes = [
            e["id"] for e in game["events"] if e["id"] in game["action_event_ids"] and e["type"] in triggers
        ]
        causes = list(dict.fromkeys(direct_causes + packet.get("causes", [])))
        if intent.action not in allowed_intents(original, actor, round_number):
            event(
                game,
                actor,
                "rejected",
                "Intention non applicable",
                "Les règles du projet ne permettent pas cette action dans l’état actuel.",
                causes=causes,
                round_number=round_number,
            )
            continue
        if any(fact not in original["agents"][actor]["knowledge"] for fact in intent.fact_ids):
            event(
                game,
                actor,
                "rejected",
                "Information non vérifiable",
                "Le message n’a pas été transmis car sa source n’est pas accessible au personnage.",
                causes=causes,
                round_number=round_number,
            )
            continue
        data = game["agents"][actor]
        action = intent.action
        if action == "wait":
            continue
        title, detail, effects = "Point de situation", intent.message, {}
        audience = ["player"]
        if action == "audit":
            game["risk_known"] = True
            if "critical" not in data["knowledge"]:
                data["knowledge"].append("critical")
            if "critical" not in game["player_knowledge"]:
                game["player_knowledge"].append("critical")
            title, detail = "L’audit confirme un risque critique", FACTS["critical"]
            data["activity"] = "Correctif et validation requis avant livraison."
        elif action == "verify":
            game["verified"] = True
            title, detail = (
                "La correction est validée",
                "Les contrôles du scénario confirment la correction. Le périmètre convenu doit encore être prêt.",
            )
            data["activity"] = "Validation de sécurité obtenue."
        elif action == "work":
            title = "Priorité prise en compte"
            detail = "Le développeur poursuit le travail affecté dans la capacité disponible."
            data["activity"] = (
                "Travaille sur le correctif."
                if game["priority"] == "fix" and game["tasks"]["fix"]["remaining"]
                else "Poursuit le périmètre de livraison."
            )
        elif action == "refuse":
            game["work_blocked"] = True
            title, detail = (
                "La surcharge bloque le travail",
                "Le développeur suspend l’exécution ce tour et demande une charge tenable.",
            )
            data["activity"] = "Demande une réduction de charge."
            effects = {"moral": adjust(game, "morale", -5)}
        elif action == "warn":
            title, detail = (
                "Le développeur demande un arbitrage",
                "Le correctif et le périmètre commercial se disputent la capacité disponible.",
            )
            data["activity"] = "Alerte sur les priorités concurrentes."
        elif action == "reveal_need":
            if "demo_acceptable" not in game["player_knowledge"]:
                game["player_knowledge"].append("demo_acceptable")
            title, detail = "L’échéance concerne une démonstration", FACTS["demo_acceptable"]
            effects = {"confiance": adjust(game, "trust", 4)}
            data["activity"] = "Ouverte à une démonstration de périmètre réduit."
        elif action == "accept_scope":
            game["scope"] = "partial"
            game["feature_committed"] = False
            game["tasks"]["core"]["remaining"] = max(0, game["tasks"]["core"]["remaining"] - 2)
            title, detail = (
                "Le périmètre réduit est accepté",
                "Le client accepte une démonstration limitée. Deux unités du socle et la fonctionnalité supplémentaire sortent de cette livraison.",
            )
            effects = {"confiance": adjust(game, "trust", 4)}
            data["activity"] = "Attend la démonstration convenue."
            game["proposals"].remove("reduce_scope")
        elif action == "accept_delay":
            game["delay_agreed"] = True
            title, detail = (
                "Une nouvelle échéance est acceptée",
                "Le client accepte de reporter la livraison. Le bilan aura lieu à la fin des six tours et précisera le travail restant.",
            )
            data["activity"] = "A accepté une nouvelle échéance."
            game["proposals"].remove("request_delay")
        elif action == "acknowledge":
            title, detail = (
                "Le client reçoit votre point de situation",
                "Les faits que vous connaissez ont été partagés. Le client dispose d’une information plus claire sur l’avancement.",
            )
            effects = {"confiance": adjust(game, "trust", 7)}
            data["activity"] = "Prend connaissance du point de situation."
        elif action in ("counter", "reject"):
            title, detail = (
                "Le client demande des garanties",
                "Le changement proposé n’est pas accepté. Un point de situation et une proposition étayée peuvent aider à rétablir la confiance.",
            )
            data["activity"] = "Attend des garanties avant de renégocier."
        elif action == "clarify_promise":
            title, detail = (
                "Le commercial clarifie son engagement",
                "Le commercial confirme la promesse initiale et propose de réaligner la communication sur le périmètre accepté.",
            )
            data["activity"] = "Aligne les engagements avec le client."
        elif action == "message":
            if not detail.strip():
                continue
            title = f"Message de {data['name']}"
            audience = [actor, intent.recipient]
        e = event(
            game,
            actor,
            action,
            title,
            detail,
            effects=effects,
            causes=causes,
            audience=audience,
            round_number=round_number,
        )
        if action == "audit":
            queue_message(game, actor, "developer", detail, ["critical"], e, round_number)
        elif action == "reveal_need":
            queue_message(game, actor, "sales", detail, ["demo_acceptable"], e, round_number)
        elif action == "clarify_promise":
            queue_message(game, actor, "client", detail, ["promise"], e, round_number)
        elif action == "message":
            queue_message(game, actor, intent.recipient, detail, intent.fact_ids, e, round_number)
    return game


def finalize_turn(original):
    game = deepcopy(original)
    if not game["released"]:
        capacity = 1 if "rest" in game["actions"] else 2
        capacity += int("reinforce" in game["actions"])
        if game["work_blocked"]:
            capacity = 0
        task_id = "fix" if game["priority"] == "fix" and game["tasks"]["fix"]["remaining"] else "core"
        if task_id == "core" and game["tasks"]["core"]["remaining"] == 0 and game["feature_committed"]:
            task_id = "feature"
        task = game["tasks"][task_id]
        units = min(task["remaining"], min(capacity, 1) if task_id == "fix" else capacity)
        task["remaining"] -= units
        if units:
            event(
                game,
                "engine",
                "work_progress",
                "Le travail avance",
                f"{task['title']} : {units} unité(s) réalisée(s), {task['remaining']} restante(s).",
                effects={"travail": units},
                causes=[
                    e["id"]
                    for e in game["events"]
                    if e["turn"] == game["turn"] + 1
                    and (
                        (e["actor"] == "developer" and e["type"] == "work")
                        or (
                            e["actor"] == "player"
                            and e["type"]
                            in {"prioritize_fix", "prioritize_core", "rest", "reinforce", "accept_feature"}
                        )
                    )
                ],
            )
        developer = game["agents"]["developer"]
        if "rest" not in game["actions"]:
            developer["stress"] = min(100, developer["stress"] + (12 if game["feature_committed"] else 5))
        adjust(game, "morale", -7 if developer["stress"] > 75 else -2)
    budget_effect = adjust(game, "budget", -12)
    if game["turn"] >= 2 and not game["delay_agreed"] and game["scope"] == "unagreed":
        trust_effect = adjust(game, "trust", -7)
        event(
            game,
            "client",
            "uncertain_commitment",
            "Le client attend un engagement clair",
            "L’échéance approche sans accord explicite sur le périmètre.",
            effects={"confiance": trust_effect},
        )
    event(
        game,
        "engine",
        "period_end",
        "La période se termine",
        "Une période de travail s’est écoulée. Les coûts récurrents sont comptabilisés une seule fois.",
        effects={"budget": budget_effect},
    )
    game["metrics"]["progress"] = round(100 * (12 - game["tasks"]["core"]["remaining"]) / 12)
    game["turn"] += 1
    game["version"] += 1
    if game["released"] or game["turn"] >= 6 or game["metrics"]["trust"] <= 10:
        game["status"] = "finished"
        if game["released"]:
            code, title = "delivered", "Livraison maîtrisée"
            if game["metrics"]["morale"] < 40:
                title = "Livraison au prix fort"
        elif game["metrics"]["trust"] <= 10:
            code, title = "contract_lost", "La relation client est rompue"
        elif game["delay_agreed"]:
            code, title = "delayed", "Report négocié"
        else:
            code, title = "blocked", "L’échéance n’est pas tenue"
        game["outcome"] = {"code": code, "title": title}
    return game
