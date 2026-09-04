# Natural Command Round Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace predefined player action cards with validated natural-language commands, expose persisted live run progress, pause once for aggregated agent questions, and present events as a turn-and-round timeline.

**Architecture:** A structured interpreter maps player text onto the existing canonical action registry before the deterministic engine validates it. A persisted `active_run` record and an in-process worker let the API return immediately while polling exposes real progress and LangGraph pause boundaries. Agent questions are collected at a dispatch barrier, answered together, and followed by one targeted non-questioning response phase before finalization.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic 2, LangGraph 1, SQLite/WAL, pytest, Next.js 16, React 19, TypeScript 5.9, Node test runner.

**Spec:** `docs/superpowers/specs/2026-09-04-natural-command-round-interaction-design.md`

## Global Constraints

- Canonical actions and all metric effects remain deterministic in `scenario.py` and `engine.py`.
- A command maps to zero, one, or two existing action IDs; unknown or conflicting interpretations never execute silently.
- Work, recurring cost, time, version, and end-state evaluation advance exactly once per completed turn.
- At most three questions are exposed per turn, all are answered together, and agents cannot ask again in the answer follow-up.
- Polling is the only live transport; SSE, WebSockets, token streaming, distributed workers, and multiple Uvicorn workers are out of scope.
- Public responses and exports never expose private goals, private facts, hidden messages, prompts, or chain-of-thought.

---

### Task 1: Structured Natural-Language Command Interpretation

**Files:**
- Modify: `backend/meltdown/models.py`
- Modify: `backend/meltdown/agents.py`
- Create: `backend/meltdown/interpreter.py`
- Test: `backend/tests/test_interpreter.py`

**Interfaces:**
- Consumes: `scenario.ACTIONS`, `scenario.action_reason(game, action)` and the public game state.
- Produces: `CommandRequest`, `CommandInterpretation`, and `interpret_command(game, command, policy) -> CommandInterpretation`.

- [x] **Step 1: Write failing schema and interpreter tests**

```python
def test_rules_interpreter_maps_two_management_intents():
    result = interpret_command(new_game("g"), "Audit the defect and put Alex on the security fix", RulesPolicy())
    assert result.actions == ["audit", "prioritize_fix"]
    assert result.confidence == "clear"

def test_rules_interpreter_refuses_to_guess_unknown_instruction():
    result = interpret_command(new_game("g"), "Do something clever", RulesPolicy())
    assert result.actions == []
    assert result.confidence == "ambiguous"
```

- [x] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest backend/tests/test_interpreter.py -q`  
Expected: collection fails because the interpreter schemas/module do not exist.

- [x] **Step 3: Add strict command schemas and deterministic phrase matching**

```python
class CommandRequest(BaseModel):
    request_id: str
    expected_version: int
    command: str = Field(min_length=1, max_length=1000)

class CommandInterpretation(BaseModel):
    summary: str = Field(min_length=1, max_length=300)
    actions: list[str] = Field(max_length=2)
    confidence: Literal["clear", "ambiguous"]
    reason: str | None = Field(default=None, max_length=300)
```

Implement normalized phrase scoring in `interpreter.py`, preserve command order, validate IDs against `ACTIONS`, and return ambiguity for no match, ties, unavailable actions, or invalid combinations. Add a structured LLM interpreter method to `LangChainPolicy`; validate its output and fall back to rules on any provider or parsing failure.

- [x] **Step 4: Run interpreter and agent tests**

Run: `uv run pytest backend/tests/test_interpreter.py backend/tests/test_agents.py -q`  
Expected: all tests pass with no external HTTP.

- [x] **Step 5: Commit the interpreter**

```bash
git add backend/meltdown/models.py backend/meltdown/agents.py backend/meltdown/interpreter.py backend/tests/test_interpreter.py
git commit -m "feat: interpret player commands safely"
```

### Task 2: Aggregate Agent Questions and Resume with Answers

**Files:**
- Modify: `backend/meltdown/models.py`
- Modify: `backend/meltdown/scenario.py`
- Modify: `backend/meltdown/agents.py`
- Modify: `backend/meltdown/engine.py`
- Modify: `backend/meltdown/graph.py`
- Test: `backend/tests/test_engine.py`
- Test: `backend/tests/test_graph.py`

**Interfaces:**
- Consumes: validated `AgentIntent`, `resolve_intents`, graph dispatch barriers, and per-agent observations.
- Produces: `Question`, `AnswerRequest`, `game["pending_questions"]`, and a LangGraph `await_answers` interrupt.

- [x] **Step 1: Write failing question lifecycle tests**

```python
def test_question_intents_are_collected_and_limited():
    game = new_game("questions")
    packets = {
        "client": {"intent": {"action": "ask_player", "question": "Is a demo enough?",
                                "question_reason": "I need to agree scope."}, "causes": []}
    }
    waiting = resolve_intents(game, packets, 1)
    assert [(q["actor"], q["question"]) for q in waiting["pending_questions"]] == [
        ("client", "Is a demo enough?")
    ]

def test_answer_followup_observation_targets_requesting_agent():
    game = new_game("answers")
    game["pending_questions"] = [{"id": "q1", "actor": "client", "question": "Is a demo enough?"}]
    resumed, dispatch = apply_player_answers(game, AnswerRequest(
        request_id="a1", answers=[{"question_id": "q1", "text": "A demo is enough."}]
    ))
    assert [item["context"]["actor"] for item in dispatch] == ["client"]
    assert dispatch[0]["context"]["player_answer"] == "A demo is enough."
```

- [x] **Step 2: Run focused tests and confirm failure**

Run: `uv run pytest backend/tests/test_engine.py backend/tests/test_graph.py -q`  
Expected: tests fail because question fields and the answer interrupt do not exist.

- [x] **Step 3: Implement bounded question collection**

Extend `AgentIntent` with optional `question` and `question_reason`, add `ask_player` to allowed intent descriptions, and initialize `pending_questions`, `answered_question_actors`, and `answer_followup` in game state. In `resolve_intents`, turn valid `ask_player` packets into public question events, deduplicate by actor plus normalized question, and retain at most three.

Add `await_answers` after `resolve`: interrupt once when pending questions exist. On resume, validate a complete `AnswerRequest`, create player answer events, build targeted inbox entries for the requesting agents, clear pending questions, set `answer_followup=True`, and dispatch only those agents with `ask_player` removed. Finalize immediately after that response phase.

- [x] **Step 4: Run engine and graph tests**

Run: `uv run pytest backend/tests/test_engine.py backend/tests/test_graph.py -q`  
Expected: all tests pass, including existing two-round and once-only finalization tests.

- [x] **Step 5: Commit the question lifecycle**

```bash
git add backend/meltdown/models.py backend/meltdown/scenario.py backend/meltdown/agents.py backend/meltdown/engine.py backend/meltdown/graph.py backend/tests/test_engine.py backend/tests/test_graph.py
git commit -m "feat: pause rounds for agent questions"
```

### Task 3: Persisted Asynchronous Runs and Polling API

**Files:**
- Modify: `backend/meltdown/store.py`
- Modify: `backend/meltdown/service.py`
- Modify: `backend/meltdown/projection.py`
- Modify: `backend/meltdown/api.py`
- Test: `backend/tests/test_api.py`
- Test: `backend/tests/test_graph.py`

**Interfaces:**
- Consumes: `CommandRequest`, `CommandInterpretation`, LangGraph checkpoints, `AnswerRequest`, and canonical game commits.
- Produces: `GameService.start_turn`, `confirm`, `answer`, `retry`, public `active_run`, and HTTP 202 mutation endpoints.

- [x] **Step 1: Write failing API phase and idempotency tests**

```python
def test_command_returns_202_and_can_be_polled_to_completion(client):
    game = client.post("/api/games").json()
    response = client.post(f"/api/games/{game['id']}/turns", json={
        "request_id": "run-1", "expected_version": 0,
        "command": "Audit the defect and prioritize the fix"
    })
    assert response.status_code == 202
    completed = poll_game(client, game["id"], "complete")
    assert completed["turn"] == 1
    assert completed["active_run"]["interpretation"]["actions"] == ["audit", "prioritize_fix"]
```

Add separate tests for `needs_confirmation`, answers, retry, concurrent-turn rejection, restart recovery, matching duplicate requests, and conflicting request fingerprints.

- [x] **Step 2: Run API and service tests and confirm failure**

Run: `uv run pytest backend/tests/test_api.py backend/tests/test_graph.py -q`  
Expected: request validation or missing service methods fail.

- [x] **Step 3: Add persisted run storage and public projection**

Create a `runs` SQLite table with `id`, `game_id`, `request_id`, `fingerprint`, `phase`, and JSON `data`. Add atomic methods `create_run`, `load_run`, `active_run`, `update_run`, and `claim_run`. Public projection must filter run data to phase, command, interpretation, active agents, progress, questions, recoverable error, and timestamps.

- [x] **Step 4: Add worker-backed service transitions and endpoints**

Use a bounded `ThreadPoolExecutor` owned by `GameService`. `start_turn` persists before scheduling and returns immediately. Worker transitions call the interpreter, pause on ambiguity, resume the existing graph, and persist every phase boundary. `confirm`, `answer`, and `retry` validate the active phase and schedule continuation. `close` shuts down accepted work before closing SQLite connections.

Update FastAPI routes to return HTTP 202 for run mutations and preserve 404/409 error semantics.

- [x] **Step 5: Run backend tests**

Run: `uv run pytest -q`  
Expected: all backend tests pass and tests remain independent of provider credentials.

- [x] **Step 6: Commit asynchronous runs**

```bash
git add backend/meltdown/store.py backend/meltdown/service.py backend/meltdown/projection.py backend/meltdown/api.py backend/tests/test_api.py backend/tests/test_graph.py
git commit -m "feat: persist and poll active turn runs"
```

### Task 4: Command Composer and Active Run UI

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`
- Create: `web/lib/timeline.ts`
- Create: `web/components/command-panel.tsx`
- Modify: `web/components/dashboard.tsx`
- Modify: `web/components/office/office-view.tsx`
- Modify: `web/lib/office-state.ts`
- Modify: `web/app/globals.css`
- Test: `web/tests/timeline.test.mjs`
- Test: `web/tests/office-state.test.mjs`

**Interfaces:**
- Consumes: public `Game.active_run`, command/confirmation/answer/retry endpoints, and existing office agent IDs.
- Produces: `CommandPanel`, `groupTimeline(events)`, polling transitions, draft preservation, and active-agent highlighting.

- [x] **Step 1: Read the installed Next.js 16 guidance relevant to client components and polling**

Run: `rg -n "useEffect|client component|poll" web/node_modules/next/dist/docs -g '*.md' | head -80`  
Expected: identify the applicable installed documentation before editing the client component.

- [x] **Step 2: Write failing pure timeline tests**

```javascript
test("groups events by turn and round in chronological order", () => {
  assert.deepEqual(groupTimeline(events), [
    { turn: 1, rounds: [{ round: 0, events: [events[0]] }, { round: 1, events: [events[1]] }] },
  ]);
});
```

- [x] **Step 3: Run frontend tests and confirm failure**

Run: `npm --prefix web test`  
Expected: timeline test fails because `groupTimeline` does not exist.

- [x] **Step 4: Add public run types, API methods, and pure grouping helper**

Define `RunPhase`, `ActiveRun`, `AgentQuestion`, command/confirmation/answers payloads, and make `Game.active_run` nullable. Add `api.command`, `api.confirm`, `api.answer`, and `api.retry`. Implement stable ascending grouping in `timeline.ts` without mutating `Game.events`.

- [x] **Step 5: Build the command and polling state UI**

`CommandPanel` owns command and answer drafts but receives phase and callbacks. Clear commands show the interpretation receipt; ambiguous commands show editable confirm/reinterpret controls; running phases show active agents and progress; awaiting answers renders all fields and submits them together; failed runs expose retry.

In `Dashboard`, replace selected action state/cards with command mutation state. Poll every 750 ms in `interpreting`, `round_active`, and `resolving`, then stop at player-input or terminal boundaries. Preserve drafts on transient failure. Pass `active_run.active_agents` into the office visualization.

- [x] **Step 6: Run tests, typecheck, and build**

Run: `npm --prefix web test && npm --prefix web run typecheck && npm --prefix web run build`  
Expected: all commands pass.

- [x] **Step 7: Commit the command experience**

```bash
git add web/lib/types.ts web/lib/api.ts web/lib/timeline.ts web/components/command-panel.tsx web/components/dashboard.tsx web/components/office web/app/globals.css web/tests
git commit -m "feat: add natural command round interface"
```

### Task 5: Narrative Timeline and End-to-End Verification

**Files:**
- Modify: `web/components/dashboard.tsx`
- Modify: `web/app/globals.css`
- Modify: `scripts/demo.py`
- Modify: `README.md`
- Test: `backend/tests/test_api.py`
- Test: `web/tests/timeline.test.mjs`
- Create: `docs/evidence/natural-command-checks.txt`

**Interfaces:**
- Consumes: `groupTimeline`, public cause IDs, `active_run.progress`, and command-based API endpoints.
- Produces: grouped crisis timeline, expandable cause summaries, updated playable demo, and verification evidence.

- [x] **Step 1: Add failing timeline cause and event-kind tests**

Assert that player commands, interpretations, questions, answers, agent actions, engine progress, and metric effects receive stable presentation kinds, and that cause IDs resolve only to visible events.

- [x] **Step 2: Implement the grouped narrative timeline**

Render turn headers and round sections in ascending narrative order, with distinct player/agent/question/answer/engine cards. Add an accessible `<details>` “Why this happened” section containing linked summaries of visible cause events. Keep orchestration as the secondary tab and show persisted live progress there.

- [x] **Step 3: Update documentation and demo flow**

Change README play instructions from card selection to natural commands and question pauses. Update `scripts/demo.py` to submit command text, poll active runs, answer pending questions, and verify one turn completes without duplicate work/cost.

- [x] **Step 4: Run full verification and record exact output**

Run:

```bash
uv run pytest -q
uv run ruff check backend
npm --prefix web test
npm --prefix web run typecheck
npm --prefix web run build
```

Write the command output and current package versions to `docs/evidence/natural-command-checks.txt`. Expected: every command exits zero.

- [x] **Step 5: Review public-data safety and working tree scope**

Run:

```bash
rg -n "private_goal|player_knowledge|knowledge|prompt|chain.of.thought" docs/evidence/natural-command-checks.txt web/lib web/components
git diff --check
git status --short
```

Expected: no private fields are introduced into web/public evidence, no whitespace errors, and only task-related files are modified.

- [x] **Step 6: Commit the timeline and verification evidence**

```bash
git add web/components/dashboard.tsx web/app/globals.css scripts/demo.py README.md backend/tests/test_api.py web/tests/timeline.test.mjs docs/evidence/natural-command-checks.txt
git commit -m "feat: present interactive crisis rounds"
```
