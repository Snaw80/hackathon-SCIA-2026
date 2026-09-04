# Three.js office implementation plan

> **For agentic workers:** Implement in the current session using the existing approved product brief. Check each deliverable before proceeding.

**Goal:** Finish the presentation layer with an interactive office driven by the public game state.

**Architecture:** A pure projection converts `Game` into room and character presentation state. A lazily loaded React Three Fiber scene renders local low-poly geometry. A DOM wrapper provides character selection, activity details, motion controls, and a usable fallback; existing game actions remain authoritative.

**Tech stack:** Next.js / React 19, Three.js, React Three Fiber 9, Drei, TypeScript.

**Spec:** `brainstorm.md`, “Utilisation du bureau 3D”, and the user's explicit request to implement Three.js now.

## Constraints

- All website copy stays English; hackathon report stays French.
- Consume only `Game` from the existing public API. No hidden knowledge, new game rules, API calls, or model costs from the scene.
- Procedural low-poly office assets live in code; no external asset/CDN dependency.
- Preserve the existing local Next.js/FastAPI architecture and current feature branch.
- Keyboard-accessible character buttons, reduced-motion support, pause/reset controls, responsive layout, WebGL failure fallback.

## Deliverables

- [x] State projection and regression tests (`web/lib/office-state.ts`, `web/tests/office-state.test.mjs`). Map stress, public security, current-turn actor events, visible negotiations, release status; never replay a previous-turn action as current. Freeze input state. Run `npm --prefix web test`.
- [x] Scene (`web/components/office/office-scene.tsx`, `office-objects.tsx`). Four desks and unique low-poly characters, meeting table, plants, security screen, task progress display. Animate transitions and character posture from projected state. Frame the room responsively; cap DPR and pause offscreen.
- [x] Dashboard wrapper (`office-view.tsx`, `office.css`, dashboard insertion). Lazy-load Canvas with SSR disabled; selection details link to actual journal events. Provide DOM alternatives, motion toggle, and camera reset. Controls never advance a game turn.
- [x] Verify compilation and existing backend regressions with network-isolated tests, review the implementation independently, update README/report/journal, and commit. Visual browser testing is outside this run unless explicitly requested.
