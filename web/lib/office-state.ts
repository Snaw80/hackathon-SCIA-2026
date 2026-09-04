import type { Character, Game, GameEvent } from "./types";

export type Position = [number, number, number];
export type OfficeCharacter = Character & {
  home: Position;
  position: Position;
  atTable: boolean;
  pressure: "Low" | "Moderate" | "High";
  pose: "idle" | "working" | "talking" | "blocked" | "celebrate";
  event: GameEvent | null;
};
const stations: Record<string, Position> = {
  developer: [-3.65, 0, -0.5],
  security: [3.65, 0, -0.5],
  client: [-3.65, 0, 2.9],
  sales: [3.65, 0, 2.9],
};
const negotiations = new Set([
  "accept_scope",
  "accept_delay",
  "counter",
  "reject",
  "acknowledge",
  "clarify_promise",
]);

/** Presentation only: no writes, hidden state, inferred message recipients, or new rules. */
export function projectOffice(game: Game, activeAgents: string[] = []) {
  const delivered = game.outcome?.code === "delivered";
  const active = new Set(activeAgents);
  const characters: OfficeCharacter[] = game.agents.map((agent) => {
    const event =
      game.events.findLast(
        (e) => e.actor === agent.id && e.turn === game.turn,
      ) ?? null;
    const atTable =
      game.status === "active" &&
      ["client", "sales"].includes(agent.id) &&
      !!event &&
      negotiations.has(event.type);
    const pose = delivered
      ? "celebrate"
      : game.status === "finished"
        ? "idle"
        : event?.type === "refuse"
          ? "blocked"
          : active.has(agent.id)
            ? ["client", "sales"].includes(agent.id)
              ? "talking"
              : "working"
          : atTable || ["message", "warn"].includes(event?.type ?? "")
            ? "talking"
            : ["work", "audit", "verify"].includes(event?.type ?? "")
              ? "working"
              : "idle";
    const home: Position = stations[agent.id] ?? [0, 0, 0];
    return {
      ...agent,
      home,
      position: atTable ? [agent.id === "client" ? -0.9 : 0.9, 0, 1.45] : home,
      atTable,
      pose,
      event,
      pressure:
        agent.stress > 70 ? "High" : agent.stress > 40 ? "Moderate" : "Low",
    };
  });
  return {
    characters,
    delivered,
    security: game.security.status,
    progress: game.metrics.progress,
  };
}
