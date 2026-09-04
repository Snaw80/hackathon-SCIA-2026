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
