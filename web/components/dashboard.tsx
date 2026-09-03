"use client";

import { useEffect, useRef, useState } from "react";
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
  Plus,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Target,
  Users,
  Wallet,
  X,
  Zap,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Game, GameEvent, TurnRequest } from "@/lib/types";

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
const categories = ["All", "Technical", "Team", "Client relations"];

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
  const [selected, setSelected] = useState<string[]>([]);
  const [category, setCategory] = useState("All");
  const [tab, setTab] = useState<"events" | "graph">("events");
  const [focused, setFocused] = useState<string[]>([]);
  const [retryPending, setRetryPending] = useState(false);
  const pending = useRef<TurnRequest | null>(null);

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

  async function createGame() {
    setBusy(true);
    setError("");
    try {
      const created = await api.create();
      localStorage.setItem(storageKey, created.id);
      setGame(created);
      setSelected([]);
      pending.current = null;
      setRetryPending(false);
      setFocused([]);
    } catch {
      setError(
        "Unable to reach the simulation. Check that the Python server is running, then try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function advance() {
    if (!game || busy) return;
    pending.current ??= {
      request_id: crypto.randomUUID(),
      expected_version: game.version,
      actions: selected,
    };
    setBusy(true);
    setError("");
    try {
      const updated = await api.advance(game.id, pending.current);
      setGame(updated);
      setSelected([]);
      setFocused([]);
      setRetryPending(false);
      pending.current = null;
    } catch (err) {
      if (err instanceof ApiError && err.status < 500 && err.status !== 408) {
        setError(err.message);
        pending.current = null;
        setRetryPending(false);
        if (err.status === 409) {
          try {
            setGame(await api.get(game.id));
            setSelected([]);
          } catch {
            /* Original error remains visible. */
          }
        }
      } else {
        setError(
          "No response received. Retry to resume the same request without playing the turn twice.",
        );
        setRetryPending(true);
      }
    } finally {
      setBusy(false);
    }
  }

  function select(id: string) {
    if (busy || retryPending) return;
    setSelected((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : current.length < 2
          ? [...current, id]
          : current,
    );
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
  const latest = game?.events.slice().reverse() || [];
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
                  <Target size={17} /> 2 decisions per turn
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
        <main className="game-layout" aria-busy={busy}>
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
              <div className="section-heading">
                <h2>
                  <Users size={18} /> The stakeholders
                </h2>
                <span className="quiet-label">4 ACTIVE CHARACTERS</span>
              </div>
              <div className="agents-grid">
                {game.agents.map((agent) => (
                  <article
                    className="agent-card"
                    key={agent.id}
                    style={
                      { "--agent-color": agent.color } as React.CSSProperties
                    }
                  >
                    <div className="agent-top">
                      <div className="avatar">{agent.initials}</div>
                      <div>
                        <h3>{agent.name}</h3>
                        <span className="agent-role">{agent.role}</span>
                      </div>
                      <span
                        className={`agent-status ${agent.stress > 70 ? "strained" : ""}`}
                      >
                        {agent.status}
                      </span>
                    </div>
                    <p className="agent-activity">{agent.activity}</p>
                    <div className="agent-bottom">
                      <span>
                        Pressure{" "}
                        <strong>
                          {agent.stress > 70
                            ? "High"
                            : agent.stress > 40
                              ? "Moderate"
                              : "Low"}
                        </strong>
                      </span>
                      <div
                        className="stress-bars"
                        aria-label={`Pressure ${agent.stress} of 100`}
                      >
                        {Array.from({ length: 8 }, (_, i) => (
                          <i
                            key={i}
                            className={
                              i < Math.ceil(agent.stress / 12.5) ? "filled" : ""
                            }
                          />
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>

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
                    {latest.map((event) => (
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
              <section className="decision-panel">
                <div className="section-heading">
                  <h2>
                    <Target size={18} /> Your decisions
                  </h2>
                  <span className="action-count">{selected.length} / 2</span>
                </div>
                <p className="panel-description">
                  {finished
                    ? "The crisis is over. Explore the consequences of your decisions in the debrief."
                    : "Choose up to two actions, then let the characters react."}
                </p>
                {!finished && (
                  <>
                    <div
                      className="category-filters"
                      aria-label="Filter decisions"
                    >
                      {categories.map((item) => (
                        <button
                          key={item}
                          aria-pressed={category === item}
                          onClick={() => setCategory(item)}
                          className={category === item ? "selected" : ""}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                    <div className="action-list">
                      {game.actions
                        .filter(
                          (action) =>
                            category === "All" || action.category === category,
                        )
                        .map((action) => (
                          <button
                            key={action.id}
                            className={`action-card ${selected.includes(action.id) ? "chosen" : ""}`}
                            disabled={
                              action.disabled ||
                              busy ||
                              retryPending ||
                              (selected.length >= 2 &&
                                !selected.includes(action.id))
                            }
                            onClick={() => select(action.id)}
                            aria-pressed={selected.includes(action.id)}
                            title={action.reason || undefined}
                          >
                            <div className="action-title">
                              <strong>{action.title}</strong>
                              <span className="action-check">
                                {selected.includes(action.id) ? (
                                  <Check size={14} />
                                ) : (
                                  <Plus size={14} />
                                )}
                              </span>
                            </div>
                            <p>{action.description}</p>
                            <div className="action-meta">
                              <span>{action.category}</span>
                              <span>
                                {action.cost
                                  ? `${action.cost} budget`
                                  : "1 decision"}
                              </span>
                            </div>
                            {action.disabled && <small>{action.reason}</small>}
                          </button>
                        ))}
                    </div>
                    <div className="decision-footer">
                      {!!selected.length && (
                        <div className="selection-summary">
                          {selected.map((id) => (
                            <span key={id}>
                              {game.actions.find((a) => a.id === id)?.title}
                            </span>
                          ))}
                        </div>
                      )}
                      <button
                        className="primary-button advance-button"
                        onClick={advance}
                        disabled={busy}
                      >
                        {busy ? (
                          <LoaderCircle className="spin" size={18} />
                        ) : (
                          <Play size={16} fill="currentColor" />
                        )}
                        {busy
                          ? "The characters are reacting…"
                          : retryPending
                            ? "Resume request"
                            : selected.length
                              ? "Resolve turn"
                              : "Continue without a new action"}
                        {!busy && <ChevronRight size={18} />}
                      </button>
                      <span className="turn-hint">
                        {busy
                          ? "Up to two rounds. Your game stays saved."
                          : "Assigned work continues each turn."}
                      </span>
                    </div>
                  </>
                )}
              </section>
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
