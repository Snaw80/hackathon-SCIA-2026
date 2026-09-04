import type { GameEvent } from "./types.ts";

export type TimelineRound = { round: number; events: GameEvent[] };
export type TimelineTurn = { turn: number; rounds: TimelineRound[] };
export type PresentationKind =
  | "player"
  | "question"
  | "answer"
  | "engine"
  | "agent";

export function groupTimeline(events: GameEvent[]): TimelineTurn[] {
  const turns = new Map<number, Map<number, GameEvent[]>>();
  for (const event of events) {
    const rounds = turns.get(event.turn) ?? new Map<number, GameEvent[]>();
    const items = rounds.get(event.round) ?? [];
    items.push(event);
    rounds.set(event.round, items);
    turns.set(event.turn, rounds);
  }
  return [...turns.entries()]
    .sort(([left], [right]) => left - right)
    .map(([turn, rounds]) => ({
      turn,
      rounds: [...rounds.entries()]
        .sort(([left], [right]) => left - right)
        .map(([round, items]) => ({ round, events: items })),
    }));
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
