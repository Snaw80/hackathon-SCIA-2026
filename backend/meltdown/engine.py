from copy import deepcopy
from .models import AgentIntent, AnswerRequest, TurnRequest
from .scenario import ACTIONS, FACTS, action_reason, allowed_intents, observation


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
        raise ValueError("This game has advanced. The latest version has been reloaded.")
    if original["status"] != "active":
        raise ValueError("This game is over.")
    for action in request.actions:
        if reason := action_reason(original, action):
            raise ValueError(reason)
    if sum(ACTIONS[a][2] for a in request.actions) > original["metrics"]["budget"]:
        raise ValueError("The budget does not cover both decisions.")
    if {"prioritize_fix", "prioritize_core"} <= set(request.actions):
        raise ValueError("The developer cannot receive two competing priorities.")
    if {"reduce_scope", "accept_feature"} <= set(request.actions):
        raise ValueError("Choose a single scope commitment.")
    game = deepcopy(original)
    game["actions"] = list(request.actions)
    game["action_event_ids"] = []
    game["proposals"] = [a for a in request.actions if a in ("reduce_scope", "request_delay")]
    game["work_blocked"] = False
    game["pending_questions"] = []
    game["answer_followup"] = False
    game["last_run"] = {"rounds": 0, "agent_calls": 0, "fallbacks": 0, "duration_ms": 0, "steps": []}
    command_causes = []
    if request.command:
        command_event = event(
            game,
            "player",
            "player_command",
            "Your instruction",
            request.command,
        )
        command_causes = [command_event["id"]]
        if request.interpretation:
            interpretation_event = event(
                game,
                "engine",
                "command_interpretation",
                "Instruction understood",
                request.interpretation,
                causes=command_causes,
            )
            command_causes = [interpretation_event["id"]]
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
            causes=command_causes,
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
                "Action cannot be applied",
                "The project rules do not allow this action in the current state.",
                causes=causes,
                round_number=round_number,
            )
            continue
        if any(fact not in original["agents"][actor]["knowledge"] for fact in intent.fact_ids):
            event(
                game,
                actor,
                "rejected",
                "Unverifiable information",
                "The message was not delivered because its source is unavailable to this character.",
                causes=causes,
                round_number=round_number,
            )
            continue
        data = game["agents"][actor]
        action = intent.action
        if action == "wait":
            continue
        if action == "ask_player":
            duplicate = any(
                question["actor"] == actor
                and question["question"].strip().casefold() == intent.question.strip().casefold()
                for question in game["pending_questions"]
            )
            if duplicate or len(game["pending_questions"]) >= 3:
                continue
            question = {
                "id": f"q-{game['turn'] + 1}-{round_number}-{actor}",
                "actor": actor,
                "question": intent.question.strip(),
                "reason": intent.question_reason.strip(),
                "turn": game["turn"] + 1,
                "round": round_number,
            }
            game["pending_questions"].append(question)
            event(
                game,
                actor,
                "agent_question",
                f"Question from {data['name']}",
                question["question"],
                causes=causes,
                round_number=round_number,
            )
            data["activity"] = "Waiting for your answer."
            continue
        title, detail, effects = "Status update", intent.message, {}
        audience = ["player"]
        if action == "audit":
            game["risk_known"] = True
            if "critical" not in data["knowledge"]:
                data["knowledge"].append("critical")
            if "critical" not in game["player_knowledge"]:
                game["player_knowledge"].append("critical")
            title, detail = "The audit confirms a critical risk", FACTS["critical"]
            data["activity"] = "A fix and verification are required before release."
        elif action == "verify":
            game["verified"] = True
            title, detail = (
                "The fix is verified",
                "The scenario checks confirm the fix. The agreed scope must also be ready.",
            )
            data["activity"] = "Security approval obtained."
        elif action == "work":
            title = "Priority acknowledged"
            detail = "The developer continues the assigned work within available capacity."
            data["activity"] = (
                "Working on the fix."
                if game["priority"] == "fix" and game["tasks"]["fix"]["remaining"]
                else "Working on the delivery scope."
            )
        elif action == "refuse":
            game["work_blocked"] = True
            title, detail = (
                "Overload blocks progress",
                "The developer pauses work this turn and asks for a sustainable workload.",
            )
            data["activity"] = "Asking for a lighter workload."
            effects = {"morale": adjust(game, "morale", -5)}
        elif action == "warn":
            title, detail = (
                "The developer asks for a decision",
                "The fix and commercial commitments compete for the available capacity.",
            )
            data["activity"] = "Flagging competing priorities."
        elif action == "reveal_need":
            if "demo_acceptable" not in game["player_knowledge"]:
                game["player_knowledge"].append("demo_acceptable")
            title, detail = "The deadline is for a demonstration", FACTS["demo_acceptable"]
            effects = {"trust": adjust(game, "trust", 4)}
            data["activity"] = "Open to a demonstration with a smaller scope."
        elif action == "accept_scope":
            game["scope"] = "partial"
            game["feature_committed"] = False
            game["tasks"]["core"]["remaining"] = max(0, game["tasks"]["core"]["remaining"] - 2)
            title, detail = (
                "The reduced scope is accepted",
                "The client accepts a limited demonstration. Two core work units and the extra feature are removed from this delivery.",
            )
            effects = {"trust": adjust(game, "trust", 4)}
            data["activity"] = "Waiting for the agreed demonstration."
            game["proposals"].remove("reduce_scope")
        elif action == "accept_delay":
            game["delay_agreed"] = True
            title, detail = (
                "A new deadline is accepted",
                "The client agrees to postpone delivery. The review at the end of six turns will identify any remaining work.",
            )
            data["activity"] = "Agreed to a new deadline."
            game["proposals"].remove("request_delay")
        elif action == "acknowledge":
            title, detail = (
                "The client receives your update",
                "Your known facts have been shared. The client now has a clearer picture of progress.",
            )
            effects = {"trust": adjust(game, "trust", 7)}
            data["activity"] = "Reviewing the status update."
        elif action in ("counter", "reject"):
            title, detail = (
                "The client asks for assurances",
                "The proposed change is not accepted. A status update and an evidence-backed proposal may help rebuild trust.",
            )
            data["activity"] = "Waiting for assurances before renegotiating."
        elif action == "clarify_promise":
            title, detail = (
                "The sales lead clarifies the commitment",
                "The sales lead confirms the original promise and proposes aligning communication with the agreed scope.",
            )
            data["activity"] = "Aligning commitments with the client."
        elif action == "message":
            if not detail.strip():
                continue
            title = f"Message from {data['name']}"
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


def apply_player_answers(original, request: AnswerRequest, round_number):
    game = deepcopy(original)
    pending = {question["id"]: question for question in game["pending_questions"]}
    supplied = {answer.question_id: answer for answer in request.answers}
    if set(supplied) != set(pending):
        raise ValueError("Submit one answer for every pending agent question.")
    dispatch = []
    for question in game["pending_questions"]:
        answer = supplied[question["id"]]
        answer_event = event(
            game,
            "player",
            "player_answer",
            f"Your answer to {game['agents'][question['actor']]['name']}",
            answer.text,
            causes=[
                item["id"]
                for item in game["events"]
                if item["type"] == "agent_question"
                and item["actor"] == question["actor"]
                and item["turn"] == question["turn"]
                and item["round"] == question["round"]
            ][-1:],
            audience=["player", question["actor"]],
            round_number=round_number,
        )
        inbox = [
            {
                "id": f"answer-{question['id']}",
                "from": "player",
                "to": question["actor"],
                "text": answer.text,
                "fact_ids": [],
                "cause": answer_event["id"],
                "turn": game["turn"] + 1,
                "round": round_number,
            }
        ]
        dispatch.append(
            {
                "context": observation(
                    game,
                    question["actor"],
                    round_number,
                    inbox,
                    allow_questions=False,
                )
            }
        )
    game["pending_questions"] = []
    game["answer_followup"] = True
    return game, dispatch


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
                "Work progresses",
                f"{task['title']} : {units} unit(s) completed, {task['remaining']} remaining.",
                effects={"work": units},
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
            "The client needs a clear commitment",
            "The deadline is approaching without an explicit scope agreement.",
            effects={"trust": trust_effect},
        )
    event(
        game,
        "engine",
        "period_end",
        "The period ends",
        "One work period has passed. Recurring costs are charged once.",
        effects={"budget": budget_effect},
    )
    game["metrics"]["progress"] = round(100 * (12 - game["tasks"]["core"]["remaining"]) / 12)
    game["turn"] += 1
    game["version"] += 1
    if game["released"] or game["turn"] >= 6 or game["metrics"]["trust"] <= 10:
        game["status"] = "finished"
        if game["released"]:
            code, title = "delivered", "Delivery under control"
            if game["metrics"]["morale"] < 40:
                title = "Delivery at a high cost"
        elif game["metrics"]["trust"] <= 10:
            code, title = "contract_lost", "The client relationship has broken down"
        elif game["delay_agreed"]:
            code, title = "delayed", "Extension negotiated"
        else:
            code, title = "blocked", "The deadline is missed"
        game["outcome"] = {"code": code, "title": title}
    return game
