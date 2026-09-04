"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  Check,
  ChevronRight,
  Clock3,
  Download,
  Flag,
  GitBranch,
  LoaderCircle,
  MessageSquare,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Target,
  Users,
  Wallet,
  X,
  Zap,
} from "lucide-react";
import OfficeView from "./office/office-view";
import CommandPanel from "./command-panel";
import { api, ApiError } from "@/lib/api";
import type { Game, GameEvent } from "@/lib/types";

const storageKey = "meltdown-game-id-en";
const actorLabels: Record<string, string> = {
  player: "You",
  developer: "Alex · Development",
  client: "Camille · Client",
  sales: "Sam · Sales",
  security: "Morgan · Security",
  director: "Management",
  engine: "Project",
};
const pollingPhases = new Set(["interpreting", "round_active", "resolving"]);

function EventCard({
  event,
  focused,
}: {
  event: GameEvent;
  focused?: boolean;
}) {
  return (
    <article
      id={`event-${event.id}`}
      className={`event-card ${focused ? "event-focused" : ""}`}
    >
      <div className="event-heading">
        <span className={`event-dot ${event.actor}`} />
        <span>{actorLabels[event.actor] || event.actor}</span>
        <span className="event-time">
          {event.turn ? `T${event.turn}` : "Briefing"}
          {event.round ? ` · R${event.round}` : ""}
        </span>
      </div>
      <h4>{event.title}</h4>
      <p>{event.detail}</p>
      {!!Object.keys(event.effects).length && (
        <div className="effects">
          {Object.entries(event.effects).map(([key, value]) => (
            <span key={key} className={value > 0 ? "positive" : "negative"}>
              {key} {value > 0 ? "+" : ""}
              {value}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

export default function Dashboard() {
  const [game, setGame] = useState<Game | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"events" | "graph">("events");
  const [focused, setFocused] = useState<string[]>([]);

  useEffect(() => {
    let mounted = true;
    const id = localStorage.getItem(storageKey);
    if (!id) {
      setLoading(false);
      return;
    }
    api
      .get(id)
      .then((value) => {
        if (mounted) setGame(value);
      })
      .catch((err) => {
        if (!mounted) return;
        if (err instanceof ApiError && err.status === 404)
          localStorage.removeItem(storageKey);
        else
          setError(
            "The game could not be loaded. Check that the server is running, then refresh.",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const gameId = game?.id;
    const phase = game?.active_run?.phase;
    if (!gameId || !phase || !pollingPhases.has(phase)) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const updated = await api.get(gameId);
        if (!cancelled) setGame(updated);
      } catch {
        // A transient polling failure is retried without losing the submitted command.
      }
      if (!cancelled) timer = setTimeout(poll, 750);
    };
    timer = setTimeout(poll, 450);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [game?.id, game?.active_run?.phase]);

  async function createGame() {
    setBusy(true);
    setError("");
    try {
      const created = await api.create();
      localStorage.setItem(storageKey, created.id);
      setGame(created);
      setFocused([]);
    } catch {
      setError(
        "Unable to reach the simulation. Check that the Python server is running, then try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function submitCommand(command: string) {
    if (!game || busy) return false;
    setBusy(true);
    setError("");
    try {
      const updated = await api.command(game.id, {
        request_id: crypto.randomUUID(),
        expected_version: game.version,
        command,
      });
      setGame(updated);
      setFocused([]);
      return true;
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No response received. Your command is preserved while the game reconnects.",
      );
      try {
        setGame(await api.get(game.id));
      } catch {
        // Keep the local state and command draft.
      }
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function confirmCommand(replacement: string | null) {
    if (!game?.active_run || busy) return false;
    setBusy(true);
    setError("");
    try {
      setGame(
        await api.confirm(game.id, game.active_run.id, {
          request_id: crypto.randomUUID(),
          ...(replacement ? { command: replacement } : { confirm: true }),
        }),
      );
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The instruction could not be confirmed.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function submitAnswers(answers: Record<string, string>) {
    if (!game?.active_run || busy) return false;
    setBusy(true);
    setError("");
    try {
      setGame(
        await api.answer(game.id, game.active_run.id, {
          request_id: crypto.randomUUID(),
          answers: game.active_run.questions.map((question) => ({
            question_id: question.id,
            text: answers[question.id],
          })),
        }),
      );
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The answers could not be submitted.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function retryRun() {
    if (!game?.active_run || busy) return false;
    setBusy(true);
    setError("");
    try {
      setGame(await api.retry(game.id, game.active_run.id));
      return true;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The round could not be resumed.");
      return false;
    } finally {
      setBusy(false);
    }
  }
  function showEvidence(ids: string[]) {
    setFocused(ids);
    setTab("events");
    requestAnimationFrame(() =>
      document
        .getElementById(`event-${ids[0]}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  }

  const finished = game?.status === "finished";
  const activeTurn = game ? Math.min(game.turn + 1, game.max_turns) : 1;
  const day = Math.ceil(activeTurn / 2);
  const runActive = !!game?.active_run && pollingPhases.has(game.active_run.phase);
  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Project Meltdown">
          <span className="brand-symbol">
            <Zap size={21} fill="currentColor" />
          </span>
          <span>
            PROJECT <strong>MELTDOWN</strong>
          </span>
        </a>
        <div className="topbar-divider" />
        <span className="workspace-name">Crisis room</span>
        <div className="topbar-right">
          <span className="local-badge">
            <span />
            {!game
              ? "Ready to play"
              : game.mode === "llm"
                ? "AI agents"
                : "Rules simulation"}
          </span>
          <span className="edition">SCIA / 2026</span>
        </div>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <ShieldAlert size={19} />
          <span>{error}</span>
          <button onClick={() => setError("")} aria-label="Dismiss alert">
            <X size={17} />
          </button>
        </div>
      )}

      {loading ? (
        <main className="loading-screen">
          <LoaderCircle className="spin" size={28} />
          <p>Restoring the crisis room…</p>
        </main>
      ) : !game ? (
        <main className="briefing-screen">
          <div className="briefing-index">
            SCENARIO 01 <span>/ CRISIS MANAGEMENT</span>
          </div>
          <div className="briefing-layout">
            <section>
              <div className="eyebrow">
                <span className="orange-dot" /> DELIVERY IN THREE DAYS
              </div>
              <h1>
                The impossible
                <br />
                <em>delivery.</em>
              </h1>
              <p className="briefing-intro">
                A promise to keep. A technical warning. A team under pressure.
                You take command.
              </p>
              <div className="briefing-facts">
                <span>
                  <Clock3 size={17} /> 6 turns
                </span>
                <span>
                  <Users size={17} /> 4 characters
                </span>
                <span>
                  <MessageSquare size={17} /> Natural-language commands
                </span>
              </div>
              <button
                className="primary-button start-button"
                onClick={createGame}
                disabled={busy}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={19} />
                ) : (
                  <Play size={18} fill="currentColor" />
                )}{" "}
                Take command <ArrowRight size={19} />
              </button>
              <p className="start-note">
                The characters react to your decisions. You do not have all the
                information.
              </p>
            </section>
            <aside className="briefing-dossier">
              <div className="dossier-header">
                <Flag size={18} /> HANDOVER NOTES <span>CONFIDENTIAL</span>
              </div>
              <h2>Your starting brief</h2>
              {[
                [
                  "01",
                  "A warning to investigate",
                  "The lead developer has found a defect. Its severity is still unknown.",
                ],
                [
                  "02",
                  "One promise too many",
                  "The client expects an extra feature promised by the sales lead.",
                ],
                [
                  "03",
                  "Limited capacity",
                  "The team is already working on delivery. Every new priority has a cost.",
                ],
              ].map(([n, title, detail]) => (
                <div className="briefing-item" key={n}>
                  <span>{n}</span>
                  <div>
                    <h3>{title}</h3>
                    <p>{detail}</p>
                  </div>
                </div>
              ))}
              <div className="dossier-footer">
                Your goal: reach a viable outcome and understand the cost of
                your choices.
              </div>
            </aside>
          </div>
          <div className="briefing-bottom">
            <GitBranch size={17} />
            <span>
              Decision → organizer → characters → consequences → next decision
            </span>
          </div>
        </main>
      ) : (
        <main className="game-layout" aria-busy={busy || runActive}>
          <section className="mission-heading">
            <div>
              <div className="eyebrow">
                SCENARIO 01 <span>/</span>{" "}
                {finished ? "GAME COMPLETE" : "CRISIS IN PROGRESS"}
              </div>
              <h1>
                The impossible delivery<span>.</span>
              </h1>
              <p>
                {finished
                  ? game.outcome?.title
                  : "Keep your commitments while staying in control of the project."}
              </p>
            </div>
            <div className="turn-clock">
              <Clock3 size={23} />
              <div>
                <strong>{finished ? "Final outcome" : `Day ${day} / 3`}</strong>
                <span>
                  {finished
                    ? `${game.turn} turns played`
                    : `${activeTurn % 2 ? "Morning" : "Afternoon"} · Turn ${activeTurn} of 6`}
                </span>
              </div>
            </div>
          </section>
          <section className="metrics-strip" aria-label="Project metrics">
            <Metric
              icon={<Target size={18} />}
              label="Progress"
              value={`${game.metrics.progress}%`}
              bar={game.metrics.progress}
            />
            <Metric
              icon={<Wallet size={18} />}
              label="Budget remaining"
              value={`${game.metrics.budget}`}
              unit="/ 100"
              bar={game.metrics.budget}
            />
            <Metric
              icon={<MessageSquare size={18} />}
              label="Client trust"
              value={`${game.metrics.trust}%`}
              bar={game.metrics.trust}
            />
            <Metric
              icon={<Users size={18} />}
              label="Team morale"
              value={`${game.metrics.morale}%`}
              bar={game.metrics.morale}
            />
            <div className={`metric security-metric ${game.security.status}`}>
              <div className="metric-label">
                {game.security.status === "safe" ? (
                  <ShieldCheck size={18} />
                ) : (
                  <ShieldAlert size={18} />
                )}{" "}
                Security
              </div>
              <strong>{game.security.label}</strong>
              <span>{game.security.detail}</span>
            </div>
          </section>

          {finished && game.debrief && (
            <section className="debrief-panel">
              <div className="section-heading">
                <div>
                  <div className="eyebrow">GAME DEBRIEF</div>
                  <h2>{game.debrief.headline}</h2>
                </div>
                <Flag size={25} />
              </div>
              <p className="debrief-summary">{game.debrief.summary}</p>
              <div className="debrief-moments">
                {game.debrief.moments.map((moment, i) => (
                  <article key={i}>
                    <span className="moment-number">0{i + 1}</span>
                    <h3>{moment.title}</h3>
                    <p>{moment.analysis}</p>
                    <p className="alternative">
                      <strong>Try another approach</strong> {moment.alternative}
                    </p>
                    <button
                      className="text-button"
                      onClick={() => showEvidence(moment.event_ids)}
                    >
                      View events <ArrowRight size={14} />
                    </button>
                  </article>
                ))}
              </div>
              <div className="debrief-footer">
                <span>
                  {game.debrief.source === "llm"
                    ? "AI coach · verified references"
                    : "Factual review based on recorded events"}
                </span>
                <button
                  className="primary-button"
                  onClick={createGame}
                  disabled={busy}
                >
                  <RotateCcw size={16} /> Replay the crisis
                </button>
              </div>
            </section>
          )}

          <div className="workspace-grid">
            <section className="main-column">
              <OfficeView
                key={game.id}
                game={game}
                busy={busy || runActive}
                activeAgents={game.active_run?.active_agents ?? []}
                onShowEvent={showEvidence}
              />

              <section className="activity-panel">
                <div className="activity-toolbar">
                  <div
                    className="tabs"
                    role="tablist"
                    aria-label="Simulation activity"
                  >
                    <button
                      role="tab"
                      aria-selected={tab === "events"}
                      className={tab === "events" ? "active" : ""}
                      onClick={() => setTab("events")}
                    >
                      <Activity size={16} /> Crisis log{" "}
                      <span>{game.events.length}</span>
                    </button>
                    <button
                      role="tab"
                      aria-selected={tab === "graph"}
                      className={tab === "graph" ? "active" : ""}
                      onClick={() => setTab("graph")}
                    >
                      <GitBranch size={16} /> Orchestration
                    </button>
                  </div>
                  <a
                    className="icon-button"
                    href={`/api/games/${game.id}/export`}
                    download
                    aria-label="Export public game log"
                  >
                    <Download size={17} />
                  </a>
                </div>
                {tab === "events" ? (
                  <div className="events-list" role="tabpanel">
                    {game.events.slice().reverse().map((event) => (
                      <EventCard
                        key={event.id}
                        event={event}
                        focused={focused.includes(event.id)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="graph-view" role="tabpanel">
                    <div className="graph-explainer">
                      <span className="graph-icon">
                        <GitBranch size={22} />
                      </span>
                      <div>
                        <h3>Behind the turn</h3>
                        <p>
                          This view shows the graph steps. Private knowledge
                          stays inside the simulation.
                        </p>
                      </div>
                    </div>
                    {game.last_run.steps.length ? (
                      <>
                        <div className="run-stats">
                          <span>
                            <strong>{game.last_run.rounds}</strong> rounds
                          </span>
                          <span>
                            <strong>{game.last_run.agent_calls}</strong>{" "}
                            activations
                          </span>
                          <span>
                            <strong>
                              {(game.last_run.duration_ms / 1000).toFixed(1)} s
                            </strong>{" "}
                            to resolve
                          </span>
                        </div>
                        <div className="graph-steps">
                          {game.last_run.steps.map((step, index) => (
                            <div
                              key={index}
                              className={`graph-step ${step.status === "fallback" ? "fallback" : ""}`}
                            >
                              <span className="step-track">
                                <span />
                                {index < game.last_run.steps.length - 1 && (
                                  <i />
                                )}
                              </span>
                              <div>
                                <strong>{step.label}</strong>
                                <span>
                                  {step.round ? `Round ${step.round} · ` : ""}
                                  {step.status === "fallback"
                                    ? "Rules fallback used"
                                    : step.node}
                                </span>
                              </div>
                              <Check size={15} />
                            </div>
                          ))}
                        </div>
                        {!!game.last_run.fallbacks && (
                          <p className="fallback-notice">
                            {game.last_run.fallbacks} activation(s) used the
                            rules fallback.
                          </p>
                        )}
                      </>
                    ) : (
                      <div className="graph-empty">
                        <span>Player decision</span>
                        <ArrowDown size={16} />
                        <span>Organizer → characters → resolution</span>
                        <ArrowDown size={16} />
                        <span>New state · waiting for your first turn</span>
                      </div>
                    )}
                  </div>
                )}
              </section>
            </section>
            <aside className="decision-column">
              <CommandPanel
                game={game}
                busy={busy}
                onCommand={submitCommand}
                onConfirm={confirmCommand}
                onAnswers={submitAnswers}
                onRetry={retryRun}
              />
              <section className="task-panel">
                <div className="section-heading">
                  <h2>Work in progress</h2>
                  <span className="quiet-label">LIMITED CAPACITY</span>
                </div>
                {game.tasks.map((task) => (
                  <div className="task-item" key={task.id}>
                    <div>
                      <span>{task.title}</span>
                      <strong>
                        {task.remaining === 0 ? (
                          <Check size={14} />
                        ) : (
                          `${task.remaining} u.`
                        )}
                      </strong>
                    </div>
                    <div className="task-progress">
                      <i
                        style={{
                          width: `${100 * (1 - task.remaining / task.total)}%`,
                        }}
                      />
                    </div>
                    <small>{task.status}</small>
                  </div>
                ))}
              </section>
            </aside>
          </div>
          <footer className="game-footer">
            <span>
              <span className="status-dot" /> Game saved · turn {game.turn}
            </span>
            <span>
              PROJECT MELTDOWN <span className="footer-separator">/</span> SCIA
              2026
            </span>
            <button
              onClick={() => {
                if (
                  window.confirm(
                    "Start a new game? Your current game will remain saved on the server.",
                  )
                )
                  createGame();
              }}
              disabled={busy}
            >
              <RotateCcw size={13} /> New game
            </button>
          </footer>
        </main>
      )}
    </div>
  );
}

function Metric({
  icon,
  label,
  value,
  unit,
  bar,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  bar: number;
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        {icon}
        {label}
      </div>
      <div className="metric-value">
        <strong>{value}</strong>
        {unit && <span>{unit}</span>}
      </div>
      <div className={`metric-bar ${bar < 30 ? "low" : ""}`}>
        <i style={{ width: `${Math.max(0, Math.min(100, bar))}%` }} />
      </div>
    </div>
  );
}
