import type { GameEvent } from "./types.ts";

export type TimelineRound = { round: number; events: GameEvent[] };
export type TimelineTurn = { turn: number; rounds: TimelineRound[] };
export type PresentationKind =
  | "player"
  | "question"
  | "answer"
  | "engine"
  | "agent";

export function agentExpression(
  event: Pick<GameEvent, "speech" | "reason" | "emotion">,
) {
  if (!event.speech || !event.reason || !event.emotion) return null;
  return {
    speech: event.speech,
    reason: event.reason,
    emotion: event.emotion,
  };
}

const councilActors = ["developer", "client", "sales", "security"] as const;

export function latestAgentResponses(events: GameEvent[]): GameEvent[] {
  const allowedActors = new Set<string>(councilActors);
  let latestTurn = -1;

  for (const event of events) {
    if (allowedActors.has(event.actor) && agentExpression(event)) {
      latestTurn = Math.max(latestTurn, event.turn);
    }
  }

  if (latestTurn < 0) return [];

  const latestByActor = new Map<string, GameEvent>();
  for (const event of events) {
    if (
      event.turn === latestTurn &&
      allowedActors.has(event.actor) &&
      agentExpression(event)
    ) {
      latestByActor.set(event.actor, event);
    }
  }

  return councilActors.flatMap((actor) => {
    const response = latestByActor.get(actor);
    return response ? [response] : [];
  });
}

export function groupTimeline(events: GameEvent[]): TimelineTurn[] {
  const turns: TimelineTurn[] = [];
  for (const event of events) {
    let turn = turns.at(-1);
    if (!turn || turn.turn !== event.turn) {
      turn = { turn: event.turn, rounds: [] };
      turns.push(turn);
    }
    let round = turn.rounds.at(-1);
    if (!round || round.round !== event.round) {
      round = { round: event.round, events: [] };
      turn.rounds.push(round);
    }
    round.events.push(event);
  }
  return turns;
}

export function presentationKind(
  event: Pick<GameEvent, "actor" | "type">,
): PresentationKind {
  if (event.type === "agent_question") return "question";
  if (event.type === "player_answer") return "answer";
  if (event.actor === "player") return "player";
  if (event.actor === "engine" || event.actor === "director") return "engine";
  return "agent";
}
