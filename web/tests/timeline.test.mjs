import assert from "node:assert/strict";
import test from "node:test";
import { agentExpression, groupTimeline, presentationKind } from "../lib/timeline.ts";
import * as timeline from "../lib/timeline.ts";

const base = {
  effects: {},
  causes: [],
};

test("groups events by turn and round without reversing narrative order", () => {
  const events = [
    { ...base, id: "e0", turn: 0, round: 0, actor: "director", type: "briefing" },
    { ...base, id: "e1", turn: 1, round: 0, actor: "player", type: "player_command" },
    { ...base, id: "e2", turn: 1, round: 1, actor: "client", type: "message" },
    { ...base, id: "e3", turn: 1, round: 0, actor: "engine", type: "period_end" },
  ];

  assert.deepEqual(
    groupTimeline(events).map((turn) => ({
      turn: turn.turn,
      rounds: turn.rounds.map((round) => ({
        round: round.round,
        ids: round.events.map((event) => event.id),
      })),
    })),
    [
      { turn: 0, rounds: [{ round: 0, ids: ["e0"] }] },
      {
        turn: 1,
        rounds: [
          { round: 0, ids: ["e1"] },
          { round: 1, ids: ["e2"] },
          { round: 0, ids: ["e3"] },
        ],
      },
    ],
  );
  assert.deepEqual(events.map((event) => event.id), ["e0", "e1", "e2", "e3"]);
});

test("assigns stable narrative kinds to questions and answers", () => {
  assert.equal(presentationKind({ actor: "client", type: "agent_question" }), "question");
  assert.equal(presentationKind({ actor: "player", type: "player_answer" }), "answer");
  assert.equal(presentationKind({ actor: "engine", type: "work_progress" }), "engine");
  assert.equal(presentationKind({ actor: "developer", type: "work" }), "agent");
});

test("exposes grounded LLM expression only when all presentation fields exist", () => {
  assert.deepEqual(
    agentExpression({
      speech: "I found a critical vulnerability.",
      reason: "The defect has now been audited.",
      emotion: "urgent",
    }),
    {
      speech: "I found a critical vulnerability.",
      reason: "The defect has now been audited.",
      emotion: "urgent",
    },
  );
  assert.equal(agentExpression({ speech: "Incomplete" }), null);
});

test("selects one latest grounded response per agent from the newest expressive turn", () => {
  const events = [
    { ...base, id: "d1", turn: 1, actor: "developer", speech: "Earlier", reason: "Earlier reason", emotion: "worried" },
    { ...base, id: "d2", turn: 2, actor: "developer", speech: "First draft", reason: "Initial thought", emotion: "focused" },
    { ...base, id: "engine-2", turn: 2, actor: "engine", speech: "System", reason: "Rule", emotion: "neutral" },
    { ...base, id: "c2", turn: 2, actor: "client", speech: "Client answer", reason: "Scope matters", emotion: "concerned" },
    { ...base, id: "s2", turn: 2, actor: "sales", speech: "Sales answer", reason: "Trust matters", emotion: "confident" },
    { ...base, id: "sec2", turn: 2, actor: "security", speech: "Security answer", reason: "Risk matters", emotion: "alert" },
    { ...base, id: "d2-last", turn: 2, actor: "developer", speech: "Final answer", reason: "Best response", emotion: "determined" },
    { ...base, id: "incomplete", turn: 3, actor: "client", speech: "Missing context" },
  ];

  assert.equal(typeof timeline.latestAgentResponses, "function");
  const responses = timeline.latestAgentResponses?.(events) ?? [];

  assert.deepEqual(
    responses.map((response) => response.id),
    ["d2-last", "c2", "s2", "sec2"],
  );
});
