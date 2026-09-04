"use client";

import dynamic from "next/dynamic";
import {
  Component,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  Box,
  Check,
  Compass,
  Monitor,
  Pause,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import type { Game } from "@/lib/types";
import { projectOffice } from "@/lib/office-state";
import "./office.css";

const OfficeScene = dynamic(() => import("./office-scene"), {
  ssr: false,
  loading: () => (
    <div className="office-loading">
      <Box size={28} />
      <span>Opening the office…</span>
    </div>
  ),
});

class SceneBoundary extends Component<
  { children: ReactNode; onUnavailable: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onUnavailable();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export default function OfficeView({
  game,
  busy,
  activeAgents,
  onShowEvent,
}: {
  game: Game;
  busy: boolean;
  activeAgents: string[];
  onShowEvent: (ids: string[]) => void;
}) {
  const room = useMemo(
    () => projectOffice(game, activeAgents),
    [activeAgents, game],
  );
  const [selected, setSelected] = useState("developer");
  const [motion, setMotion] = useState(true);
  const [reduced, setReduced] = useState(true);
  const [visible, setVisible] = useState(false);
  const [foreground, setForeground] = useState(true);
  const [flat, setFlat] = useState(false);
  const [coarsePointer, setCoarsePointer] = useState(true);
  const [touchOrbit, setTouchOrbit] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [webglReady, setWebglReady] = useState<boolean | null>(null);
  const [reset, setReset] = useState(0);
  const surface = useRef<HTMLDivElement>(null);
  const actor =
    room.characters.find((a) => a.id === selected) ?? room.characters[0];
  const onUnavailable = useCallback(() => setUnavailable(true), []);
  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pointer = window.matchMedia("(any-pointer: coarse)");
    const update = () => setReduced(preference.matches);
    update();
    const updatePointer = () => setCoarsePointer(pointer.matches);
    updatePointer();
    try {
      const probe = document.createElement("canvas");
      const context = probe.getContext("webgl2") ?? probe.getContext("webgl");
      if (context) {
        context.getExtension("WEBGL_lose_context")?.loseContext();
        setWebglReady(true);
      } else {
        setWebglReady(false);
        setUnavailable(true);
      }
    } catch {
      setWebglReady(false);
      setUnavailable(true);
    }
    preference.addEventListener("change", update);
    pointer.addEventListener("change", updatePointer);
    const visibility = () =>
      setForeground(document.visibilityState === "visible");
    visibility();
    document.addEventListener("visibilitychange", visibility);
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.05 },
    );
    if (surface.current) observer.observe(surface.current);
    return () => {
      preference.removeEventListener("change", update);
      pointer.removeEventListener("change", updatePointer);
      document.removeEventListener("visibilitychange", visibility);
      observer.disconnect();
    };
  }, []);
  const animate = motion && !reduced && visible && foreground;
  return (
    <section className="office-panel" aria-label="Crisis office">
      <header className="office-header">
        <div>
          <span className="office-kicker">YOUR TEAM, IN CONTEXT</span>
          <h2>
            <Box size={18} />
            The crisis room
          </h2>
        </div>
        <div className="office-tools">
          <button
            type="button"
            onClick={() => setMotion((v) => !v)}
            disabled={reduced || flat || unavailable || webglReady !== true}
            aria-pressed={motion && !reduced}
            aria-label={
              motion && !reduced
                ? "Pause office animation"
                : "Resume office animation"
            }
            title={
              reduced
                ? "Reduced motion is enabled on your device"
                : motion
                  ? "Pause animation"
                  : "Resume animation"
            }
          >
            {motion && !reduced ? <Pause size={15} /> : <Play size={15} />}
          </button>
          {coarsePointer && !flat && !unavailable && webglReady === true && (
            <button
              type="button"
              onClick={() => setTouchOrbit((value) => !value)}
              aria-pressed={touchOrbit}
              title={touchOrbit ? "Let the page scroll" : "Move the 3D camera"}
            >
              <Compass size={15} />
              <span>{touchOrbit ? "Scroll" : "Orbit"}</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => setReset((v) => v + 1)}
            disabled={flat || unavailable || webglReady !== true}
            aria-label="Reset office camera"
            title="Reset camera"
          >
            <RotateCcw size={15} />
          </button>
          <button
            type="button"
            onClick={() => setFlat((v) => !v)}
            disabled={unavailable || webglReady !== true}
            aria-pressed={flat || unavailable}
            title={flat ? "Show 3D office" : "Show 2D overview"}
          >
            <Monitor size={15} />
            <span>{flat || unavailable ? "2D" : "3D"}</span>
          </button>
        </div>
      </header>
      <div className="office-viewport" ref={surface}>
        <div className="office-state-label" role="status">
          <i className={busy ? "busy" : ""} />
          {busy
            ? "Resolving decisions"
            : game.status === "finished"
              ? "Final state"
              : "Saved state"}
          <span>TURN {game.turn} / 6</span>
        </div>
        {webglReady === null ? (
          <div className="office-loading">
            <Box size={28} />
            <span>Checking 3D support…</span>
          </div>
        ) : flat || unavailable ? (
          <div className="office-flat">
            <p>
              {unavailable
                ? "3D is unavailable on this device. Your game remains fully playable."
                : "Team overview · the same saved game state"}
            </p>
            <div className="office-flat-grid">
              {room.characters.map((a) => (
                <button
                  type="button"
                  key={a.id}
                  onClick={() => setSelected(a.id)}
                  aria-pressed={a.id === actor.id}
                  style={{ "--person-color": a.color } as React.CSSProperties}
                >
                  <span>{a.initials}</span>
                  <strong>{a.name}</strong>
                  <small>{a.role}</small>
                  <em>{a.pressure} pressure</em>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <SceneBoundary onUnavailable={onUnavailable}>
            <OfficeScene
              room={room}
              selected={actor.id}
              animate={animate}
              reset={reset}
              orbitEnabled={!coarsePointer || touchOrbit}
              onSelect={setSelected}
              onUnavailable={onUnavailable}
            />
          </SceneBoundary>
        )}
        <div className="office-caption">
          <span>
            {flat || unavailable
              ? "Select a teammate below"
              : coarsePointer && !touchOrbit
                ? "Tap a teammate · page scrolling stays enabled"
                : "Drag to orbit · select a teammate"}
          </span>
          <span className={`office-signal ${room.security}`}>
            {room.security === "safe" ? (
              <ShieldCheck size={12} />
            ) : (
              <ShieldAlert size={12} />
            )}
            {game.security.label}
          </span>
        </div>
        {room.delivered && (
          <div className="office-delivered">
            <Check size={14} />
            DELIVERY COMPLETE
          </div>
        )}
      </div>
      <div className="office-roster" aria-label="Select a teammate">
        {room.characters.map((a) => (
          <button
            type="button"
            key={a.id}
            onClick={() => setSelected(a.id)}
            aria-pressed={actor.id === a.id}
            style={{ "--person-color": a.color } as React.CSSProperties}
          >
            <span className="office-initials">{a.initials}</span>
            <span>
              <strong>{a.name}</strong>
              <small>{a.pressure} pressure</small>
            </span>
            <i
              style={{ "--pressure": `${a.stress}%` } as React.CSSProperties}
            />
          </button>
        ))}
      </div>
      <div className="office-detail" aria-live="polite">
        <div className="office-detail-title">
          <span style={{ background: actor.color }} />
          <strong>{actor.name}</strong>
          <span>{actor.role}</span>
          <small>{actor.status}</small>
        </div>
        <p>{actor.event?.title ?? actor.activity}</p>
        <div className="office-detail-footer">
          <span>
            Pressure <b>{actor.stress}/100</b>
            <i />
            Trust in you <b>{actor.trust}/100</b>
          </span>
          {actor.event && (
            <button
              type="button"
              onClick={() => onShowEvent([actor.event!.id])}
            >
              Read the event
              <ArrowRight size={13} />
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
