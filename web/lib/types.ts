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
export type RunPhase =
  | "interpreting"
  | "needs_confirmation"
  | "round_active"
  | "awaiting_answers"
  | "resolving"
  | "complete"
  | "failed";
export type AgentQuestion = {
  id: string;
  actor: string;
  question: string;
  reason: string;
  turn: number;
  round: number;
};
export type ActiveRun = {
  id: string;
  phase: RunPhase;
  command: string;
  interpretation: {
    summary: string;
    actions: string[];
    confidence: "clear" | "ambiguous";
    reason: string | null;
  } | null;
  active_agents: string[];
  progress: { label: string; status: string }[];
  questions: AgentQuestion[];
  error: string | null;
  created_at: number;
  updated_at: number;
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
  active_run: ActiveRun | null;
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
  command: string;
};
export type ConfirmationRequest = {
  request_id: string;
  confirm?: boolean;
  command?: string;
};
export type AnswersRequest = {
  request_id: string;
  answers: { question_id: string; text: string }[];
};
