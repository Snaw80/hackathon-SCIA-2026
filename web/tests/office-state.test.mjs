import test from "node:test";
import assert from "node:assert/strict";
import { projectOffice } from "../lib/office-state.ts";

function fixture() {
  return {
    turn: 2,
    status: "active",
    outcome: null,
    metrics: { progress: 67 },
    security: { status: "unknown" },
    agents: ["developer", "client", "sales", "security"].map((id) => ({
      id,
      name: id,
      stress: 35,
      activity: "At work",
    })),
    events: [],
  };
}

test("presentation uses public security status and does not mutate the game", () => {
  const game = fixture();
  const before = structuredClone(game);
  const room = projectOffice(game);
  assert.equal(room.security, "unknown");
  assert.equal(room.characters.length, 4);
  assert.deepEqual(game, before);
});
test("only current-turn public negotiation moves its participants to the table", () => {
  const game = fixture();
  game.events = [
    { id: "e1", turn: 1, actor: "client", type: "accept_scope" },
    { id: "e2", turn: 2, actor: "sales", type: "clarify_promise" },
  ];
  const room = projectOffice(game);
  assert.equal(room.characters.find((a) => a.id === "client").atTable, false);
  assert.equal(room.characters.find((a) => a.id === "client").event, null);
  assert.equal(room.characters.find((a) => a.id === "sales").atTable, true);
  assert.equal(room.characters.find((a) => a.id === "sales").event.id, "e2");
});
test("overload is visible and a refusal stops the working pose", () => {
  const game = fixture();
  game.agents[0].stress = 88;
  game.events = [{ id: "e3", turn: 2, actor: "developer", type: "refuse" }];
  const actor = projectOffice(game).characters[0];
  assert.equal(actor.pressure, "High");
  assert.equal(actor.pose, "blocked");
});
test("a completed delivery overrides activity poses and preserves the final public risk", () => {
  const game = fixture();
  game.status = "finished";
  game.outcome = { code: "delivered" };
  game.security.status = "safe";
  const room = projectOffice(game);
  assert.equal(room.delivered, true);
  assert.equal(room.security, "safe");
  assert.ok(room.characters.every((a) => a.pose === "celebrate"));
});
test("a missed deadline does not animate a successful delivery", () => {
  const game = fixture();
  game.status = "finished";
  game.outcome = { code: "blocked" };
  const room = projectOffice(game);
  assert.equal(room.delivered, false);
  assert.ok(room.characters.every((a) => a.pose === "idle"));
});
