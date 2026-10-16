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
- **Session-label autocomplete:** focus the session-label field and Focus Flow
  suggests the labels you used before (e.g. "Thesis chapter 3") as an accessible
  `listbox`, so you can pick one instead of retyping it. `ArrowDown`/`ArrowUp`
  move, `Enter`/`Tab` accept, `Escape` dismisses, and a tap or click chooses an
  option; accepting one fills the input and is announced once through the
  screen-reader live region. The suggestions are built by the pure
  `recentLabels` helper in `app/history.js` from the labels already in
  `localStorage["focus-flow:history"]` (trimmed, case-insensitively
  de-duplicated, newest first, capped at 8), so the feature reads **only the
  existing history key** and adds **no new `localStorage` key, no network
  request, and no third-party dependency**. A fresh install with no history
  shows no list, and free-text labels keep working exactly as before.
- **Label aliases (session tags):** a **Label aliases** group in Settings lets
  you rename how a session label is shown — for example show `Thesis` as `PhD` —
  in every view without changing the sessions you already saved. The Stats
  filter chips and totals, the **Recent sessions** list, the autocomplete
  suggestions, the weekly and daily goal scoping, the per-label goal breakdown,
  and the Weekly review all show the alias, and stored labels that share an
  alias are merged into one row. Each change is announced once through the
  screen-reader live region, an empty alias list shows a localised empty-state
  message, and the rows re-render in the chosen language. The map is stored only
  in `localStorage["focus-flow:session-tags"]` (removed when empty) and included
  in backups. It is read by the pure `normalizeSessionTags` / `applyAliases`
  helpers in `app/history.js`, so it adds **no network request and no
  third-party dependency**; the stored history is never rewritten.
- **Weekly focus goal:** set a target number of focused minutes per week in
  Settings (optionally scoped to the currently selected label, e.g. "5 hours on
  Thesis chapter 3"). The Stats panel shows the target, minutes focused so far
  this week, a percentage, and a progress bar, and switches to a "Goal reached"
  state once you hit the target. Set it to `0` or use **Clear goal** to remove
  it. A derived **pace projection** under the per-label breakdown shows the pace
  needed to finish the week.
- **Daily focus goal:** set a target number of focused minutes for **today**
  (optionally scoped to the currently selected label). The Stats panel adds a
  **Daily goal** row with the target, today's focused minutes, a percentage, and
  a progress bar, and switches to a "Daily goal reached" state once you hit the
  target — announced once through the screen-reader live region. The row is
  hidden until a daily goal is set. The goal is derived from today's slice of the
  existing session history and stored only in
  `localStorage["focus-flow:daily-goal"]`; set it to `0` or use **Clear daily
  goal** to remove the key so a default install leaves no trace.
- **PWA app badge:** when the app is installed and a daily goal is set, the
  home-screen / desktop badge shows today's **remaining focused minutes** and is
  cleared once the goal is reached or removed. The value is decided by the pure
  `badgeState` helper, and the on-device platform badge call is
  **feature-detected**, so a browser without it is a no-op that never throws. It
  adds **no new `localStorage` key, no network request, and no third-party
  dependency**, and it is derived only from the existing `focus-flow:history`
  and `focus-flow:daily-goal` keys.
- **Per-label daily breakdown in Stats:** the Stats **Daily goal** row also
  shows a compact breakdown of today by session label — each label's focused
  minutes and its share of the target, ranked by minutes, with an `(unlabelled)`
  row when unlabelled sessions exist. It respects the active label filter (a
  filtered Stats view shows only the matching label) and stays hidden when today
  has no label rows. It is derived from the pure `dailyReview` helper in
  `app/history.js`, so it reads only the existing `focus-flow:history` and
  `focus-flow:daily-goal` keys and adds **no new `localStorage` key, no network
  request, and no third-party dependency**.
- **Per-label goal breakdown in Stats:** the Stats **Weekly goal** row also
  shows a compact breakdown of the current week by session label — each label's
  focused minutes and its share of the target, ranked by minutes, with an
  `(unlabelled)` row when unlabelled sessions exist. It respects the active
  label filter (a filtered Stats view shows only the matching label) and stays
  hidden when the week has no label rows. The breakdown is derived from the same
  pure `weeklyReview` helper as the Weekly review panel, so it reads only the
  existing `focus-flow:history` and `focus-flow:goal` keys and adds **no new
  `localStorage` key, no network request, and no third-party dependency**.
- **Weekly goal pace projection:** under that per-label breakdown, a single line
  answers *"will I hit my weekly goal at this pace?"* — it shows the rounded
  pace needed for each remaining day of the week (e.g. "≈ 45 min/day for 3 more
  days") plus a neutral **on-track / behind-pace** signal, and hides itself when
  no weekly goal is set. It respects the active label filter and the **Week
  starts on** preference, counts the remaining local calendar days (including
  today) with calendar arithmetic so daylight-saving weeks are handled
  correctly, and is announced once through the screen-reader live region when it
  first appears or the goal is reached. The line comes from the pure `goalPace`
  helper in `app/history.js`, applied to the same `weeklyReview` result, so it
  reads only the existing `focus-flow:history` and `focus-flow:goal` keys and
  adds **no new `localStorage` key, no network request, and no third-party
  dependency**.
- **Weekly focus trend sparkline:** the Stats panel adds a compact **Focus
  trend** line chart covering the **last 8 weeks** (including the current,
  partial week), one point per week of total focused minutes, so you can see at a
  glance whether your focus is trending up or down. A caption states the
  direction (**Trending up**, **Steady**, or **Trending down**) — computed by
  comparing the newest week with the week before it — plus the numeric
  min–max range. The chart is a single accessible `role="img"` region, and its
  caption is announced through the screen-reader live region when it first
  appears or its direction changes. It respects the active label filter (a
  filtered Stats view shows the trend for that label only), the **Week starts
  on** preference, and the label aliases, using the same local-calendar
  arithmetic as the weekly review so daylight-saving weeks never shift, drop, or
  duplicate a bucket. It is derived by the pure `weeklyTrend` helper in
  `app/history.js` from the existing `focus-flow:history` log only, so it adds
  **no new `localStorage` key, no network request, and no third-party
  dependency**.
- **Focus heatmap:** the Stats panel adds a compact **Focus heatmap** — a small
  grid with one cell per **local calendar day** over the trailing **12 weeks**
  (including the current, partial week), shaded from level `0` (no focused
  minutes) to level `4` (your current best day in the range). Each day is shaded
  by its total focused minutes relative to the best day, so you can see at a
  glance whether you are building a habit rather than only today or this week.
  The whole grid is a single accessible `role="img"` region with a localised
  accessible name and a min–max focused-minutes-per-day caption, every day cell
  exposes a localised `{weekday} {month} {day}: {minutes} min` `title`/`aria-label`,
  a short localised **Less … More** legend explains the shading, and an empty
  state is shown before the first session. It respects the active label filter
  (a filtered Stats view shows only the matching days), the **Week starts on**
  preference, and the label aliases, using the same local-calendar arithmetic as
  the weekly review so daylight-saving transitions never shift, drop, or
  duplicate a day. It re-renders on language, label-filter, and week-start
  changes and after each completed work phase, and it is announced once through
  the screen-reader live region when it first appears or its range changes. It
  is derived by the pure `focusHeatmap` helper in `app/history.js` from the
  existing `focus-flow:history` log only, so it adds **no new `localStorage`
  key, no network request, and no third-party dependency**.
- **Weekly review:** a dedicated panel compares the current week's focused
  minutes against the goal and ranks every session label seen this week by
  focused minutes, with its session count and its share of the target (including
  an `(unlabelled)` row when needed). It updates live when a work phase
  completes, the goal changes, or a label filter changes, and it shows a
  "Goal reached" state once the target is met.
- **Weekly review CSV export:** an **Export CSV** button in the Weekly review
  panel downloads the current week's review as
  `focus-flow-week-<YYYY-MM-DD>.csv` — a header row, one row per session label
  (label, sessions, minutes, share of the target), and a totals row. Fields
  containing commas, quotes, or newlines are quoted and their internal quotes
  doubled per RFC 4180, so labels round-trip safely into any spreadsheet. The
  button is **disabled until the week has at least one label row**. The file is
  built by the pure `weeklyReviewCsv` helper in `app/history.js` and saved
  through a browser `Blob` URL, so the export makes **no network request, adds
  no new `localStorage` key, and adds no third-party dependency** — the CSV is
  created and downloaded entirely on your device.
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
- **Bundled internationalisation:** every user-facing string comes from a small
  message catalog (`app/i18n.js`), and a **Language** switcher in Settings lets
  you pick between **English**, **Deutsch**, and **Español**. Changing it
  applies immediately — no save step — and the choice is stored only on the
  device in `localStorage["focus-flow:locale"]`. The *derived* values are
  localised too: the catalogue also carries weekday and month names, plural
  forms, and number grouping, so the Stats per-day bars, the **Recent sessions**
  timestamps, the streak text, the weekly-review label stats, and the focus
  heatmap day labels render in the
  selected language (for example `1.234,5` and `Montag` in German).
- **User-selectable first day of week:** a **Week starts on** control in
  Settings lets you start the week on **Monday** (the default) or **Sunday**. The
  choice flows through every week-scoped surface — the Stats **Weekly goal** row,
  the **Weekly review** panel and its per-label breakdown, and the streak
  day-adjacency logic. It is rendered through the bundled catalog, announced once
  through the screen-reader live region, and stored only on the device in
  `localStorage["focus-flow:week-start"]` (the key is removed when you pick the
  default).
- **Backup & restore:** a **Backup & restore** group in Settings can export all of
  your local Focus Flow data to a single
  `focus-flow-backup-<YYYY-MM-DD>.json` file — your settings, session history
  (with labels), weekly goal, daily goal, ambient-sound choice, language,
  week-start preference, and label aliases — and restore it on the same or
  another device. The
  **Restore backup** control reads a file you pick, **validates and normalises**
  it before writing, and leaves your existing data untouched if the file is not a
  usable backup (showing an inline error and announcing it). The JSON is built by
  the pure backup helpers in `app/history.js` and handed to the browser as a
  `Blob` URL; restore uses the browser's `FileReader`. Nothing is uploaded, and
  the feature adds **no new `localStorage` key, no network request, and no
  third-party dependency**.
- Settings, session count, history, the weekly goal, the daily goal, the
  ambient-sound choice, the language, and the week-start choice persist across
  reloads.
- Accessible, responsive layout for mobile, tablet, and desktop.
- Installable PWA with a web manifest and an offline-first service worker.

Focus Flow is **privacy-first by construction**: the focus history, any session
labels you type, your weekly focus goal, your daily focus goal, your
ambient-sound choice, your language preference, your week-start preference, and
your label aliases
live only on your device. They are never uploaded, synced, or sent anywhere. The
**Daily goal** row in the Stats panel is derived from today's slice of the
existing session history, so it adds no history key and no upload of its own. Its
**per-label daily breakdown** is derived from the same history and daily-goal
keys by the pure `dailyReview` helper, so it too adds no new `localStorage` key,
no network request, and no third-party dependency, and the **PWA app badge** is
decided by the pure `badgeState` helper and pushed through a
**feature-detected, on-device** platform call, adding no new key, no network
request, and no third-party dependency either. The
weekly review, the **weekly review CSV export**, the **per-label goal breakdown
in the Stats panel**, the **weekly goal pace projection**, the **weekly focus
trend sparkline**, the **focus heatmap**, the focus streaks,
the daily reminder hint, and the
**session-label autocomplete** are all **derived** from that existing local data
only — they add no new storage key, no network request, and no third-party
dependency. The weekly focus trend sparkline in particular is derived from the
same `focus-flow:history` log by the pure `weeklyTrend` helper, so it reads no
storage of its own, adds no new key, makes no network request, and adds no
third-party dependency. The focus heatmap in particular is derived from the
same `focus-flow:history` log by the pure `focusHeatmap` helper, so it reads no
storage of its own, adds no new key, makes no network request, and adds no
third-party dependency. The weekly goal pace projection in particular is derived from the
same `weeklyReview` result by the pure `goalPace` helper, so it reads only the
existing `focus-flow:history` and `focus-flow:goal` keys, adds no new key, makes
no network request, and adds no third-party dependency. The autocomplete in
particular reads only the labels already in
`focus-flow:history` and never uploads, adds, or reorders anything. The label
aliases are read by pure helpers and stored only under the optional
`focus-flow:session-tags` key, so they add no network request, no third-party
dependency, and no upload, and they never rewrite the stored history. The CSV
is written by a pure helper and handed to the browser as a local `Blob` URL, so
it is created and saved entirely on your device and never leaves it. The
**backup & restore** JSON is likewise built by a pure helper and handed over as a
local `Blob` URL, then read back with the browser's `FileReader`, so it is
created, saved, and restored entirely on your device, adds no new `localStorage`
key, and never leaves it. The ambient
sound is generated locally and adds no audio file, no network request, and no
third-party asset. The i18n catalog is bundled locally, so localisation adds no
network request and no third-party library. All data stays on the device.

### Storage keys

All state lives in the browser's `localStorage`:

- `focus-flow:settings` — work/break durations, long-break interval, chime and
  auto-start-break toggles.
- `focus-flow:sessions` — the running "sessions completed today" counter.
- `focus-flow:theme` — the remembered light/dark choice.
- `focus-flow:history` — the local session log (capped at 500 entries / 90
  days).
- `focus-flow:goal` — the optional weekly focus goal.
- `focus-flow:daily-goal` — the optional daily focus goal, shaped `{ minutes,
  label? }` (minutes for today, optionally scoped to a session label); removed
  when the goal is `0`/empty.
- `focus-flow:ambient` — the optional ambient-sound `{ type, volume }`; removed
  when the type is `off`.
- `focus-flow:locale` — the canonical locale id for the chosen language;
  removed when the locale is the default (`en`).
- `focus-flow:week-start` — the optional first-day-of-week preference (`0` =
  Sunday, `1` = Monday), rendered through the bundled catalog; removed when the
  default Monday is selected.
- `focus-flow:session-tags` — the optional `{ label: alias }` display map for
  **label aliases**, coerced by the pure `normalizeSessionTags` helper; removed
  when the map is empty, and included in backups.

The Stats **Weekly goal** per-label breakdown, its **pace projection**, the
**weekly focus trend sparkline**, the **focus heatmap**, the
Weekly review panel, the CSV
export, the focus streaks, and the daily reminder hint are all **derived** from
`focus-flow:history` and `focus-flow:goal` and add **no new storage key**. The
breakdown is rendered by the same pure `weeklyReview` helper and the pace line by
the pure `goalPace` helper, so they
make no network request and add no third-party dependency. The trend sparkline is
derived by the pure `weeklyTrend` helper and the heatmap by the pure
`focusHeatmap` helper, both straight from the `focus-flow:history`
log, so they too add no key, make no network request, and add no third-party
dependency.

The Stats **Daily goal** row is derived from the same `focus-flow:history` log by
the pure `dailyGoalProgress` helper in `app/history.js`, which sums only
completed work entries whose `endedAt` falls on the current local calendar day.
It reads no storage of its own and makes no network request.

The Stats **per-label daily breakdown** and the **PWA app badge** are derived
from the same `focus-flow:history` and `focus-flow:daily-goal` keys by the pure
`dailyReview` and `badgeState` helpers, so they add **no new `localStorage`
key**, make no network request, and add no third-party dependency. A default
install still stores nothing new, and the badge call is feature-detected so
browsers without it are unaffected.

The **session-label autocomplete** is derived from the same `focus-flow:history`
log by the pure `recentLabels` helper in `app/history.js`, which returns the
newest distinct labels for the suggestion list. It reads **only the existing
history key**, adds no new `localStorage` key, makes no network request, and
adds no third-party dependency, so the labels stay on the device.

**Backup & restore** adds **no new `localStorage` key** and makes no network
request: the exported JSON mirrors the existing keys listed above (settings,
history, goal, daily goal, ambient, locale, week start, and label aliases) and a restored file
is normalised with the same pure helpers before those keys are rewritten. The
file is created and read entirely on the device.

The full concept, audience, roadmap, and criteria mapping live in
[`CONCEPT.md`](CONCEPT.md).

## Languages

Focus Flow ships **English** (`en`), **German** (`de`), and **Spanish** (`es`).
Pick a language from the **Language** dropdown in Settings; the change applies
immediately, with no save step, and every visible string — including the
screen-reader announcements — updates at once.

The catalog lives in [`app/i18n.js`](app/i18n.js). It is **bundled with the app
and fully offline**: there is no network request, no third-party library, and no
runtime download. Unknown or malformed stored values fall back to English, and a
message missing from a locale falls back to English and then to its own key, so
the page never breaks. Message keys are shared across locales (verified by the
test suite), and the rendered labels are localised from the same catalog.

The same file also carries a frozen `LOCALE_DATA` map and the pure helpers
`formatNumber`, `formatWeekday`, `formatMonth`, `formatDuration`, and
`pluralise`. Weekday and month names, decimal/group separators, and plural forms
are read from those bundled tables rather than from `Intl` or any network
service, so dates, numbers, and durations localise with the rest of the UI.
This adds **no new `localStorage` key** — only the optional
`focus-flow:locale` preference described below is persisted — and no new
dependency or request.

Your language choice is saved **only on the device** under
`localStorage["focus-flow:locale"]`. A default install stores nothing, and the
choice is never uploaded, synced, or sent anywhere.

The same bundled catalog also labels the **Week starts on** preference in
Settings, so the first-day-of-week choice is localised with the rest of the UI.
It adds no network request, no third-party dependency, and no storage beyond the
optional `focus-flow:week-start` key described above.

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
