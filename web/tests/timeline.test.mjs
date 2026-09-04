import assert from "node:assert/strict";
import test from "node:test";
import { groupTimeline, presentationKind } from "../lib/timeline.ts";

const base = {
  effects: {},
  causes: [],
};

test("groups events by turn and round without reversing narrative order", () => {
  const events = [
    { ...base, id: "e0", turn: 0, round: 0, actor: "director", type: "briefing" },
    { ...base, id: "e1", turn: 1, round: 0, actor: "player", type: "player_command" },
    { ...base, id: "e2", turn: 1, round: 1, actor: "client", type: "message" },
    { ...base, id: "e3", turn: 1, round: 2, actor: "engine", type: "period_end" },
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
          { round: 2, ids: ["e3"] },
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
