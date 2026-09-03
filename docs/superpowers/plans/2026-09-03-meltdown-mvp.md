# Project Meltdown Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for this local implementation. Steps use checkbox syntax.

**Goal:** Deliver a locally playable six-turn crisis with a persistent LangGraph organizer, two bounded agent rounds, private observations and a traceable debrief.

**Architecture:** Next.js presents public snapshots from FastAPI. LangGraph runs a persisted per-game loop with interrupt/resume, dynamic Send workers and a deterministic resolver; SQLite records canonical games and idempotent requests. Rules policies work without credentials; a LangChain structured-output adapter enables configured models.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph 1.x, SQLite checkpointer, Next.js 16, React 19, TypeScript.

**Spec:** docs/graphe-orchestration.md and docs/cadrage.md, approved by the user for implementation.

## Global Constraints

- Six turns, up to two player actions, four active characters.
- Maximum two internal rounds; one agent invocation per round; work and time advance once.
- Each agent receives only its allowed observation. API and trace exports expose public data only.
- Only the resolver changes simulation metrics. Commands and outputs are validated.
- SQLite persists state, checkpoints, and request receipts. Duplicate requests never consume another turn.
- Local single-process execution first. A model outage falls back visibly to rules; no claims of live LLM testing without credentials.
- French UI and report. Keep 3D as the documented next presentation milestone after the functional MVP.

## File and interface map

- `backend/meltdown/models.py`: validated TurnRequest and AgentIntent boundaries.
- `scenario.py`: initial state, factual scenario, actions, role metadata and agent observations.
- `engine.py`: player validation, action application, agent resolution and finalization.
- `agents.py`: RulesPolicy, LangChainPolicy, bounded timeout/fallback and prompt.
- `graph.py`: build_graph(store, policy, checkpointer), worker dispatch and human interrupt.
- `store.py`: SQLite game snapshots, request receipts and atomic commit.
- `service.py`: GameService.create(), get(game_id), advance(game_id, TurnRequest), close().
- `projection.py`: public_view(game), debrief grounded in event IDs.
- `api.py`: create_app(db_path, policy), /api/games, /api/games/{id}, /turns, /export.
- `web/lib/types.ts`, `api.ts`: client data and transport.
- `web/components/dashboard.tsx`, `web/app/page.tsx`, `globals.css`: playable dashboard and debrief.
- `scripts/dev.sh`, `.env.example`, `README.md`: setup and local execution.

## Task 1: Rules and observations

- [ ] Write behavior tests: rejecting three actions; hidden client fact absent from developer observation and public view; work advances once; safe and overloaded strategies differ.
- [ ] Run `uv run pytest backend/tests/test_engine.py -q` and confirm absent behavior fails.
- [ ] Implement models, scenario, engine and projection; use fixed scenario values and record event causes.
- [ ] Rerun tests; inspect actual public snapshots.

```python
request = TurnRequest(request_id="test-1", expected_version=0, actions=["audit", "prioritize_fix"])
assert len(request.actions) == 2
```

## Task 2: Persistent orchestration

- [ ] Write integration tests for second-round routing, bounded calls, fallback, restart and duplicate request receipts using a temporary real SQLite database.
- [ ] Run `uv run pytest backend/tests/test_graph.py -q` before implementation.
- [ ] Implement graph, store, policies and service. Collect worker proposals with stable keys; filter by round before resolving. Only accepted messages authorize another round.
- [ ] Verify restart resumes the same game and a conflicting request ID is rejected.

```python
service = GameService(db_path)
game = service.create()
request = TurnRequest(request_id="retry-1", expected_version=0, actions=["audit"])
first = service.advance(game["id"], request)
assert service.advance(game["id"], request) == first
assert first["turn"] == 1
```

## Task 3: API and playable dashboard

- [ ] Write FastAPI integration tests for create, invalid actions, stale versions, completed games and public export.
- [ ] Implement local endpoints and the Next.js proxy; show briefing, queued decisions, metrics, character cards, messages, orchestration trace and end debrief.
- [ ] Preserve a request ID across network retries, restore the last game from device-local storage and expose loading/error states.
- [ ] Build with `npm --prefix web run build`; run all backend tests.
- [ ] Start the local servers, request the page and open the working preview.

## Task 4: Evidence and handoff

- [ ] Run a scripted full game and a contrasting strategy against the real API; save public JSON evidence in docs/evidence.
- [ ] Update report and journal with delivered behavior, exact test results, dependency versions and remaining limitations.
- [ ] Review boundaries, retries, terminal behavior and LLM output validation; fix concrete findings.
- [ ] Commit the implementation on codex/meltdown-mvp and provide the local URL and run instructions.
