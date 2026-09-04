# Natural Commands and Interactive Round Design

**Date:** 2026-09-04  
**Status:** Approved for implementation planning

## Purpose

Project Meltdown currently asks the player to choose up to two predefined action cards and resolves a complete turn in one synchronous request. This design replaces the cards with natural-language instructions, makes the real progress of an active round visible, improves the event log, and lets agents collect questions for the player at the end of an agent round.

The simulation remains bounded and auditable. Player language is translated into the existing game mechanics; neither the command interpreter nor character agents may invent effects or modify metrics directly.

## Product Decisions

- The player writes what they want instead of selecting action cards.
- Free-form text maps to zero, one, or two existing canonical actions.
- Clear interpretations execute immediately and display an interpretation receipt.
- Ambiguous interpretations pause before execution and allow the player to edit the original instruction or confirm the proposed interpretation.
- Character questions are collected after all agents in the current parallel round finish.
- The player answers all collected questions together.
- Only agents that asked a question receive the corresponding answer and participate in the bounded answer follow-up.
- The frontend polls a persisted run state. Server-Sent Events and WebSockets are out of scope.

## Non-Goals

- Dynamically creating new game actions, costs, tasks, or metric effects.
- Allowing model output to bypass `prepare_turn`, `allowed_intents`, or the deterministic engine.
- Streaming individual model tokens.
- Turning the crisis log into a display of private agent prompts, hidden knowledge, or chain-of-thought.
- Supporting multiple Uvicorn workers or distributed job execution.

## Turn Lifecycle

An active turn is represented by a persisted run with the following public phases:

1. `interpreting`: translate the player's text into canonical actions.
2. `needs_confirmation`: the interpretation is ambiguous and awaits confirmation or a replacement instruction.
3. `round_active`: the graph is dispatching agents or applying their validated intents.
4. `awaiting_answers`: one or more agent questions await a single player response submission.
5. `resolving`: apply the bounded answer follow-up and finalize the period.
6. `complete`: the new game version is committed and the game is ready for another turn or its debrief.
7. `failed`: infrastructure work stopped and may be retried with the same request identity.

Only one non-terminal run may exist for a game. A new command is rejected while a run is active. Phase changes and public progress steps are persisted so that browser refreshes show the current state rather than restarting the turn.

Work, recurring costs, time, game version, and end-state evaluation advance exactly once, during finalization. Interpretation, confirmation, question pauses, answers, retries, and agent follow-ups do not advance them.

## Natural-Language Command Interpreter

### Input

The command endpoint accepts:

```json
{
  "request_id": "client-generated-id",
  "expected_version": 2,
  "command": "Ask Morgan to investigate the defect and put Alex on the fix"
}
```

The command is required, trimmed, and length-limited. An empty command is not used as an implicit no-op; the player can explicitly say they want to wait or continue without issuing a new instruction.

### Structured result

The interpreter returns an internal schema containing:

- `summary`: concise player-facing English.
- `actions`: zero to two IDs from the existing `ACTIONS` registry.
- `confidence`: `clear` or `ambiguous`.
- `reason`: an explanation when confirmation is required.

The interpreter receives only the public game state and currently available actions with their constraints. Its output is validated against the schema and then passed through the existing deterministic `prepare_turn` validation. It cannot provide effect values.

In LLM mode, a structured model call performs semantic interpretation. In rules mode, and whenever the model call fails, a deterministic synonym and phrase matcher handles common formulations. The fallback returns `ambiguous` instead of guessing when it cannot identify a unique safe mapping.

### Confirmation behavior

A `clear` result begins the agent round immediately. The public run includes an interpretation receipt such as “Understood: audit the defect and prioritize the security fix.”

An `ambiguous` result moves the run to `needs_confirmation` without applying actions. The player may:

- confirm the proposed canonical actions; or
- replace the text, which creates a new interpretation attempt within the same request/run identity.

Confirmation never permits disabled, conflicting, unknown, or unaffordable actions. If game validation rejects an otherwise clear interpretation, the run moves to `needs_confirmation` with the validation reason and no game mutation.

## Agent Questions

`AgentIntent` gains an `ask_player` intent with a concise question and a reason. The action is available only when an answer could affect a decision that is valid for that character. An agent may ask at most one question per turn.

After the round's parallel dispatch barrier completes, the resolver validates and collects public questions. Questions are deduplicated by requesting agent and normalized text, and the turn exposes no more than three. Other intents from the same round are resolved normally before the pause.

Each public question contains:

- a stable question ID;
- the requesting character's public identity;
- the question;
- a short reason the answer is needed; and
- the turn and round in which it was asked.

The answers endpoint accepts the active run ID and exactly one answer for every pending question. Answers are length-limited, treated as untrusted game data, and never interpreted as system instructions.

The graph sends each answer only to its requesting agent. Those agents enter one targeted answer follow-up phase in which `ask_player` is disabled. They may select another currently allowed intent or wait. After that phase, the turn finalizes; answers cannot create an unbounded conversation loop. If questions arise in either normal agent round, the same one-pause and one-follow-up limit applies.

Answers and resulting character responses appear in the public event history. Answers do not automatically become verified facts. Agents may use them as player direction or negotiation context, while engine-controlled facts and prerequisites remain authoritative.

## Backend Architecture

### Persisted run record

SQLite gains a turn-run record keyed by run ID and linked to a game. It contains the request fingerprint, expected game version, original command, phase, structured interpretation, public progress, pending questions, submitted answers, error state, and timestamps.

The canonical game remains in the existing `games` table. The run record is operational state and does not expose private observations or prompts. Completed request receipts retain idempotent responses as they do today.

### Background execution

Submitting a valid new command creates the run record and returns `202 Accepted` promptly. An in-process worker advances the LangGraph until one of three boundaries:

- interpretation requires confirmation;
- agent questions require answers; or
- the turn reaches completion or an infrastructure failure.

Polling reads the canonical game and its public active-run projection without waiting for model calls to finish. Database operations are short and serialized where necessary; the service must not hold the current global mutation lock across an external model call.

LangGraph checkpoints remain the source for graph continuation. A retry claims the same persisted run and resumes its incomplete boundary. Nodes that produce externally visible progress must be idempotent or checkpointed before they are reported as complete.

This remains a single-process local architecture. On server restart, an incomplete run is marked resumable rather than silently restarted; the player can resume it with the same request ID.

### API shape

- `POST /api/games/{game_id}/turns` creates a run from natural-language input and returns the updated public game/run projection with HTTP 202.
- `GET /api/games/{game_id}` includes the current public run, if any, and supports frontend polling.
- `POST /api/games/{game_id}/runs/{run_id}/confirmation` confirms the proposed interpretation or supplies replacement command text.
- `POST /api/games/{game_id}/runs/{run_id}/answers` submits all pending answers and resumes the graph.
- `POST /api/games/{game_id}/runs/{run_id}/retry` resumes a failed or abandoned infrastructure operation without creating a second turn.

Every mutation carries a request identifier and verifies the game/run version appropriate to its boundary. A stale, duplicate-with-different-payload, wrong-phase, or wrong-run request returns a specific conflict response.

## Public Projection

The game projection gains an optional `active_run` with only player-safe fields:

- run ID and phase;
- original command;
- interpretation summary and canonical action labels;
- confirmation reason, when applicable;
- active agent IDs;
- public progress steps and timestamps;
- pending questions;
- recoverable error information.

Canonical action definitions remain server-side inputs to interpretation and validation. The public response no longer needs to present the full action catalog as the primary interaction mechanism. It may retain action labels only where needed to explain an interpretation or exported historical event.

No private goal, private fact, hidden message, raw prompt, chain-of-thought, or model response is added to the projection or export.

## Frontend Experience

### Command composer

The decision column becomes a command composer headed “What do you want the team to do?” It contains a multiline text field, a primary “Start round” control, and contextual placeholder copy. It does not contain selectable decision cards or category filters.

After a clear submission, the composer becomes the live run panel and shows the interpretation receipt. When confirmation is required, it shows the proposed understanding, the reason for uncertainty, an editable copy of the original command, and explicit confirm/reinterpret controls.

### Active round panel

While a run is active, the panel displays:

- the current phase in plain language;
- the real active characters reported by the backend;
- completed public progress steps;
- elapsed time;
- a saved/recoverable status message; and
- a retry action only when the run is marked failed.

The page polls while `active_run` is non-terminal, backs off modestly when no phase changes, and stops polling at `complete`, `needs_confirmation`, `awaiting_answers`, or `failed`. The 3D office uses `active_agents` to highlight characters but remains a visualization of public state, not a second execution engine.

### Question form

In `awaiting_answers`, the active panel becomes “Agents need your input.” Every question shows the character, question, and reason, followed by an individual response field. The player submits all answers together. Empty or missing answers are rejected inline without losing completed text.

### Crisis timeline

The default crisis log is grouped first by turn and then by agent round. It distinguishes:

- player commands and interpretation receipts;
- character actions and messages;
- character questions and player answers;
- engine work and time progression; and
- metric changes and important outcomes.

Events remain chronological within a group. Cause relationships are shown through an expandable “Why this happened” control containing linked source-event summaries. The current flat technical orchestration list remains a secondary tab and uses persisted live progress during an active run.

On completion, the debrief continues to cite stable event IDs. Command, question, and answer events may become evidence, but suggestions remain clearly distinguished from simulated outcomes.

## Errors and Recovery

- Interpretation failure: use the deterministic fallback; if still uncertain, request confirmation rather than choosing an action.
- Invalid mapped action: show the engine's validation reason in `needs_confirmation`; do not mutate the game.
- Agent model failure: use the existing per-agent rules fallback and visibly count it in orchestration metadata.
- Worker interruption: retain the run and checkpoint, expose `failed` or resumable state, and retry with the same identity.
- Polling/network failure: keep the submitted command or answers in the browser and allow polling to resume without resubmission.
- Stale version: reload the canonical game and show that the command was not applied.
- Duplicate request: return the existing run or completed receipt when the fingerprint matches; reject conflicting reuse.

## Testing Strategy

### Backend unit tests

- Map representative natural-language commands to the correct existing actions.
- Return ambiguity for unknown, conflicting, or low-confidence instructions.
- Ensure interpreter output cannot introduce unknown actions or effects.
- Preserve all existing action validation rules after interpretation.
- Collect multiple questions after a dispatch barrier and expose at most three.
- Deliver each answer only to its requesting agent.
- Disable repeat questions during the answer follow-up.
- Advance work, costs, time, and version exactly once.

### Service and API tests

- Return 202 for a newly accepted run and expose each public phase through polling.
- Reject concurrent turns, stale versions, wrong phases, and conflicting idempotency reuse.
- Resume confirmation, answers, and failed runs from the correct checkpoint.
- Recover an incomplete persisted run after recreating the service.
- Verify public projections and exports contain no private agent data.
- Retain distinct outcomes for the existing safe and neglected playthroughs.

### Frontend tests

- Render composer, interpretation receipt, confirmation state, live state, question form, retry state, and next-turn state.
- Preserve command and answer drafts across transient request failures.
- Poll only in running phases and stop at player-input boundaries.
- Group events by turn and round without changing chronological order.
- Associate cause links and debrief evidence with the correct event IDs.
- Maintain keyboard accessibility, visible focus, reduced-motion behavior, and the existing 2D/WebGL fallback.

### Verification

Run the existing backend, lint, frontend build, and frontend test commands. Add an end-to-end demo path that submits natural language, answers at least one agent question, resumes the same run, and completes a turn without double-applying work or cost.

## Implementation Boundaries

Implementation should preserve the current separation of concerns:

- `models.py`: validated command, interpretation, question, answer, and run schemas.
- `scenario.py`: canonical actions, availability, and allowed character intents.
- `agents.py`: structured command interpretation and `ask_player` policy behavior.
- `graph.py`: pause/resume boundaries and targeted answer follow-up.
- `engine.py`: deterministic validation, effects, and public events.
- `store.py` and `service.py`: persisted runs, idempotency, worker coordination, and recovery.
- `projection.py`: private-data-safe active-run and timeline projection.
- `api.py`: run creation, confirmation, answer, retry, and polling endpoints.
- `web/lib`: public TypeScript types, API methods, polling state helpers, and timeline grouping.
- `web/components`: command composer, active-run/question UI, and improved timeline presentation.

Refactoring unrelated game mechanics, redesigning the 3D office, distributed execution, and expanding the action catalog are outside this change.
