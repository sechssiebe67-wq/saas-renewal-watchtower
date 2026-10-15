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
- Settings, session count, and history persist across reloads.
- Accessible, responsive layout for mobile, tablet, and desktop.
- Installable PWA with a web manifest and an offline-first service worker.

Focus Flow is **privacy-first by construction**: the focus history lives only on
your device. It is never uploaded, synced, or sent anywhere.

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
