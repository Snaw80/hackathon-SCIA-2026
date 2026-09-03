from copy import deepcopy
import time
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, interrupt
from .agents import RulesPolicy
from .engine import prepare_turn, resolve_intents, finalize_turn
from .models import AgentIntent, TurnRequest
from .projection import public_view, build_debrief
from .scenario import ROLES, observation


def merge_packets(left, right):
    return {**left, **right}


class GraphState(TypedDict):
    game: dict
    request: dict
    round: int
    dispatch: list[dict]
    packets: Annotated[dict, merge_packets]
    started_at: float


def build_graph(store, policy, checkpointer):
    fallback = RulesPolicy()

    def await_player(state):
        decision = interrupt(public_view(state["game"]))
        return {"request": decision}

    def prepare(state):
        game = prepare_turn(state["game"], TurnRequest.model_validate(state["request"]))
        game["last_run"]["steps"].append(
            {"node": "validate_decision", "round": 0, "label": "Decisions validated", "status": "ok"}
        )
        return {"game": game, "round": 1, "started_at": time.time()}

    def organize(state):
        game = deepcopy(state["game"])
        round_number = state["round"]
        selected = (
            list(ROLES)
            if round_number == 1
            else [actor for actor in ROLES if any(m["to"] == actor for m in game["pending_messages"])]
        )
        dispatch = []
        pending = game["pending_messages"]
        for actor in selected:
            inbox = [m for m in pending if m["to"] == actor]
            for message in inbox:
                for fact in message["fact_ids"]:
                    if fact not in game["agents"][actor]["knowledge"]:
                        game["agents"][actor]["knowledge"].append(fact)
            dispatch.append({"context": observation(game, actor, round_number, inbox)})
        game["pending_messages"] = [m for m in pending if m["to"] not in selected]
        game["last_run"]["steps"].append(
            {
                "node": "organizer",
                "round": round_number,
                "label": f"Dispatch to {len(selected)} character(s)",
                "status": "ok",
            }
        )
        return {"game": game, "dispatch": dispatch}

    def distribute(state):
        return [Send("agent", item) for item in state["dispatch"]] or "finalize"

    def agent(worker):
        context = worker["context"]
        used_fallback = False
        try:
            intent = AgentIntent.model_validate(policy.decide(deepcopy(context)))
            if intent.action not in context["allowed_actions"] or any(
                key not in context["facts"] for key in intent.fact_ids
            ):
                raise ValueError("Invalid model intention")
        except Exception:
            used_fallback = True
            intent = fallback.decide(context)
        packet = {
            "actor": context["actor"],
            "intent": intent.model_dump(),
            "fallback": used_fallback,
            "turn": context["turn"],
            "round": context["round"],
            "causes": [m["cause"] for m in context["inbox"]],
        }
        key = f"{context['turn']}:{context['round']}:{context['actor']}"
        return {"packets": {key: packet}}

    def resolve(state):
        game = state["game"]
        packets = {
            p["actor"]: p
            for p in state["packets"].values()
            if p["turn"] == game["turn"] + 1 and p["round"] == state["round"]
        }
        expected = {item["context"]["actor"] for item in state["dispatch"]}
        if set(packets) != expected:
            raise RuntimeError("Incomplete dispatch barrier")
        game = resolve_intents(game, packets, state["round"])
        run = game["last_run"]
        run["rounds"] = state["round"]
        run["agent_calls"] += len(packets)
        run["fallbacks"] += sum(p["fallback"] for p in packets.values())
        for actor in ROLES:
            if actor in packets:
                run["steps"].append(
                    {
                        "node": "agent",
                        "agent": actor,
                        "round": state["round"],
                        "label": f"{ROLES[actor]['name']} · {ROLES[actor]['role']}",
                        "status": "fallback" if packets[actor]["fallback"] else "ok",
                    }
                )
        run["steps"].append(
            {
                "node": "resolve_round",
                "round": state["round"],
                "label": "Intentions validated and effects applied",
                "status": "ok",
            }
        )
        return {"game": game, "round": state["round"] + 1}

    def next_step(state):
        return (
            "organize"
            if state["round"] <= 2 and state["game"]["pending_messages"] and not state["game"]["released"]
            else "finalize"
        )

    def finalize(state):
        game = finalize_turn(state["game"])
        game["last_run"]["duration_ms"] = max(0, round((time.time() - state["started_at"]) * 1000))
        game["last_run"]["steps"].append(
            {"node": "finalize_turn", "round": 0, "label": "One work period elapsed", "status": "ok"}
        )
        return {"game": game}

    def coach(state):
        game = deepcopy(state["game"])
        debrief = build_debrief(game)
        if hasattr(policy, "coach"):
            try:
                debrief = policy.coach(debrief)
            except Exception:
                debrief["source"] = "rules_fallback"
        game["debrief"] = debrief
        return {"game": game}

    def commit(state):
        game = deepcopy(state["game"])
        game["last_run"]["steps"].append(
            {
                "node": "commit_state",
                "round": 0,
                "label": "State saved · return to player",
                "status": "ok",
            }
        )
        return {"game": store.commit(game, state["request"])}

    graph = StateGraph(GraphState)
    for name, node in [
        ("await_player", await_player),
        ("prepare", prepare),
        ("organize", organize),
        ("agent", agent),
        ("resolve", resolve),
        ("finalize", finalize),
        ("coach", coach),
        ("commit", commit),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "await_player")
    graph.add_edge("await_player", "prepare")
    graph.add_conditional_edges(
        "prepare", lambda state: "finalize" if state["game"]["released"] else "organize"
    )
    graph.add_conditional_edges("organize", distribute, ["agent", "finalize"])
    graph.add_edge("agent", "resolve")
    graph.add_conditional_edges("resolve", next_step)
    graph.add_conditional_edges(
        "finalize", lambda state: "coach" if state["game"]["status"] == "finished" else "commit"
    )
    graph.add_edge("coach", "commit")
    graph.add_conditional_edges(
        "commit", lambda state: END if state["game"]["status"] == "finished" else "await_player"
    )
    return graph.compile(checkpointer=checkpointer)
