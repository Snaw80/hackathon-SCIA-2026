export type GameEvent = {
  id: string;
  turn: number;
  round: number;
  actor: string;
  type: string;
  title: string;
  detail: string;
  effects: Record<string, number>;
  causes: string[];
};
export type Action = {
  id: string;
  title: string;
  description: string;
  cost: number;
  category: string;
  disabled: boolean;
  reason: string | null;
};
export type Character = {
  id: string;
  name: string;
  role: string;
  initials: string;
  color: string;
  stress: number;
  trust: number;
  activity: string;
  status: string;
};
export type Game = {
  id: string;
  version: number;
  turn: number;
  max_turns: number;
  status: "active" | "finished";
  mode: string;
  metrics: { progress: number; budget: number; trust: number; morale: number };
  security: { status: string; label: string; detail: string };
  agents: Character[];
  tasks: {
    id: string;
    title: string;
    remaining: number;
    total: number;
    status: string;
  }[];
  actions: Action[];
  events: GameEvent[];
  last_run: {
    rounds: number;
    agent_calls: number;
    fallbacks: number;
    duration_ms: number;
    steps: {
      node: string;
      agent?: string;
      round: number;
      label: string;
      status: string;
    }[];
  };
  outcome: { code: string; title: string } | null;
  debrief: {
    headline: string;
    summary: string;
    moments: {
      title: string;
      analysis: string;
      event_ids: string[];
      alternative: string;
    }[];
    source: string;
  } | null;
};
export type TurnRequest = {
  request_id: string;
  expected_version: number;
  actions: string[];
};
