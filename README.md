# Focus Flow

Focus Flow is a **distraction-free, offline-capable focus timer** delivered as a
static, client-side web app. It helps students, remote knowledge workers, and
anyone who benefits from structured work/break cycles run Pomodoro-style
sessions without accounts, databases, tracking, or any external service.

Everything runs in the browser and all state (settings, session count, and
focus history) is stored locally in `localStorage`. There are no runtime network
calls, no telemetry, and no secrets.

## Features

- Configurable work / short break / long break durations.
- Start, pause, reset, and skip controls.
- Keyboard shortcuts: `Space` start/pause, `R` reset, `S` skip.
- Automatic long break every 4 work sessions (interval configurable).
- Session counter, dark/light theme, audible and visual notifications.
- **Local session history:** every completed work phase is logged to
  `localStorage["focus-flow:history"]` (capped at 500 entries / 90 days), and a
  **7-day stats panel** shows the total sessions, focused minutes, and a
  per-day count. Skipped phases are not recorded.
- **Optional session labels:** type a short label (e.g. "Thesis chapter 3") on
  the timer card and it is attached to the next completed work phase. The Stats
  panel turns the labels from the last 7 days into **filter chips** — select one
  to filter the totals and per-day bars to that label (or the `(unlabelled)`
  chip for entries without one) — and a **Recent sessions** list shows the
  newest five entries. Labels are capped at 40 characters and cleared after each
  completed work phase.
- **Weekly focus goal:** set a target number of focused minutes per week in
  Settings (optionally scoped to the currently selected label, e.g. "5 hours on
  Thesis chapter 3"). The Stats panel shows the target, minutes focused so far
  this week, a percentage, and a progress bar, and switches to a "Goal reached"
  state once you hit the target. Set it to `0` or use **Clear goal** to remove
  it.
- **Weekly review:** a dedicated panel compares the current week's focused
  minutes against the goal and ranks every session label seen this week by
  focused minutes, with its session count and its share of the target (including
  an `(unlabelled)` row when needed). It updates live when a work phase
  completes, the goal changes, or a label filter changes, and it shows a
  "Goal reached" state once the target is met.
- **Focus streaks & daily reminder hint:** the Stats panel derives a **current
  streak** (consecutive local calendar days, ending today or yesterday, with at
  least one completed work session) and a **longest streak** from your local
  session log, and shows how many sessions and focused minutes you have logged
  today. Days are compared with local calendar arithmetic, so daylight-saving
  transitions never break a streak. When
  today has no completed session *and* a weekly goal is set, a neutral **"No
  focus session logged today yet."** hint appears. The streak increases the
  moment a work phase completes and the new value is announced once through the
  existing screen-reader live region.
- **Optional ambient sound:** choose **brown noise**, **pink noise**, or **soft
  rain** — or keep the default **Off** — and set the volume in Settings. The
  loop plays during work sessions (and through breaks when they auto-start) and
  is silenced whenever you pause or reset the timer. Every sound is
  **synthesised in the browser with the Web Audio API**, so no audio files are
  downloaded or shipped and no network request is made; your choice and volume
  are stored only in `localStorage["focus-flow:ambient"]`.
- Settings, session count, history, the weekly goal, and the ambient-sound
  choice persist across reloads.
- Accessible, responsive layout for mobile, tablet, and desktop.
- Installable PWA with a web manifest and an offline-first service worker.

Focus Flow is **privacy-first by construction**: the focus history, any session
labels you type, your weekly focus goal, and your ambient-sound choice live only
on your device. They are never uploaded, synced, or sent anywhere. The weekly
review, the focus streaks, and the daily reminder hint are all **derived** from
that existing local data only — they add no new storage key, no network request,
and no third-party dependency. The ambient sound is generated locally and adds
no audio file, no network request, and no third-party asset. All data stays on
the device.

### Storage keys

All state lives in the browser's `localStorage`:

- `focus-flow:settings` — work/break durations, long-break interval, chime and
  auto-start-break toggles.
- `focus-flow:sessions` — the running "sessions completed today" counter.
- `focus-flow:theme` — the remembered light/dark choice.
- `focus-flow:history` — the local session log (capped at 500 entries / 90
  days).
- `focus-flow:goal` — the optional weekly focus goal.
- `focus-flow:ambient` — the optional ambient-sound `{ type, volume }`; removed
  when the type is `off`.

The full concept, audience, roadmap, and criteria mapping live in
[`CONCEPT.md`](CONCEPT.md).

## Run locally

The app needs no build step. Serve the `app/` directory with any static server:

```sh
cd app
python3 -m http.server 8080
```

Then open <http://localhost:8080>.

## Install as an app

Focus Flow is a Progressive Web App. Serve it over `https:` (or `localhost`),
open it in a modern browser, and use the install icon in the address bar — or
your browser's "Install" / "Add to Home Screen" action — to add it to your
desktop or home screen. It then launches standalone, without browser chrome.

A service worker (`app/service-worker.js`) precaches the app shell and assets on
the first visit. **After that first load the app keeps working fully offline**,
including the timer, settings, and session counter, so a flaky connection never
interrupts a focus session. No runtime network calls, telemetry, or third-party
requests are introduced; the service worker only handles same-origin `GET`
requests and ignores everything else.

To try the offline mode: load the app, then open your browser DevTools and
switch the network to "Offline" and reload. The page still loads and the timer
still runs.

## Run the tests

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The suite checks the static assets and structure, the `Dockerfile`, and renders
the Helm chart with `helm template`. The pipeline's own generator tests live in
`.github/scripts` and run with
`python3 -m unittest discover -s .github/scripts -p 'test_*.py' -v`.

## Container

```sh
docker build -t focus-flow:local .
docker run --rm -p 8080:8080 focus-flow:local
```

The image serves `app/` with nginx (unprivileged) and exposes `/healthz` for
health checks. The listen port is configurable via the `PORT` environment
variable.

## Deployment

The Helm chart in [`helm/`](helm) renders a `Deployment`, `Service`, `Ingress`,
resource requests/limits, and liveness/readiness probes that hit `/healthz`:

```sh
helm template focus-flow helm
```

Argo CD syncs this chart into the existing k3s cluster. No database, external
API, or additional infrastructure is required.

## Create an independent project

This repository ships an autonomous development pipeline alongside the product.
To reuse it for a new idea, export the tree without Git history and initialize a
fresh repository:

```sh
mkdir ../my-new-project
git archive empty-repo | tar -x -C ../my-new-project
cd ../my-new-project
git init -b main
git add .
git commit -m "chore: initialize empty development pipeline"
```

See [`.github/README.md`](.github/README.md) for the required secrets and
repository settings.
