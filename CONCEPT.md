# Focus Flow — Concept

## Goal

Focus Flow is a distraction-free, offline-capable **focus timer** delivered as a
static web application. It helps people structure their work into deliberate
work/break cycles using the Pomodoro technique, without accounts, databases,
tracking, or any external service.

The repository goal is to keep the whole product small enough to understand in
one sitting: a handful of plain HTML/CSS/JS files, a minimal container image,
and a Helm chart that renders on the existing k3s / Argo CD pipeline. Anyone can
serve the `app/` directory with any static file server and get the full product.

### Why this exists

- **Real user value:** structured work/break cycles reduce context switching and
  help sustain attention; the timer removes the need for a phone or a third-party
  SaaS account.
- **Low cost and low maintenance:** there is no backend, no database, and no
  runtime network traffic, so operating costs approach zero and there is nothing
  to patch beyond the base container image.
- **Privacy by construction:** all state lives in the browser's `localStorage`.
  No data ever leaves the device, so there is no personal data to protect or
  leak.

## Intended users

- **Students** who need to pace study blocks and scheduled breaks.
- **Remote knowledge workers** who want a lightweight timer that does not add
  another account or browser extension.
- **Anyone** who benefits from structured work/break cycles, including people
  with attention or task-initiation difficulties.

The product is usable on a phone, tablet, or desktop, and works fully offline
after the first load.

## Current capabilities (MVP)

- Configurable **work**, **short break**, and **long break** durations.
- A timer **state machine** for work / short break / long break phases.
- **Start, pause, reset, and skip** controls.
- **Keyboard shortcuts:** `Space` start/pause, `R` reset, `S` skip.
- **Session counter** with an automatic **long break every 4 work sessions**
  (interval configurable).
- **Session history & stats:** every completed *work* phase is appended to a
  fully local log (`app/history.js`), and a collapsible **Stats** panel
  summarises the last 7 days — total completed work sessions, total focused
  minutes, and a per-day list that pairs each bar with its numeric count.
  Skipped phases are not recorded. The log is capped at 500 entries and 90 days
  so `localStorage` cannot grow unbounded.
- **Optional session labels:** a user can type a short label (e.g. "Thesis
  chapter 3") on the timer card before or during a work phase, and the label is
  attached to the next completed work entry. The Stats panel lists the labels
  seen in the last 7 days as filter chips — selecting one filters the totals
  and per-day bars to that label (and the `(unlabelled)` chip to entries without
  one), and a **Recent sessions** list shows the newest five entries. Labels
  are stored only in `localStorage` and are never uploaded.
- **Weekly focus goal:** a user can set a target number of focused minutes for
  the current week (e.g. `300`), optionally scoped to a single session label so
  the target can read "5 hours on Thesis chapter 3". The Stats panel renders a
  goal row with the target, the minutes focused so far this week, a percentage,
  and a `role="progressbar"` bar; once the target is met the row switches to a
  clear, non-intrusive **"Goal reached"** state and the app announces it once
  through the existing ARIA live region. The goal can be changed or cleared
  (a `0`/empty value, or the **Clear goal** control) from the settings form.
  The whole goal lives only in `localStorage` under `focus-flow:goal` and is
  never uploaded.
- **Weekly review:** a dedicated panel lines the weekly goal up against the
  per-label breakdown for the current week. It shows the focused minutes so far
  against the target, a percentage, and a `role="progressbar"` bar, plus a
  per-label list that ranks each label seen this week by focused minutes with its
  session count and its share of the target (including an `(unlabelled)` row when
  unlabelled sessions exist). When the target is met the panel shows a clear
  **"Goal reached"** state and the app announces it once through the ARIA live
  region. The review reads the existing history and goal keys only and adds no
  new `localStorage` key.
- **Focus streaks & daily reminder hint:** the Stats panel derives a **current
  streak** (the number of consecutive local calendar days, ending today or
  yesterday, on which at least one completed work session was logged) and a
  **longest streak** from the local session log, and shows today's
  completed-session count and focused minutes. Day adjacency is computed with
  local calendar arithmetic, so a 23h/25h daylight-saving transition does not
  break or shorten a run. A neutral **"No focus session logged today yet."**
  reminder appears only when today has no completed work *and* a weekly goal is
  set. The values come from a new pure `streaks` helper and read only the
  existing `focus-flow:history` and `focus-flow:goal` keys — there is **no new
  `localStorage` key, no network request, and no new runtime dependency**.
- **Audible and visual notifications** when a phase ends.
- **Local persistence** of settings, the current session count, and the session
  history via `localStorage`.
- **Dark / light theme** toggle that is remembered.
- **Responsive layout** for mobile (360px), tablet (768px), and desktop (1280px).
- **Accessible markup:** semantic landmarks, a skip link, an ARIA live region
  that announces timer/phase updates, visible focus states, and a
  high-contrast palette.
- **Installable PWA:** `manifest.webmanifest` with original 192px, 512px, and
  maskable icons, so the app can be added to a home screen or desktop and
  launched standalone.
- **Offline-first service worker:** `service-worker.js` precaches the static
  shell and serves cached responses when the network is unavailable, so a focus
  session never breaks because of a flaky connection. After the first visit the
  app keeps working fully offline.

## Repository structure

- `app/` — the whole product, served as static files.
  - `index.html`, `styles.css` — the accessible, responsive shell.
  - `timer.js` — the pure timer state machine.
  - `history.js` — the pure session-history helpers (`recordSession`,
    `pruneHistory`, `summarise`, `labelSummary`, `recentSessions`,
    `normalizeGoal`, `weekWindow`, `goalProgress`, `weeklyReview`, `streaks`,
    `HISTORY_VERSION`, `GOAL_STORAGE_SHAPE_VERSION`) with no DOM access.
    `weeklyReview` returns the current week's goal versus per-label breakdown
    (`{ weekStart, targetMinutes, focusedMinutes, remainingMinutes, percent,
    reached, labels, perLabel }`), and `streaks` returns the derived
    consistency view (`{ current, longest, todayCount, todayMinutes,
    lastActiveDay }`).
  - `main.js` — the DOM layer and the `registerServiceWorker()` helper.
  - `manifest.webmanifest` — the PWA manifest (name, icons, colours, scope).
  - `service-worker.js` — versioned cache, precache list, and offline handlers.
  - `icons/` — original artwork: `icon.svg` source, `icon-192.png`,
    `icon-512.png`, `icon-maskable-512.png`, and the
    `generate_icons.py` rasteriser.
  - `healthz` — static health endpoint.
- `docker/` — the nginx template that serves the app with the right content
  types and caching rules.
- `Dockerfile` — unprivileged nginx image.
- `helm/` — the Kubernetes chart.
- `tests/` — static, PWA, and Helm rendering tests.

## Data & persistence

Focus Flow stores everything in the browser's `localStorage`; no data ever
leaves the device. There is no backend, no account, and no sync.

| Key | Shape | Notes |
| --- | --- | --- |
| `focus-flow:settings` | `{ work, shortBreak, longBreak, longBreakInterval, sound, autoStartBreaks }` | Timer configuration. |
| `focus-flow:sessions` | integer | Running "sessions completed today" counter, kept for backwards compatibility. |
| `focus-flow:theme` | `"light"` \| `"dark"` | Remembered theme choice. |
| `focus-flow:history` | array of `{ endedAt, phase, durationSeconds, label? }` | Local session log. `endedAt` is an ISO timestamp, `phase` is `"work"`, and `durationSeconds` is the configured work duration. `label` is optional: a trimmed string of at most 40 characters, and it is absent when the user leaves the session-label field empty. Only completed work phases are appended; the log is pruned to the most recent 500 entries and 90 days. `HISTORY_VERSION` in `app/history.js` documents the entry schema version: **version 2** adds the optional `label` field, and version 1 entries (which have no `label`) remain valid and still count toward the 7-day totals. |
| `focus-flow:goal` | `{ minutes, label? }` | Optional **weekly focus goal**. `minutes` is an integer clamped to `0..10080` (a full week; `0` means "no goal"), and `label` is an optional trimmed string of at most 40 characters that scopes the goal to a single session label. The goal is stored **only in `localStorage`** and is never uploaded; `GOAL_STORAGE_SHAPE_VERSION` in `app/history.js` documents the shape version, and `normalizeGoal` coerces older or malformed values. |

The **Weekly review** panel is derived, not stored: it reads only the existing
`focus-flow:history` and `focus-flow:goal` keys through the pure `weeklyReview`
helper and adds no new `localStorage` key and no network request.

The **focus streaks** and the daily reminder hint are derived the same way: the
pure `streaks` helper turns `focus-flow:history` into a current/longest streak
and today's totals, the reminder compares `todayCount` against the presence of a
`focus-flow:goal`, and nothing new is persisted or transmitted.

## Next direction

- [x] **Focus streaks and reminders**, derived locally from the session history
  and building on the weekly goal and weekly review panels.
- [ ] Optional **ambient sound** (e.g. brown noise / rain) using the Web Audio API.
- [ ] **Internationalisation (i18n)** with a small message catalog.

## How the repository meets its own criteria

### Hard requirements (MUST)

| Requirement | How Focus Flow satisfies it |
| --- | --- |
| Web Deployable | Static SPA served from `app/`; installable PWA with a manifest and service worker that runs in any modern browser. |
| Originality | A no-account, offline, single-file focus timer with explicit privacy and k3s/GitOps packaging; not a copy of an existing product. |
| Expandable | Pure timer engine (`app/timer.js`) is decoupled from the DOM layer (`app/main.js`), so features slot in without rewrites. |
| Real User Value | Structures work/break cycles to improve focus and reduce context switching. |
| Clearly Defined Audience | Students, remote knowledge workers, and anyone needing structured cycles. |
| Standalone | No dependency on any other AI Product Factory application. |
| Autonomous Operation | No backend; nothing to administer after deployment, and the service worker keeps the app usable offline. |
| Kubernetes Compatible | `Dockerfile` + `helm/` chart with `Deployment`, `Service`, `Ingress`, probes, and resource limits. |
| Resource Efficient | Tiny nginx:alpine image, static files only, small CPU/RAM requests and limits in `helm/values.yaml`. |
| Security | No secrets, no runtime external calls, no telemetry, no user input leaves the browser; the service worker ignores cross-origin and non-GET requests; container runs as non-root. |
| Testable | `tests/` verifies assets, structure, the PWA manifest and service worker, and Helm rendering via `unittest`. |
| Maintainable | Plain HTML/CSS/JS with no build step and clear project structure. |
| Legal Compliance | Original code, no third-party assets, no personal data collected. |
| Health Monitoring | `/healthz` static endpoint used by liveness/readiness probes. |
| Unique Product Identity | Product name "Focus Flow", own repository, own subdomain via the Helm ingress. |

### Soft requirements (SHOULD)

| Requirement | How Focus Flow addresses it |
| --- | --- |
| Database Independence | Uses only `localStorage`; no database. |
| Monetization Potential | Future paid themes/ambient packs or a hosted team dashboard; the core stays free. |
| Low Operating Costs | Static assets, near-zero CPU/RAM, no external APIs; the service worker removes repeated network round-trips. |
| Fast MVP Development | No build tooling; the MVP is a few files. |
| Low Maintenance | No backend or data migrations to maintain. |
| Market Differentiation | Privacy-first, offline, no-account, and packaged as a Kubernetes-native OSS app. |
| Growth Potential | Serving more users costs effectively nothing. |
| User Retention | Daily use pattern; persistent settings, session counts, and a 7-day focus-history panel that shows progress; optional per-session labels, a label filter, and a weekly review that ranks each label against the weekly goal let users see where their focus went; a derived current/longest focus streak and a gentle daily reminder hint encourage users to come back and keep the streak alive, plus one-tap install to the home screen or desktop. |
| Discoverability | Clear name, description, and docs; shareable as a URL. |
| Mobile Friendly | Responsive layout, touch-friendly controls, and an installable PWA that launches standalone. |
| Accessibility | Semantic landmarks, ARIA live region, keyboard shortcuts, focus states, contrast. |
| Minimal Dependencies | Zero runtime JS/CSS dependencies. |
| Measurable Success | `/healthz` for reliability; the local session history, 7-day stats, optional label breakdown, the weekly focus goal, and the weekly review give users a visible, measurable view of their focus habit, including what each block of time was spent on and how close each label came to their weekly target; the derived current/longest focus streak and today's totals make consistency itself measurable. |
| Reusability | Reuses the standard static-container + Helm deployment template. |
| Innovation Potential | Ambient sound and internationalisation remain natural next steps after the shipped focus streaks and weekly review. |

## Repository criteria (canonical definitions)

These are the requirements every product in this repository must be evaluated
against. The tables above map Focus Flow to each one.

### Hard Requirements (MUST)

Every product must satisfy these requirements before the Salesman can approve its development.

- **Web Deployable:** Must run as a web application and be accessible through a browser.
- **Originality:** Must not be a direct copy of an existing product, whether internally developed or commercially available. Existing concepts may be combined or significantly improved to create something unique.
- **Expandable:** Must have an architecture that allows additional features and future improvements.
- **Real User Value:** Must solve a real problem, provide entertainment, improve productivity, or offer another clearly identifiable benefit.
- **Clearly Defined Audience:** Must have at least one identifiable target audience.
- **Standalone:** Must function independently without requiring another AI Product Factory application.
- **Autonomous Operation:** Must operate without continuous human intervention after deployment.
- **Kubernetes Compatible:** Must be containerized and deployable on the existing k3s cluster using Helm and Argo CD.
- **Resource Efficient:** Must stay within defined CPU, RAM, and storage budgets.
- **Security:** Must follow basic security practices, including dependency scanning, safe secret handling, and input validation.
- **Testable:** Must support automated testing and have measurable acceptance criteria.
- **Maintainable:** Must contain readable source code, clear project structure, and sufficient technical documentation.
- **Legal Compliance:** Must respect software licences, copyright, privacy regulations, and applicable laws.
- **Health Monitoring:** Must expose a reliable way to verify whether the deployment is healthy.
- **Unique Product Identity:** Must have a unique repository name, product name, and subdomain.

### Soft Requirements (SHOULD)

These requirements should influence the Salesman's evaluation and ranking.

- **Database Independence:** Should preferably work without a database. A database is allowed when persistent storage adds meaningful value.
- **Monetization Potential:** Should have a realistic path to revenue, such as subscriptions, advertisements, one-time purchases, or paid features.
- **Low Operating Costs:** Should require minimal infrastructure, external APIs, and paid services.
- **Fast MVP Development:** Should ideally have a deployable minimum viable product within a limited development budget.
- **Low Maintenance:** Should require minimal ongoing maintenance and manual administration.
- **Market Differentiation:** Should offer a meaningful advantage over existing alternatives.
- **Growth Potential:** Should be able to attract additional users without a proportional increase in operating costs.
- **User Retention:** Should provide reasons for users to return regularly.
- **Discoverability:** Should be understandable, searchable, and easy to share.
- **Mobile Friendly:** Should work well on smartphones, tablets, and desktop browsers.
- **Accessibility:** Should follow established accessibility principles.
- **Minimal Dependencies:** Should avoid unnecessary external services and vendor lock-in.
- **Measurable Success:** Should provide metrics that help evaluate adoption, reliability, and product value.
- **Reusability:** Should preferably reuse existing components, design patterns, and deployment templates.
- **Innovation Potential:** Should have opportunities for unique features or future experimentation.

### Product Rejection Criteria

The Salesman must reject a product idea if:

- It is merely a clone without meaningful differentiation.
- Its purpose or target audience cannot be explained clearly.
- It cannot run within the available infrastructure budget.
- It requires unavailable credentials, licences, hardware, or external services.
- It introduces unacceptable security, legal, or privacy risks.
- It has no realistic path to a working MVP.
- It requires continuous manual operation.
- It offers no meaningful advantage over an already active product.
- Its projected value does not justify its development and operating costs.

### Product Lifecycle Requirements

Every approved product must support:

1. **Creation:** A dedicated GitHub repository is created.
2. **Development:** The AI Developer implements the MVP.
3. **Review:** Automated testing and AI code review validate the product.
4. **Deployment:** Helm and GitOps configuration deploy the application.
5. **Monitoring:** Operational health and product performance are evaluated.
6. **Iteration:** The product can receive additional features and improvements.
7. **Archival:** The repository is preserved while the deployment and Helm chart are removed.
8. **Reactivation:** An archived product can be rebuilt and deployed again if its potential improves.

The maximum number of simultaneously active product repositories is **10**.

## Operating notes

- **Run locally:** `python3 -m http.server 8080` from `app/`, then open
  <http://localhost:8080>. `localhost` counts as a secure context, so the
  service worker registers and offline mode can be tested in DevTools.
- **Regenerate icons:** `python3 app/icons/generate_icons.py`.
- **Run tests:** `python3 -m unittest discover -s tests -p 'test_*.py' -v`.
- **Render the chart:** `helm template focus-flow helm`.
- **Deploy:** build the image from `Dockerfile`, publish it, and let Argo CD
  sync the `helm/` chart into k3s.
