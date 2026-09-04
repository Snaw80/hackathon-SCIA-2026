import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  ChevronRight,
  CircleHelp,
  LoaderCircle,
  MessageSquareText,
  Play,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import type { Game } from "@/lib/types";

const phaseLabels = {
  interpreting: "Understanding your instruction",
  round_active: "Agents are responding",
  resolving: "Applying your answers",
} as const;

export default function CommandPanel({
  game,
  busy,
  onCommand,
  onConfirm,
  onAnswers,
  onRetry,
}: {
  game: Game;
  busy: boolean;
  onCommand: (command: string) => Promise<boolean>;
  onConfirm: (replacement: string | null) => Promise<boolean>;
  onAnswers: (answers: Record<string, string>) => Promise<boolean>;
  onRetry: () => Promise<boolean>;
}) {
  const run = game.active_run;
  const [command, setCommand] = useState("");
  const [replacement, setReplacement] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});

  useEffect(() => {
    if (run?.phase === "needs_confirmation") setReplacement(run.command);
  }, [run?.id, run?.phase, run?.command]);

  useEffect(() => {
    if (run?.phase !== "awaiting_answers") return;
    setAnswers((current) =>
      Object.fromEntries(
        run.questions.map((question) => [question.id, current[question.id] ?? ""]),
      ),
    );
  }, [run?.id, run?.phase, run?.questions]);

  const running =
    run && ["interpreting", "round_active", "resolving"].includes(run.phase);
  const allAnswered = useMemo(
    () =>
      !!run?.questions.length &&
      run.questions.every((question) => answers[question.id]?.trim()),
    [answers, run?.questions],
  );

  if (game.status === "finished") {
    return (
      <section className="decision-panel command-panel">
        <div className="section-heading">
          <h2>
            <Check size={18} /> Crisis complete
          </h2>
        </div>
        <p className="panel-description">
          Explore the timeline and debrief to understand the consequences of
          your instructions.
        </p>
      </section>
    );
  }

  if (running) {
    return (
      <section className="decision-panel command-panel live-run" aria-live="polite">
        <div className="run-phase-icon">
          <LoaderCircle className="spin" size={22} />
        </div>
        <div className="eyebrow">ROUND IN PROGRESS</div>
        <h2>{phaseLabels[run.phase as keyof typeof phaseLabels]}</h2>
        {run.interpretation && (
          <div className="interpretation-receipt">
            <Sparkles size={15} />
            <span>
              <small>I understood this as</small>
              {run.interpretation.summary}
            </span>
          </div>
        )}
        {!!run.active_agents.length && (
          <div className="active-agent-list">
            {run.active_agents.map((actor) => (
              <span key={actor}>{actor}</span>
            ))}
          </div>
        )}
        <div className="run-progress">
          {run.progress.map((step, index) => (
            <div key={`${step.label}-${index}`}>
              <Check size={13} /> {step.label}
            </div>
          ))}
          <div className="current">
            <LoaderCircle className="spin" size={13} /> Processing current phase
          </div>
        </div>
        <p className="saved-note">This round is saved and safe to refresh.</p>
      </section>
    );
  }

  if (run?.phase === "needs_confirmation") {
    const canConfirm = !!run.interpretation?.actions.length;
    const changed = replacement.trim() !== run.command.trim();
    return (
      <section className="decision-panel command-panel clarification-panel">
        <div className="section-heading">
          <h2>
            <CircleHelp size={18} /> Clarify your instruction
          </h2>
        </div>
        {run.interpretation && (
          <div className="interpretation-receipt uncertain">
            <AlertCircle size={16} />
            <span>
              <small>I understood this as</small>
              {run.interpretation.summary}
            </span>
          </div>
        )}
        <p className="clarification-reason">
          {run.interpretation?.reason ?? "Please make the instruction more specific."}
        </p>
        <label className="command-field">
          <span>Your instruction</span>
          <textarea
            value={replacement}
            onChange={(event) => setReplacement(event.target.value)}
            disabled={busy}
            rows={5}
          />
        </label>
        <div className="command-actions">
          {canConfirm && !changed && (
            <button
              className="secondary-button"
              disabled={busy}
              onClick={() => onConfirm(null)}
            >
              Confirm interpretation
            </button>
          )}
          <button
            className="primary-button"
            disabled={busy || !replacement.trim() || (!changed && !canConfirm)}
            onClick={() => onConfirm(replacement.trim())}
          >
            {busy ? <LoaderCircle className="spin" size={17} /> : <RotateCcw size={16} />}
            Reinterpret
          </button>
        </div>
      </section>
    );
  }

  if (run?.phase === "awaiting_answers") {
    return (
      <section className="decision-panel command-panel question-panel">
        <div className="section-heading">
          <h2>
            <MessageSquareText size={18} /> Agents need your input
          </h2>
          <span className="action-count">{run.questions.length}</span>
        </div>
        <p className="panel-description">
          The agent round is paused. Answer every question, then everyone will
          continue from the same saved state.
        </p>
        <div className="question-list">
          {run.questions.map((question) => (
            <label key={question.id} className="question-card">
              <span className="question-actor">{question.actor}</span>
              <strong>{question.question}</strong>
              <small>{question.reason}</small>
              <textarea
                rows={3}
                value={answers[question.id] ?? ""}
                onChange={(event) =>
                  setAnswers((current) => ({
                    ...current,
                    [question.id]: event.target.value,
                  }))
                }
                placeholder="Type your answer…"
                disabled={busy}
              />
            </label>
          ))}
        </div>
        <button
          className="primary-button advance-button"
          disabled={busy || !allAnswered}
          onClick={() => onAnswers(answers)}
        >
          {busy ? <LoaderCircle className="spin" size={17} /> : <Play size={16} />}
          Resume round <ChevronRight size={17} />
        </button>
      </section>
    );
  }

  if (run?.phase === "failed") {
    return (
      <section className="decision-panel command-panel failed-panel">
        <AlertCircle size={23} />
        <h2>The round needs attention</h2>
        <p>{run.error}</p>
        <button className="primary-button" disabled={busy} onClick={onRetry}>
          <RotateCcw size={16} /> Retry safely
        </button>
      </section>
    );
  }

  return (
    <section className="decision-panel command-panel">
      <div className="section-heading">
        <h2>
          <MessageSquareText size={18} /> Your instruction
        </h2>
        <span className="quiet-label">UP TO 2 DECISIONS</span>
      </div>
      <p className="panel-description">
        Tell the team what outcome you want. The simulation will translate it
        into the available project controls.
      </p>
      {run?.phase === "complete" && run.interpretation && (
        <div className="interpretation-receipt complete">
          <Check size={15} />
          <span>
            <small>Last round understood as</small>
            {run.interpretation.summary}
          </span>
        </div>
      )}
      <label className="command-field">
        <span>What do you want the team to do?</span>
        <textarea
          rows={6}
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="For example: investigate the security warning, then ask Alex to prioritize the fix."
          disabled={busy}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && command.trim()) {
              event.preventDefault();
              void onCommand(command.trim()).then((ok) => ok && setCommand(""));
            }
          }}
        />
      </label>
      <button
        className="primary-button advance-button"
        disabled={busy || !command.trim()}
        onClick={() =>
          void onCommand(command.trim()).then((ok) => ok && setCommand(""))
        }
      >
        {busy ? <LoaderCircle className="spin" size={18} /> : <Play size={16} fill="currentColor" />}
        {busy ? "Submitting…" : "Start round"}
        {!busy && <ChevronRight size={18} />}
      </button>
      <span className="turn-hint">⌘ Enter to submit · existing work continues each turn</span>
    </section>
  );
}
