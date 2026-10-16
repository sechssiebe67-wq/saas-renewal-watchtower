# Focus Flow — Concept

## Goal

Focus Flow is a distraction-free, offline-capable **focus timer** delivered as a
static web application. It helps people structure their work into deliberate
work/break cycles using the Pomodoro technique, without accounts, databases,
tracking, or any external service.

Alongside the timer it offers local, privacy-first planning aids: a **weekly
focus goal** that answers *"am I on pace this week?"* and a **daily focus goal**
that answers *"have I done enough today?"*. Both are derived from the same
on-device session history, stored only in `localStorage`, and never uploaded.

The repository goal is to keep the whole product small enough to understand in
one sitting: a handful of plain HTML/CSS/JS files, a minimal container image,
and a Helm chart that renders on the existing k3s / Argo CD pipeline. Anyone can
serve the `app/` directory with any static file server and get the full product.
It follows the user's own conventions where it can — language, sound, and the
first day of the week are all local, device-only preferences.

### Why this exists

- **Real user value:** structured work/break cycles reduce context switching and
  help sustain attention; the timer removes the need for a phone or a third-party
  SaaS account.
- **Low cost and low maintenance:** there is no backend, no database, and no
  runtime network traffic, so operating costs approach zero and there is nothing
  to patch beyond the base container image.
- **Privacy by construction:** all state lives in the browser's `localStorage`.
  No data ever leaves the device, so there is no personal data to protect or
  leak. Everything the product adds on top of the raw log — the weekly and daily
  goals, the weekly review, the weekly and daily goal paces, the streaks, the
  **weekly focus trend sparkline**, the **daily focus
  trend sparkline**, the **focus heatmap**, the
  **focus share donut**, and the **30-day focus summary** — is
  **derived locally** from that same on-device history by pure functions, so it
  needs no server, no third-party service, and no upload.

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
- **Session-label autocomplete:** focusing the optional session-label field
  offers the labels already used in earlier sessions (e.g. "Thesis chapter 3")
  as a keyboard-accessible suggestion list, so a returning user can pick one
  instead of retyping it. Suggestions come only from the existing
  `focus-flow:history` log, derived by the pure `recentLabels` helper in
  `app/history.js` (trimmed, non-empty, case-insensitively de-duplicated,
  newest first by `endedAt`, capped at 8). The DOM layer renders a
  `<ul role="listbox">` of `role="option"` items under the input and supports
  `ArrowDown`/`ArrowUp` to move, `Enter`/`Tab` to accept, `Escape` to dismiss,
  and click/tap to choose; the accessible name comes from the bundled catalog.
  Free text is untouched when no suggestion is chosen, accepting a suggestion
  fills the input and announces the label once through the existing ARIA live
  region, and a fresh install with no history shows no list at all. The feature
  adds **no new `localStorage` key, no network request, and no third-party
  dependency**, keeping the privacy-by-construction invariant.
- **Label aliases (session tags):** a device-only **Label aliases** group in
  Settings lets a user rename how a session label is *displayed* without
  rewriting the stored `focus-flow:history` log. Each alias maps an original
  label to a display label (e.g. `Thesis` → `PhD`); every derived view — the
  Stats filter chips and per-label totals, the **Recent sessions** list, the
  session-label autocomplete, the weekly and daily goal scoping, the per-label
  goal breakdown, and the **Weekly review** — shows the alias, and several
  stored labels that share one alias are merged into a single row. The map is
  coerced by the pure `normalizeSessionTags` helper in `app/history.js`
  (trimmed, non-empty, length-capped, case-insensitively de-duplicated,
  entry-capped) and read by the pure `applyAliases` helper; the DOM layer
  threads it into the derived views through a `tags` option that defaults to
  `undefined`, so omitting it keeps the previous behaviour byte-for-byte.
  Adding or removing an alias is announced once through the existing ARIA live
  region, an empty list shows a localised empty-state message, every row is
  re-rendered when the language changes, and a default install stores nothing.
  The map lives only in `localStorage` under
  `focus-flow:session-tags` (the key is removed when the map is empty) and is
  included in the local backup; the pure module stays DOM-, storage-, and
  network-free.
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
- **Daily focus goal:** a user can set a target number of focused minutes for
  **today** (e.g. `50`), optionally scoped to a single session label. The Stats
  panel renders a **Daily goal** row with the target, the minutes focused so far
  today, a percentage, and a `role="progressbar"` bar; once the target is met the
  row switches to a clear, non-intrusive **"Daily goal reached"** state and the
  app announces it once through the existing ARIA live region. The row is hidden
  until a daily goal is set, and the goal can be changed or cleared (a `0`/empty
  value, or the **Clear daily goal** control) from the settings form. Today's
  focused minutes are derived from the existing `focus-flow:history` log by the
  pure `dailyGoalProgress` helper, which sums only completed work entries whose
  `endedAt` falls on the current local calendar day. The goal itself lives only
  in `localStorage` under `focus-flow:daily-goal` (a `{ minutes, label? }` shape,
  clamped to `0..1440`), and the key is removed when the goal is `0`/empty so a
  default install leaves no trace. It is never uploaded.
- **PWA app badge for the daily goal:** when the app is installed and a daily
  goal is set, the home-screen / desktop badge shows **today's remaining focused
  minutes** and is cleared once the goal is reached or the goal is removed. The
  decision comes from the pure `badgeState` helper in `app/history.js`, and the
  DOM layer performs the on-device `navigator.setAppBadge` /
  `navigator.clearAppBadge` calls **behind a feature check**, so a browser
  without the API is a no-op and never throws. This is a pure, on-device call:
  there is **no new `localStorage` key, no network request, and no third-party
  dependency**, and the badge is derived only from the already-local
  `focus-flow:history` and `focus-flow:daily-goal` keys.
- **Per-label weekly goal breakdown in the Stats panel:** the **Weekly goal**
  row in the Stats panel now shows a compact, per-label breakdown of the current
  week's focused minutes, so a label-scoped goal (e.g. "5 hours on Thesis
  chapter 3") is visible at a glance without opening the separate Weekly review
  card. Each row shows the label, its focused minutes, and its share of the
  target (including an `(unlabelled)` row when unlabelled sessions exist), ranked
  by minutes descending then label ascending. The list respects the existing
  label filter, so a filtered Stats view shows only the matching label, and it is
  hidden when the week has no label rows. The breakdown is derived entirely from
  the already-stored `focus-flow:history` and `focus-flow:goal` keys through the
  existing pure `weeklyReview` helper in `app/history.js` — there is **no new
  `localStorage` key, no network request, and no new runtime dependency**. Every
  string (heading, accessible name, per-row stats, announcement) comes from the
  bundled `app/i18n.js` catalog, and the list is announced once through the
  existing ARIA live region when it first appears or the goal is reached.
- **Weekly goal pace projection in the Stats panel:** under the existing
  per-label weekly breakdown, the **Weekly goal** row adds a small, purely
  derived projection line that answers *"will I hit my weekly goal at this
  pace?"* without leaving the Stats panel. It shows the rounded **pace needed
  per remaining day of the week** (e.g. "≈ 45 min/day for 3 more days") plus a
  neutral **on-track / behind-pace** signal, and it hides itself when no weekly
  goal is set. `remainingMinutes` is `max(0, target − focusedMinutes)`,
  `remainingDays` counts the local calendar days left in the current week
  *including today* (computed with local calendar arithmetic, so DST transitions
  never desynchronise the count), and `perDayMinutes` is the rounded
  per-remaining-day requirement (`0` once the goal is met). It is derived from
  the already-stored `focus-flow:history` and `focus-flow:goal` keys through the
  new pure `goalPace` helper in `app/history.js` (built on the existing
  `weeklyReview` result and reusing `weekWindow` / `normalizeWeekStart`), so
  there is **no new `localStorage` key, no network request, and no new runtime
  dependency**. It respects the active label filter (a filtered Stats view shows
  the projection for the matching label) and the user's *Week starts on*
  preference, every string comes from the bundled `app/i18n.js` catalog, and it
  is announced once through the existing ARIA live region when it first appears
  or when the goal is reached.
- **Weekly focus trend sparkline in the Stats panel:** the Stats panel shows a
  compact **Focus trend** line chart covering the **last 8 weeks** (including the
  current, partial week), with one point per week, so a user can answer *"is my
  focus trending up or down over the last few weeks?"* without leaving the app.
  Each point is the total focused minutes for that week, computed with the user's
  existing **Week starts on** preference and the same local-calendar arithmetic
  already used by `weeklyReview` (so daylight-saving transitions never shift,
  drop, or duplicate a week bucket). The sparkline respects the active **label
  filter** — a filtered Stats view shows the trend for that label only — and
  applies the **label aliases** map exactly as `weeklyReview` does. A short
  caption states the direction (**Trending up**, **Steady**, or **Trending
  down**) — computed by comparing the newest week with the week before it — plus
  the numeric min–max range, and the whole chart is a single
  `role="img"` region with an accessible name and range so the shape is readable
  by screen readers. The caption announces itself through the existing ARIA live
  region when the sparkline first appears or its direction changes. It is derived
  entirely from the already-stored
  `focus-flow:history` key by the pure `weeklyTrend` helper in `app/history.js`;
  there is **no new `localStorage` key, no network request, no third-party
  dependency, and no new runtime asset**, and every string comes from the bundled
  `app/i18n.js` catalog.
- **Daily focus trend sparkline in the Stats panel:** the Stats panel shows a
  compact **Daily focus trend** line chart covering the **last 14 local calendar
  days** (today included), with one point per day of total focused minutes, so a
  user can answer *"is my daily focus trending up or down over the last two
  weeks?"* without leaving the app, complementing the weekly trend sparkline,
  heatmap, and share donut. Each point is that day's rounded total focused
  minutes, computed with the same local-calendar arithmetic already used by
  `weeklyTrend` / `focusHeatmap` (so daylight-saving transitions never shift,
  drop, or duplicate a day bucket). The sparkline respects the active **label
  filter** — a filtered Stats view shows only the matching days — and applies the
  **label aliases** map exactly as `weeklyReview` does. A short caption states
  the direction (**Trending up**, **Steady**, or **Trending down**) — computed by
  comparing the newest day with the previous day — plus the numeric min–max
  range, and the whole chart is a single `role="img"` region with a localised
  accessible name and range so the shape is readable by screen readers. The
  caption announces itself through the existing ARIA live region when the
  sparkline first appears or its direction changes, and a localised empty state
  is shown when the range has no sessions. It re-renders on language and
  label-filter changes and after each completed work phase. It is derived
  entirely from the already-stored `focus-flow:history` key by the pure
  `dailyTrend` helper in `app/history.js`; there is **no new `localStorage` key,
  no network request, no third-party dependency, and no new runtime asset**, and
  every string comes from the bundled `app/i18n.js` catalog.
- **Focus heatmap in the Stats panel:** the Stats panel shows a compact **Focus
  heatmap** — a small grid with one cell per **local calendar day** over the
  trailing **12 weeks** (including the current, partial week), shaded from level
  `0` (no focused minutes) to level `4` (the user's current best day in the
  range). Each cell is shaded by that day's total focused minutes relative to
  the best day, so the shape of the user's recent consistency — *"am I building
  a habit?"* — is visible at a glance rather than only today or this week. The
  heatmap respects the active **label filter** (a filtered Stats view shows only
  the matching days) and applies the **label aliases** map exactly as
  `weeklyReview` does, and it follows the same **Week starts on** preference as
  the week-scoped views. The whole grid is a single `role="img"` region with a
  localised accessible name and a min–max focused-minutes-per-day caption; every
  day cell carries a localised `{weekday} {month} {day}: {minutes} min`
  `title`/`aria-label`, a short localised **Less … More** legend explains the
  shading, and an empty state is shown when there are no sessions yet. It
  re-renders on language, label-filter, and week-start changes and after each
  completed work phase, and it announces itself once through the existing ARIA
  live region when it first appears or its range changes. It is derived entirely
  from the already-stored `focus-flow:history` key by the pure `focusHeatmap`
  helper in `app/history.js` (using the same local-calendar arithmetic as
  `weekWindow` / `weeklyTrend`, so daylight-saving transitions never shift,
  drop, or duplicate a day bucket); there is **no new `localStorage` key, no
  network request, no third-party dependency, and no new runtime asset**, and
  every string comes from the bundled `app/i18n.js` catalog.
- **Focus share donut in the Stats panel:** the Stats panel shows a compact
  **Focus share** donut that answers *"where did my focused time go this week?"*
  at a glance. It renders one ring segment per session label seen in the current
  week (plus the `(unlabelled)` bucket when unlabelled sessions exist), ranked by
  minutes descending then label ascending and sized by each label's share of the
  week's total focused minutes. The ring is a single `role="img"` region with a
  localised accessible name and a total-minutes/label-count caption, and every
  segment carries a localised `{label}: {minutes} · {percent}%`
  `title`/`aria-label`, so the distribution is readable by screen readers. It
  respects the active **label filter** and applies the **label aliases** map
  exactly as `weeklyReview` does, and an empty state is shown before the first
  session of the week. It re-renders on language, label-filter, and week-start
  changes and after each completed work phase, and it announces itself once
  through the existing ARIA live region when it first appears or its slices
  change. It is derived entirely from the already-stored `focus-flow:history`
  key by the pure `labelShare` helper in `app/history.js` (which consumes the
  `weeklyReview` result, so the label filter, alias map, and week window are not
  duplicated); there is **no new `localStorage` key, no network request, no
  third-party dependency, and no new runtime asset**, and every string comes from
  the bundled `app/i18n.js` catalog.
- **30-day focus summary in the Stats panel:** a compact, purely derived block
  answers *"how much have I focused in total, and how does the last 30 days
  compare to my all-time average?"* without leaving the app. It shows the total
  focused minutes and completed work sessions over the trailing **30 local
  calendar days** (today included), the same totals for **all time** (the whole
  retained log), and a short, neutral comparison line relating the 30-day daily
  average to the all-time daily average (with a small tolerance so tiny
  fluctuations do not flip the label) so the user can see whether recent focus is
  above or below their long-run baseline. The window day set and the all-time day
  count use the same local-calendar arithmetic as `dailyTrend` / `weeklyTrend`
  (so a daylight-saving transition never shifts, drops, or duplicates a day), and
  the block respects the active **label filter** and the **label aliases** map
  exactly as the other derived views do. The empty state is shown when the log
  has no entries, it re-renders on language, label-filter changes, and after each
  completed work phase, and it is announced once through the existing ARIA live
  region when it first appears or its trend value changes. It is derived entirely
  from the already-stored `focus-flow:history` key (and, for the label filter and
  aliases, the existing `focus-flow:session-tags` map) by the pure
  `focusSummary` helper in `app/history.js`; there is **no new `localStorage`
  key, no network request, no third-party dependency, and no new runtime asset**,
  and every string comes from the bundled `app/i18n.js` catalog.
- **Per-label daily goal breakdown in the Stats panel:** the **Daily goal** row
  in the Stats panel also shows a compact, per-label breakdown of *today's*
  focused minutes, so a label-scoped daily goal (e.g. "50 minutes on Thesis
  chapter 3") is visible at a glance. Each row shows the label, its focused
  minutes, and its share of the target (including an `(unlabelled)` row when
  unlabelled sessions exist), ranked by minutes descending then label ascending.
  The list respects the existing label filter, so a filtered Stats view shows
  only the matching label, and it is hidden when today has no label rows. The
  breakdown is derived entirely from the already-stored `focus-flow:history` and
  `focus-flow:daily-goal` keys through the pure `dailyReview` helper in
  `app/history.js` — there is **no new `localStorage` key, no network request,
  and no new runtime dependency**. Every string comes from the bundled
  `app/i18n.js` catalog, and the list is announced once through the existing
  ARIA live region when it first appears.
- **Daily goal pace projection in the Stats panel:** under the existing
  per-label daily breakdown, the **Daily goal** row adds a small, purely derived
  projection line that answers *"will I hit my daily goal at this pace?"*
  without leaving the Stats panel. It shows the rounded **pace needed per
  remaining hour of the day** (e.g. "≈ 12 min/hour for 4 more hours") plus a
  neutral **on-track / behind-pace** signal, and it hides itself when no daily
  goal is set or the goal is already reached. `remainingMinutes` is
  `max(0, target − focusedMinutes)`, `remainingHours` counts the whole local
  hours left in the current local calendar day *including the current hour*
  (derived from the local hour-of-day, so a 23h/25h daylight-saving day still
  yields a sane count), and `perHourMinutes` is the rounded per-remaining-hour
  requirement (`0` once the goal is met). It is derived from the already-stored
  `focus-flow:history` and `focus-flow:daily-goal` keys through the new pure
  `dailyGoalPace` helper in `app/history.js` (built on the existing
  `dailyReview` result and reusing the local calendar arithmetic already used by
  `dailyGoalProgress`), so there is **no new `localStorage` key, no network
  request, and no new runtime dependency**. It respects the active label filter
  (a filtered Stats view shows the projection for the matching label) and the
  label aliases map exactly as `dailyReview` does, every string comes from the
  bundled `app/i18n.js` catalog, and it is announced once through the existing
  ARIA live region when it first appears or when the goal is reached.
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
- **Optional ambient sound:** an off-by-default background layer that loops
  during work phases and, when breaks are set to auto-start, keeps playing
  through them. The user picks between **brown noise**, **pink noise**, and
  **soft rain**, or keeps the default **Off**, and sets a volume between `0`
  and `1`. Every sound is **synthesised in the browser** from a seeded PRNG with
  the Web Audio API (a pure `ambient.js` module with no DOM access), so the app
  ships **no audio files, makes no network request, and adds no third-party
  asset**; the choice and volume are stored only in `localStorage`. Playback
  follows the timer — it starts with a work phase and is silenced whenever the
  timer is paused or reset — and coordinates are chosen so the loop only starts
  on a genuine user gesture.
- **Internationalisation (i18n):** every user-facing string is delivered from a
  tiny, bundled message catalog (`app/i18n.js`), and a **Language** switcher in
  the settings card renders the app in **English**, **German**, or **Spanish**.
  The pure catalog module maps plain data to plain data — no DOM, no network,
  no third-party library — and exports `SUPPORTED_LOCALES`, `LOCALE_LABELS`,
  `DEFAULT_LOCALE`, `MESSAGES`, `normalizeLocale`, `translate`,
  `createTranslator`, and `LOCALE_STORAGE_SHAPE_VERSION`. Changing the language
  applies immediately, re-renders every visible string (including the Stats,
  goal, weekly-review, and streak text), and is announced once through the
  existing ARIA live region. The choice is stored only on the device under
  `focus-flow:locale`, and the key is removed when the default locale is
  selected so a default install leaves no trace. Unknown or malformed stored
  values fall back to `DEFAULT_LOCALE` (`en`), a message missing from a locale
  falls back to English and then to its own key, and missing `{name}`
  placeholders are left in place instead of throwing.
- **Localised dates, numbers, and durations:** the same bundled catalog also
  carries the locale data for *derived* values, so weekday and month names,
  plural forms, and number grouping are localised rather than hard-coded in
  English. `app/i18n.js` exports a frozen `LOCALE_DATA` map (short and long
  weekday and month names, decimal and group separators, and a pure plural
  selector) plus the pure helpers `formatNumber`, `formatWeekday`,
  `formatMonth`, `formatDuration`, and `pluralise`. The DOM layer routes the
  per-day Stats bars, the **Recent sessions** timestamps, the streak text, and
  the weekly-review label stats through these helpers, so a user on `de` or `es`
  sees their own weekday and month names, decimal commas, thousands separators,
  and plural forms. This adds **no `Intl` dependency, no new `localStorage` key,
  no network request, and no third-party library** — the data ships in the same
  file as the message catalog.
- **User-selectable first day of week:** a **Week starts on** control in the
  settings card lets the user choose whether the week begins on **Monday**
  (default) or **Sunday**. The choice is rendered through the existing bundled
  `app/i18n.js` catalog (no new dependency and no network request), and flows
  through every week-scoped surface — the Stats **Weekly goal** row, the
  **Weekly review** panel, and its per-label breakdown, plus the streak
  day-adjacency logic. Changing it re-renders the Stats and Weekly review panels
  immediately and is announced once through the existing ARIA live region. It is
  stored only on the device under `focus-flow:week-start` (`0` = Sunday,
  `1` = Monday), and the key is removed when the default Monday is selected so a
  default install leaves no trace. `normalizeWeekStart` in `app/history.js`
  coerces arbitrary stored input into `0` or `1` and never throws.
- **Weekly review CSV export:** the Weekly review panel has an **Export CSV**
  button that saves the current week's review as a
  `focus-flow-week-<YYYY-MM-DD>.csv` file (the date is the week start). The file
  contains a header row, one row per session label (label, sessions, minutes,
  share of the target) plus a totals row, and it is produced entirely by the
  pure `weeklyReviewCsv` helper in `app/history.js` and handed to the browser as
  a `Blob` object URL. Fields containing `,`, `"`, or a newline are quoted and
  internal quotes doubled per RFC 4180. The button is disabled until the week
  has at least one label row. The export reads only the existing
  `focus-flow:history` and `focus-flow:goal` keys through `weeklyReview`, adds
  **no new `localStorage` key, no network request, and no new runtime
  dependency**, so nothing leaves the device.
- **Backup & restore:** the Settings card has a **Backup & restore** group. An
  **Export backup** button writes a single JSON file
  (`focus-flow-backup-<YYYY-MM-DD>.json`) containing the settings, the session
  history (with labels), the weekly goal, the daily goal, the ambient choice,
  the locale, the week-start preference, and the label aliases; a **Restore
  backup** button reads a
  file the user picks, validates and normalises it through the existing pure
  helpers, and writes it back to `localStorage`. The file is produced by the
  pure `exportBackup` / `backupToJson` helpers in `app/history.js` and handed to
  the browser as a `Blob` object URL, exactly like the weekly-review CSV export;
  restore reads the file with the browser's `FileReader` and applies it locally.
  A malformed or truncated file shows a non-destructive inline error, is
  announced through the ARIA live region, and leaves existing data untouched.
  The capability stays inside the product's invariants: it adds **no new
  `localStorage` key**, makes **no network request**, and adds **no third-party
  dependency**, so the data never leaves the device.
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
  - `ambient.js` — the pure ambient-sound helpers (`AMBIENT_TYPES`,
    `AMBIENT_LABELS`, `DEFAULT_AMBIENT`, `normalizeAmbient`,
    `createNoiseBuffer`, `shouldPlay`) with no DOM access. `createNoiseBuffer`
    synthesises brown, pink, or filtered-rain noise from a deterministic seeded
    PRNG, and `shouldPlay` decides whether the layer is active for a timer
    phase.
  - `history.js` — the pure session-history helpers (`recordSession`,
    `pruneHistory`, `summarise`, `labelSummary`, `recentSessions`,
    `recentLabels`, `normalizeGoal`, `weekWindow`, `goalProgress`,
    `normalizeDailyGoal`, `dailyGoalProgress`, `dailyReview`, `dailyGoalPace`,
    `badgeState`,
    `weeklyReview`, `goalPace`, `weeklyTrend`, `labelShare`, `focusSummary`,
    `streaks`, `normalizeWeekStart`, `normalizeSessionTags`, `applyAliases`,
    `weeklyReviewCsv`, `exportBackup`, `backupToJson`, `parseBackup`,
    `backupFileName`, `HISTORY_VERSION`, `GOAL_STORAGE_SHAPE_VERSION`,
    `DAILY_GOAL_STORAGE_SHAPE_VERSION`, `WEEK_START_OPTIONS`,
    `WEEK_START_STORAGE_SHAPE_VERSION`, `SESSION_TAGS_MAX_ENTRIES`,
    `SESSION_TAGS_MAX_ALIAS_LENGTH`, `SESSION_TAGS_STORAGE_SHAPE_VERSION`,
    `BACKUP_FORMAT_VERSION`, `BACKUP_KEYS`, `TREND_WEEKS`, `SUMMARY_DAYS`,
    `SUMMARY_TREND_TOLERANCE_MINUTES`, `SUMMARY_TREND_TOLERANCE_RATIO`) with no
    DOM access.
    `recentLabels` returns the newest distinct labels from the log (trimmed,
    non-empty, case-insensitively de-duplicated, newest first by `endedAt`,
    capped at a requested `limit`) for the session-label autocomplete, without
    touching the DOM, storage, or the network.
    `normalizeSessionTags` coerces arbitrary stored input into the canonical
    `{ label: alias }` display map and `applyAliases` resolves a stored label
    through it; the derived views accept an optional `tags` map so they can
    return aliased labels and match aliased filters without rewriting history.
    `dailyGoalProgress` measures the current local calendar day against the
    optional daily goal and returns `{ targetMinutes, focusedMinutes,
    remainingMinutes, percent, reached, dayStart }`, and `normalizeDailyGoal`
    clamps arbitrary stored input to a `{ minutes, label? }` shape in
    `0..1440`.
    `dailyReview` adds today's per-label breakdown on top of the same
    `{ dayStart, targetMinutes, focusedMinutes, remainingMinutes, percent,
    reached, scoped, labels, perLabel }` shape as `weeklyReview`, and
    `badgeState` turns a daily goal plus a `dailyReview` result into the
    on-device app-badge decision (the remaining focused minutes, or `null`) so
    the DOM layer owns the feature-detected badge calls.
    `normalizeWeekStart` coerces arbitrary stored input into the
    supported first day of week (`0` = Sunday, `1` = Monday), and
    `WEEK_START_OPTIONS` pairs each value with its catalog label key.
    `weeklyReview` returns the current week's goal versus per-label breakdown
    (`{ weekStart, targetMinutes, focusedMinutes, remainingMinutes, percent,
    reached, scoped, labels, perLabel }`), `weeklyReviewCsv` serialises that
    result to a deterministic RFC 4180 CSV string (header, one row per label,
    totals row) without touching the DOM, storage, or the network, and `streaks`
    returns the derived consistency view (`{ current, longest, todayCount,
    todayMinutes, lastActiveDay }`).
    `goalPace` turns a `weeklyReview` result into the forward-looking weekly
    goal projection (`{ remainingMinutes, remainingDays, perDayMinutes,
    onTrack }`), counting the remaining local calendar days (including today)
    with calendar arithmetic and reusing `weekWindow` / `normalizeWeekStart`, and
    returns `null` when no goal is set. It reads no storage of its own, makes no
    network request, and never throws on malformed input.
    `dailyGoalPace` is its day-scale companion: it turns a `dailyReview` result
    into the daily goal projection (`{ remainingMinutes, remainingHours,
    perHourMinutes, onTrack, reached }`), counting the whole local hours left in
    the current local calendar day (including the current hour) from the local
    hour-of-day, and likewise returns `null` when no goal is set, reads no
    storage of its own, makes no network request, and never throws on malformed
    input.
    `weeklyTrend` derives the **weekly focus trend** sparkline from the same
    log (`{ weeks, points, min, max, direction, empty }`), one
    `{ weekStart, minutes }` point per week over the trailing `TREND_WEEKS`
    weeks (the current, partial week included), computed with the same
    calendar arithmetic and the same `normalizeWeekStart` / `applyAliases`
    handling as `weeklyReview`, so it too reads no storage, makes no network
    request, and never throws on malformed input.
    `dailyTrend` derives the **daily focus trend** sparkline from the same log
    (`{ points, direction, min, max, empty }`), one `{ date, minutes }` point
    per local calendar day over the trailing `DAILY_TREND_DAYS` days (today
    included), computed with the same calendar arithmetic and the same label /
    `applyAliases` handling as `weeklyTrend`, so it likewise reads no storage,
    makes no network request, and never throws on malformed input.
    `labelShare` turns a `weeklyReview` result into the **focus share** donut
    data (`{ total, slices, empty }`), one `{ label, minutes, percent }`
    segment per label ranked by minutes descending then label ascending, reading
    the already-computed review only (so the label filter and alias map are
    already applied) and never touching the DOM, storage, or the network.
    `focusSummary` derives the **30-day summary** from the same log
    (`{ window, allTime, trend }`), each side `{ sessions, minutes, days,
    perDayMinutes }` for the trailing `SUMMARY_DAYS`-day window and the whole
    retained log, with `trend` (`"up"` / `"steady"` / `"down"`) comparing the two
    daily averages within `SUMMARY_TREND_TOLERANCE_MINUTES` /
    `SUMMARY_TREND_TOLERANCE_RATIO`. Its window day set and all-time day count
    use local-calendar arithmetic and the same label / `applyAliases` handling as
    the other derived views, so it too reads no storage, makes no network
    request, and never throws on malformed input.
    `exportBackup` / `backupToJson` serialise already-read storage values to a
    deterministic `{ version, exportedAt, data }` JSON envelope and
    `parseBackup` validates and normalises a backup string back through the same
    pure helpers (returning `null` for anything unusable, and rejecting a
    `version` newer than `BACKUP_FORMAT_VERSION`), while `backupFileName`
    derives the `focus-flow-backup-<YYYY-MM-DD>.json` download name.
  - `i18n.js` — the pure, bundled message catalog (`SUPPORTED_LOCALES`,
    `LOCALE_LABELS`, `DEFAULT_LOCALE`, `MESSAGES`, `normalizeLocale`,
    `translate`, `createTranslator`, `LOCALE_STORAGE_SHAPE_VERSION`) plus the
    frozen `LOCALE_DATA` map (weekday and month names, decimal/group separators,
    and a pure plural selector) and the pure helpers `formatNumber`,
    `formatWeekday`, `formatMonth`, `formatDuration`, and `pluralise`, all with
    no DOM access and no third-party import. `normalizeLocale` coerces arbitrary
    stored input into a supported locale id, `translate` falls back to the
    default locale and then to the key, and every catalog string and every piece
    of locale data ships in the file so the app stays offline.
  - `main.js` — the DOM layer, the `registerServiceWorker()` helper, and the
    only place that applies translations to the shell and the dynamic strings.
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
| `focus-flow:daily-goal` | `{ minutes, label? }` | Optional **daily focus goal**. `minutes` is an integer clamped to `0..1440` (a full day; `0` means "no goal") and rounded to whole minutes, and `label` is an optional trimmed string of at most 40 characters that scopes the goal to a single session label. The goal is stored **only in `localStorage`** and is never uploaded; `DAILY_GOAL_STORAGE_SHAPE_VERSION` in `app/history.js` documents the shape version, and `normalizeDailyGoal` coerces a number, an object, a numeric string, `null`, or garbage without throwing. The key is removed when the goal is `0`/empty so a default install leaves no trace. |
| `focus-flow:ambient` | `{ type, volume }` | Optional **ambient sound** setting. `type` is one of `"off"`, `"brown"`, `"pink"`, or `"rain"`, and `volume` is a number clamped to `0..1`. The key is **removed** when `type` is `"off"`; `normalizeAmbient` in `app/ambient.js` coerces arbitrary stored input and never throws. Nothing is uploaded and no audio file is stored — the sound is synthesised in the browser. |
| `focus-flow:locale` | locale id string (`"en"` \| `"de"` \| `"es"`) | Optional **language** preference. The stored value is the canonical id from `SUPPORTED_LOCALES`; `normalizeLocale` in `app/i18n.js` coerces arbitrary stored input (a string, a `{ locale }` object, or anything else) into a supported id, falling back to `DEFAULT_LOCALE` (`"en"`) and never throwing. The key is **removed** when the locale is the default so a default install leaves no trace, matching the ambient-sound behaviour. `LOCALE_STORAGE_SHAPE_VERSION` documents the shape version. Together with `focus-flow:week-start` this is one of the only added storage keys, and both are removed when they hold a default value. |
| `focus-flow:week-start` | `0` \| `1` | Optional **first day of the week** preference: `0` = Sunday, `1` = Monday (default `1`). Stored as a bare integer; `normalizeWeekStart` in `app/history.js` coerces arbitrary stored input (a number, a numeric string, a `{ weekStartsOn }` object, `null`, or anything else) into `0` or `1`, falling back to `DEFAULT_WEEK_START` and never throwing. The key is **removed** when the default Monday is selected so a default install leaves no trace, matching the ambient-sound and locale behaviour. `WEEK_START_STORAGE_SHAPE_VERSION` documents the shape version. |
| `focus-flow:session-tags` | `{ [canonicalLabel]: aliasLabel }` | Optional **label aliases**. Each key is a stored session label and each value the label to *display* in its place; both are trimmed, keys are capped to 40 characters and aliases to `SESSION_TAGS_MAX_ALIAS_LENGTH`, keys that differ only by case are merged, and the map is capped at `SESSION_TAGS_MAX_ENTRIES`. `normalizeSessionTags` in `app/history.js` coerces an object, an array of `{ from, to }` pairs, `null`, or anything else into the canonical map without throwing; `applyAliases` resolves a stored label through it. The key is **removed** when the map is empty so a default install leaves no trace, and the map is included in the local backup. `SESSION_TAGS_STORAGE_SHAPE_VERSION` documents the shape version. |

The **Weekly review** panel is derived, not stored: it reads only the existing
`focus-flow:history` and `focus-flow:goal` keys through the pure `weeklyReview`
helper and adds no new `localStorage` key and no network request.

The **Daily goal** row is derived the same way: the DOM layer renders it from
the pure `dailyGoalProgress` helper, which reads only the existing
`focus-flow:history` log (and, as its target, the optional
`focus-flow:daily-goal` key). The helper adds no storage access of its own, makes
no network request, and never mutates the log. It measures only the current local
calendar day — the week answers "am I on pace", the day answers "have I done
enough today".

The **per-label daily goal breakdown** in the Stats panel is derived the same
way: the DOM layer renders `dailyReview`'s `perLabel` rows (plus the derived
`unlabelled` bucket) inside the existing **Daily goal** row, so it reads only
`focus-flow:history` and `focus-flow:daily-goal`, adds **no new `localStorage`
key, no network request, and no third-party dependency**, and keeps the app fully
offline.

The **daily goal pace projection** is derived the same way: the pure
`dailyGoalPace` helper turns a `dailyReview` result into the remaining focused
minutes, the whole local hours left in the current local calendar day (the
current hour included), the rounded per-hour requirement, and an on-track
signal, and the DOM layer renders it as a single localised line under the
**Daily goal** row's per-label breakdown (hiding it once the goal is met). It
reads only `focus-flow:history` and `focus-flow:daily-goal`, adds **no new
`localStorage` key, no network request, and no third-party dependency**, and
keeps the app fully offline.

The **PWA app badge** is derived the same way and stays entirely on the device:
the pure `badgeState` helper turns the daily goal and the current `dailyReview`
result into today's remaining focused minutes (or `null` when the goal is unset
or reached), and the DOM layer performs the feature-detected, on-device platform
badge call behind a guard, so it adds **no new `localStorage` key, no network
request, and no third-party dependency**, and unsupported browsers are unaffected.

The **per-label weekly goal breakdown** in the Stats panel is derived the same
way: the DOM layer renders `weeklyReview`'s `perLabel` rows (plus the derived
`unlabelled` bucket) inside the existing **Weekly goal** row, so it reads only
`focus-flow:history` and `focus-flow:goal`, adds **no new `localStorage` key, no
network request, and no third-party dependency**, and keeps the app fully
offline.

The **weekly goal pace projection** is derived the same way: the pure `goalPace`
helper turns a `weeklyReview` result into the remaining focused minutes, the
number of remaining local calendar days (including today), the rounded per-day
requirement, and an on-track signal, and the DOM layer renders it as a single
localised line under the **Weekly goal** row's per-label breakdown. It reads only
`focus-flow:history` and `focus-flow:goal`, adds **no new `localStorage` key, no
network request, and no third-party dependency**, and keeps the app fully
offline.

The **weekly focus trend sparkline** is derived the same way: the pure
`weeklyTrend` helper turns `focus-flow:history` into one `{ weekStart, minutes }`
point per week (`weekStart` as a `YYYY-MM-DD` calendar key, plus the `min`/`max`
range, a `direction` that compares the newest week with the week before it, and
an `empty` flag), and the DOM layer draws it as a single inline-SVG `role="img"`
chart with a direction + range caption. It respects the active label filter and
the **Week starts on** preference and reads only `focus-flow:history`, so it adds
**no new `localStorage` key, no network request, and no third-party dependency**,
and keeps the app fully offline.

The **daily focus trend sparkline** is derived the same way: the pure
`dailyTrend` helper turns `focus-flow:history` into one `{ date, minutes }`
point per local calendar day over the trailing `DAILY_TREND_DAYS` days (today
included, `date` as a `YYYY-MM-DD` calendar key, plus the `min`/`max` range, a
`direction` that compares the newest day with the previous day, and an `empty`
flag), and the DOM layer draws it as a single inline-SVG `role="img"` chart with
a direction + range caption. It respects the active label filter and the alias
map, uses the same local-calendar arithmetic as `weeklyTrend` / `focusHeatmap`
so daylight-saving transitions never shift, drop, or duplicate a day bucket, and
reads only `focus-flow:history`, so it adds **no new `localStorage` key, no
network request, and no third-party dependency**, and keeps the app fully
offline.

The **focus heatmap** is derived the same way: the pure `focusHeatmap` helper
turns `focus-flow:history` into one `{ date, minutes, sessions, level }` bucket
per local calendar day for the trailing `HEATMAP_WEEKS` weeks (zero-filled
`YYYY-MM-DD` days, a `0..4` `level` relative to the `maxMinutes` best day, and an
`empty` flag), and the DOM layer draws it as a single `role="img"` grid with a
min–max caption, per-cell labels, and a `Less … More` legend. It respects the
active label filter and the **Week starts on** preference and reads only
`focus-flow:history`, so it adds **no new `localStorage` key, no network request,
and no third-party dependency**, and keeps the app fully offline.

The **focus share donut** is derived the same way: the pure `labelShare` helper
turns the already-computed `weeklyReview` result into `{ total, slices, empty }`,
one `{ label, minutes, percent }` segment per label ranked by minutes descending
then label ascending, and the DOM layer draws it as a single `role="img"` donut
with a total caption and per-segment `title`/`aria-label`. Because it consumes
the review result, the active label filter, the label aliases, and the **Week
starts on** window are already applied; it reads only `focus-flow:history`, so it
adds **no new `localStorage` key, no network request, and no third-party
dependency**, and keeps the app fully offline.

The **30-day focus summary** is derived the same way: the pure `focusSummary`
helper turns `focus-flow:history` into `{ window, allTime, trend }`, where each
scope carries `{ sessions, minutes, days, perDayMinutes }` for the trailing
`SUMMARY_DAYS`-day window and the whole retained log, and `trend` compares the
two daily averages. The window day set and the all-time day count use the same
local-calendar arithmetic as `dailyTrend` / `weeklyTrend`, so daylight-saving
transitions never shift, drop, or duplicate a day, and the block respects the
active label filter and the label aliases map exactly as the other derived views
do. The DOM layer renders it as a compact block with a localised heading,
accessible name, the two totals lines, a comparison line, and an empty state, and
announces it once through the existing ARIA live region when it first appears or
its trend value changes. It reads only `focus-flow:history` (plus the existing
label filter and `focus-flow:session-tags` map), so it adds **no new
`localStorage` key, no network request, no third-party dependency, and no new
runtime asset**, and keeps the app fully offline.

The **weekly review CSV export** is derived the same way and stays entirely on
the device: the pure `weeklyReviewCsv` helper turns the `weeklyReview` result
into a CSV string, and the DOM layer hands that string to the browser as a
`Blob` object URL for download. It reads no storage of its own, writes no new
key, and makes no network request.

The **focus streaks** and the daily reminder hint are derived the same way: the
pure `streaks` helper turns `focus-flow:history` into a current/longest streak
and today's totals, the reminder compares `todayCount` against the presence of a
`focus-flow:goal`, and nothing new is persisted or transmitted.

The **session-label autocomplete** is derived the same way: the pure
`recentLabels` helper reads only the existing `focus-flow:history` log to list
the newest distinct labels, and the DOM layer renders them as a listbox under
the session-label input. It adds **no new `localStorage` key, no network
request, and no third-party dependency**, so it, too, keeps every label on the
device.

The **label aliases** are read-time only: the DOM layer applies the
`focus-flow:session-tags` map through the pure `applyAliases` helper when it
renders the Stats chips and totals, the Recent sessions list, the autocomplete,
the goal scoping, the per-label goal breakdown, and the Weekly review, so the
stored `focus-flow:history` log is never rewritten. Several stored labels that
share one alias collapse into a single display row. The map is added to the
local backup alongside the other keys, is removed when empty, and is never
uploaded; reading it adds no network request and no third-party dependency.

The **internationalisation** catalog is bundled, not fetched: every string lives
in `app/i18n.js`, the service worker precaches `./i18n.js`, and the app makes no
network request at runtime. The same file also bundles the `LOCALE_DATA` used to
localise derived weekday and month names, plural forms, and number grouping, so
those values need no extra storage and no extra request either. Only the optional
`focus-flow:locale` preference is persisted, and it is removed when the default
locale is selected.

### Backup & restore

Focus Flow can save and reload its local state as a single JSON file, which is
**created and read entirely on the device**. The backup contains the settings,
the session history (with labels), the weekly goal, the daily goal, the ambient
choice, the locale, the week-start preference, and the label aliases; it
contains **no secrets**
and is handed to the browser as a `Blob` object URL, so it is never uploaded and
no network request is made. `exportBackup` / `backupToJson` in `app/history.js`
build the deterministic `{ version, exportedAt, data }` envelope, and
`backupFileName` names the download
`focus-flow-backup-<YYYY-MM-DD>.json`.

A restored file is **validated and normalised before it is written**: the DOM
layer reads it with the browser's `FileReader`, passes the text to the pure
`parseBackup` helper, and only then writes the canonical values back to
`localStorage` (removing any key whose normalised value is empty/default, so the
restore keeps the "a default install leaves no trace" rule). A file that is not
a usable backup — bad JSON, wrong types, a missing `data` envelope, or a
`version` newer than `BACKUP_FORMAT_VERSION` — is rejected with a
non-destructive inline error and an announcement through the live region, and
the existing data is never overwritten. The feature adds **no new `localStorage`
key**, makes **no network request**, and adds **no third-party dependency**.

## Next direction

- [x] **Focus streaks and reminders**, derived locally from the session history
  and building on the weekly goal and weekly review panels.
- [x] Optional **ambient sound** (brown noise / pink noise / soft rain) using
  the Web Audio API, generated entirely in the browser with no audio files.
- [x] **Internationalisation (i18n)** with a small bundled message catalog and a
  locale switcher.
- [x] **Localised date and number formatting** by extending the catalog's locale
  data to every derived label (weekday and month names, plural rules), building
  on the shipped i18n module.
- [x] **User-selectable first day of week**, letting the weekly goal and the
  weekly review start their week on Sunday or Monday, with the choice rendered
  through the same bundled catalog and stored only on the device as the next
  follow-up to localised formatting. Implemented: the **Week starts on**
  setting is announced once through the live region and stored under
  `focus-flow:week-start` (removed when the default Monday is selected).
- [x] **Weekly review CSV export**, the next step after the week-start
  preference: a pure `weeklyReviewCsv` helper in `app/history.js` serialises the
  `weeklyReview` result to an RFC 4180 CSV string, and the Weekly review panel
  downloads it as `focus-flow-week-<YYYY-MM-DD>.csv` through a `Blob` object
  URL. The export is local-only — it makes no network request, adds no
  `localStorage` key, and adds no new runtime dependency.
- [x] **Per-label weekly goal breakdown in the Stats panel**, the follow-up to
  the weekly review and CSV export that surfaces the same `weeklyReview`
  `perLabel` data inline in the Stats **Weekly goal** row. The DOM layer renders
  each label's focused minutes and share of the target (plus an `(unlabelled)`
  row when needed), routed through the bundled catalog and the shared
  `formatNumber` / `formatDuration` / `pluralise` helpers, and announces the
  breakdown once through the existing ARIA live region. It respects the active
  label filter, hides itself when the week has no label rows, reads only
  `focus-flow:history` and `focus-flow:goal`, adds no `localStorage` key, and
  makes no network request.
- [x] **Daily focus goal**, the day-scale companion to the weekly goal: a pure
  `dailyGoalProgress` helper in `app/history.js` sums completed work entries
  whose `endedAt` falls on the current local calendar day, with the same
  label / `UNLABELLED` matching rule as `goalProgress`. The Stats panel renders a
  hidden-by-default **Daily goal** row with the target, today's focused minutes,
  a percentage, and a `role="progressbar"` bar, and switches to a
  **"Daily goal reached"** state that is announced once through the existing ARIA
  live region. The goal is coerced by `normalizeDailyGoal`, stored only under
  `focus-flow:daily-goal` (`{ minutes, label? }`, clamped to `0..1440`), and the
  key is removed when the goal is `0`/empty. It adds no new runtime dependency,
  no network request, and no third-party asset.
- [x] **Local backup & restore**, the data-portability follow-up to the
  export-only CSV: the pure `exportBackup` / `backupToJson` / `parseBackup` /
  `backupFileName` helpers in `app/history.js` write the whole local state to a
  `focus-flow-backup-<YYYY-MM-DD>.json` file and read it back, and the Settings
  card gains **Export backup** and **Restore backup** controls. Restore
  validates and normalises through the existing pure helpers before writing, and
  a rejected file is announced and leaves the existing data untouched. The
  feature adds no new `localStorage` key, makes no network request, and adds no
  third-party dependency.
- [x] **Session-label autocomplete**, the typing-reduction follow-up to
  per-session labels: the pure `recentLabels` helper in `app/history.js`
  returns the newest distinct labels from the existing `focus-flow:history` log
  (trimmed, non-empty, case-insensitively de-duplicated, newest first by
  `endedAt`, capped at 8), and the DOM layer renders them as an accessible
  `<ul role="listbox">` under the session-label input. It supports
  `ArrowDown`/`ArrowUp` to move, `Enter`/`Tab` to accept, `Escape` to dismiss,
  and click/tap to choose, announces the accepted label once through the
  existing ARIA live region, keeps free text intact when no suggestion is
  chosen, and shows nothing on a fresh install. It adds **no new
  `localStorage` key, no network request, and no third-party dependency**.
- [x] **Label aliases (session tags)**, the display-cleanup follow-up to
  per-session labels: a device-only `{ label: alias }` map lets a user rename
  how a label is shown everywhere without rewriting the stored history. The pure
  `normalizeSessionTags` / `applyAliases` helpers in `app/history.js` coerce and
  read the map, the derived views accept an optional `tags` option to return
  aliased labels and match aliased filters, and the Settings card gains a
  **Label aliases** group that adds and removes rows and announces each change
  once through the existing ARIA live region. The map is stored only under
  `focus-flow:session-tags` (removed when empty), is included in the local
  backup, adds no network request and no third-party dependency, and shows
  nothing on a default install.
- [x] **Per-label daily goal breakdown**, the day-scale companion to the weekly
  breakdown: the pure `dailyReview` helper in `app/history.js` mirrors
  `weeklyReview` for the current local calendar day (with the same
  minutes-descending / label-ascending ranking and `(unlabelled)` bucket), and
  the Stats **Daily goal** row renders its rows inline. It respects the active
  label filter and the alias map, hides itself when today has no label rows,
  reads only `focus-flow:history` and `focus-flow:daily-goal`, and adds no
  `localStorage` key and no network request.
- [x] **PWA app badge for the daily goal**, the at-a-glance follow-up to the
  day-scale goal: the pure `badgeState` helper in `app/history.js` returns the
  remaining focused minutes (or `null` once the goal is reached or unset), and
  the DOM layer performs the feature-detected, on-device `setAppBadge` /
  `clearAppBadge` call and announces the new state once through the existing ARIA
  live region. It adds no new `localStorage` key, makes no network request, adds
  no third-party dependency, and leaves unsupported browsers untouched.
- [x] **Weekly goal pace projection**, the forward-looking follow-up to the
  weekly goal and its per-label breakdown: the pure `goalPace` helper in
  `app/history.js` turns a `weeklyReview` result into the rounded per-day pace
  needed for the remaining local calendar days (including today), the remaining
  minutes, and a neutral on-track / behind-pace signal, returning `null` when no
  goal is set. The Stats **Weekly goal** row renders a single localised line
  under its per-label breakdown and announces it once through the existing ARIA
  live region when it first appears or the goal is reached. It respects the
  active label filter and the **Week starts on** preference, reads only
  `focus-flow:history` and `focus-flow:goal`, and adds no `localStorage` key, no
  network request, and no third-party dependency.
- [x] **Daily goal pace projection**, the day-scale companion to the weekly pace
  projection: the pure `dailyGoalPace` helper in `app/history.js` turns a
  `dailyReview` result into the rounded per-hour pace needed for the whole local
  hours left in the current local calendar day (the current hour included), the
  remaining minutes, a `reached` flag, and a neutral on-track / behind-pace
  signal, returning `null` when no daily goal is set. The Stats **Daily goal**
  row renders a single localised line under its per-label breakdown, hides it
  once the goal is reached, and announces it once through the existing ARIA live
  region when it first appears or the goal is reached. It respects the active
  label filter and the alias map, reads only `focus-flow:history` and
  `focus-flow:daily-goal`, and adds no `localStorage` key, no network request,
  and no third-party dependency.
- [x] **Weekly focus trend sparkline**, the at-a-glance follow-up to the weekly
  review: the pure `weeklyTrend` helper in `app/history.js` returns one
  `{ weekStart, minutes }` point per week over the trailing `TREND_WEEKS`
  weeks (the current, partial week included, clamped to `1..26`), with
  `weekStart` as a `YYYY-MM-DD` calendar key, plus the `min`/`max` range, a
  `direction` that compares the newest week with the week before it (`"up"`,
  `"down"`, or `"flat"`), and an `empty`
  flag. The Stats panel draws it as a single inline-SVG `role="img"` sparkline
  with a direction + range caption, respects the active label filter and the
  **Week starts on** preference, applies the alias map, shows a localised empty
  state, and announces itself through the existing ARIA live region when it
  first appears or its direction changes. It
  reads only `focus-flow:history`, makes no network request, and adds no
  `localStorage` key and no third-party dependency.
- [x] **Focus heatmap**, the consistency-at-a-glance follow-up to the weekly
  trend: the pure `focusHeatmap` helper in `app/history.js` returns one
  `{ date, minutes, sessions, level }` bucket per local calendar day over the
  trailing `HEATMAP_WEEKS` weeks (the current, partial week included, clamped to
  `1..26`), zero-filled with a `0..4` `level` relative to the `maxMinutes` best
  day and an `empty` flag, using the same local-calendar arithmetic as
  `weekWindow` / `weeklyTrend` so daylight-saving transitions never shift, drop,
  or duplicate a bucket. The Stats panel draws it as a single `role="img"` grid
  with a min–max focused-minutes-per-day caption, a localised per-day
  `title`/`aria-label`, and a localised **Less … More** legend, respects the
  active label filter, the **Week starts on** preference, and the alias map,
  re-renders on language / label-filter / week-start changes and after each
  completed work phase, shows a localised empty state, and announces itself once
  through the existing ARIA live region when it first appears or its range
  changes. It reads only `focus-flow:history`, makes no network request, and
  adds no `localStorage` key and no third-party dependency.
- [x] **Daily focus trend sparkline**, the day-scale companion to the weekly
  trend: the pure `dailyTrend` helper in `app/history.js` returns one
  `{ date, minutes }` point per local calendar day over the trailing
  `DAILY_TREND_DAYS` days (today included, clamped to `1..90`), zero-filled with
  a `min`/`max` range, a `direction` that compares the newest day with the
  previous day (`"up"`, `"down"`, or `"flat"`), and an `empty` flag, using the
  same local-calendar arithmetic as `weeklyTrend` / `focusHeatmap` so
  daylight-saving transitions never shift, drop, or duplicate a day bucket. The
  Stats panel draws it as a single inline-SVG `role="img"` sparkline with a
  direction + range caption, respects the active label filter and the alias map,
  re-renders on language / label-filter changes and after each completed work
  phase, shows a localised empty state, and announces itself through the existing
  ARIA live region when it first appears or its direction changes. It reads only
  `focus-flow:history`, makes no network request, and adds no `localStorage` key
  and no third-party dependency.
- [x] **30-day focus summary**, the long-run baseline follow-up to the trend and
  heatmap views: the pure `focusSummary` helper in `app/history.js` returns
  `{ window, allTime, trend }`, with each scope carrying `{ sessions, minutes,
  days, perDayMinutes }` for the trailing `SUMMARY_DAYS`-day window and the whole
  retained log, and `trend` (`"up"` / `"steady"` / `"down"`) comparing the two
  daily averages within a small tolerance. The Stats panel renders a compact,
  purely derived block with a localised heading, accessible name, the two totals
  lines, a comparison line, and a localised empty state, respecting the active
  label filter and the alias map and using the same local-calendar arithmetic as
  `dailyTrend` / `weeklyTrend`, and announces it once through the existing ARIA
  live region when it first appears or its trend value changes. It reads only
  `focus-flow:history` (plus the existing label filter and
  `focus-flow:session-tags` map), makes no network request, and adds no
  `localStorage` key, no third-party dependency, and no new runtime asset.

## How the repository meets its own criteria

### Hard requirements (MUST)

| Requirement | How Focus Flow satisfies it |
| --- | --- |
| Web Deployable | Static SPA served from `app/`; installable PWA with a manifest and service worker that runs in any modern browser. |
| Originality | A no-account, offline, single-file focus timer with explicit privacy and k3s/GitOps packaging; not a copy of an existing product. |
| Expandable | Pure timer engine (`app/timer.js`) is decoupled from the DOM layer (`app/main.js`), so features slot in without rewrites. The pure `app/i18n.js` catalog lets new locales and messages be added as plain data. |
| Real User Value | Structures work/break cycles to improve focus and reduce context switching. |
| Clearly Defined Audience | Students, remote knowledge workers, and anyone needing structured cycles. |
| Standalone | No dependency on any other AI Product Factory application. |
| Autonomous Operation | No backend; nothing to administer after deployment, and the service worker keeps the app usable offline. |
| Kubernetes Compatible | `Dockerfile` + `helm/` chart with `Deployment`, `Service`, `Ingress`, probes, and resource limits. |
| Resource Efficient | Tiny nginx:alpine image, static files only, small CPU/RAM requests and limits in `helm/values.yaml`. |
| Security | No secrets, no runtime external calls, no telemetry, no user input leaves the browser; the service worker ignores cross-origin and non-GET requests; container runs as non-root. The ambient sound layer is synthesised in-browser with the Web Audio API, so it adds **no network request and no third-party asset**. The i18n catalog is bundled in `app/i18n.js`, so localisation adds **no network request and no third-party library**, and the only new storage is the optional locale preference. The user-selectable first day of week is rendered from that same bundled catalog, so it too adds **no network request and no third-party dependency** — the only new storage is the optional `focus-flow:week-start` preference. The daily focus goal is measured from the existing history by a pure helper and stored only under the optional `focus-flow:daily-goal` key, so it adds **no network request, no third-party dependency, and no upload**. The per-label daily goal breakdown is derived from that same history and daily-goal key by the pure `dailyReview` helper, and the PWA app badge is decided by the pure `badgeState` helper and pushed through a feature-detected, on-device platform call, so both add **no new `localStorage` key, no network request, no third-party dependency, and no upload**, and unsupported browsers throw nothing. The local backup/restore writes and reads a JSON file entirely on the device through pure helpers, so it adds **no new `localStorage` key, no network request, no third-party dependency, and no upload**. The session-label autocomplete is derived from the existing history key by the pure `recentLabels` helper, so it adds **no new `localStorage` key, no network request, no third-party dependency, and no upload**. The label aliases are coerced and read by the pure `normalizeSessionTags` / `applyAliases` helpers and stored only under the optional `focus-flow:session-tags` key (removed when empty), so they add **no network request, no third-party dependency, and no upload**. The weekly goal pace projection is derived from the existing history and goal keys by the pure `goalPace` helper, so it adds **no new `localStorage` key, no network request, no third-party dependency, and no upload**. The daily goal pace projection is derived from the same history and daily-goal keys by the pure `dailyGoalPace` helper, so it likewise adds **no new `localStorage` key, no network request, no third-party dependency, and no upload**. The focus heatmap is derived from the existing history key by the pure `focusHeatmap` helper, so it adds **no new `localStorage` key, no network request, no third-party dependency, and no upload**. |
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
| User Retention | Daily use pattern; persistent settings, session counts, and a 7-day focus-history panel that shows progress; optional per-session labels, a label filter, and a weekly review that ranks each label against the weekly goal let users see where their focus went, and the Stats **Weekly goal** row now carries an inline per-label breakdown so each label's contribution is visible at a glance and a derived pace projection line answers "will I hit my goal at this pace?"; a daily focus goal gives the same "have I done enough today" feedback at day scale, with a per-label daily breakdown in the Stats **Daily goal** row, a derived daily pace projection line that answers "will I hit today's goal at this pace?", and an on-device app badge that keeps today's remaining minutes visible from the home screen, and a derived current/longest focus streak and a gentle daily reminder hint encourage users to come back and keep the streak alive, and a derived focus heatmap makes recent day-to-day consistency visible at a glance, and a derived daily focus trend sparkline shows whether the last two weeks are trending up or down, plus one-tap install to the home screen or desktop. |
| Discoverability | Clear name, description, and docs; shareable as a URL. Ships English, German, and Spanish from a bundled catalog with an accessible language switcher, and the derived weekday/month names, plural forms, and number grouping come from that same bundled catalog. |
| Mobile Friendly | Responsive layout, touch-friendly controls, and an installable PWA that launches standalone. |
| Accessibility | Semantic landmarks, ARIA live region, keyboard shortcuts, focus states, contrast. The locale switcher and the **Week starts on** control are labelled `<select>`s with accessible names, every string (including live-region announcements) is routed through the catalog, derived weekday/month names and numbers are localised from the same bundled catalog, and `<html lang>` follows the active locale. The session-label autocomplete is a real `role="listbox"`/`role="option"` combobox that is fully operable by keyboard (`ArrowDown`/`ArrowUp` to move, `Enter`/`Tab` to accept, `Escape` to dismiss) with a visible active-option state. The focus heatmap is a single `role="img"` region with a localised accessible name and range caption, and every day cell exposes a localised `title`/`aria-label`. The daily focus trend is likewise a single `role="img"` region with a localised accessible name and range caption. |
| Minimal Dependencies | Zero runtime JS/CSS dependencies; the i18n catalog and its `LOCALE_DATA` (weekday/month names, separators, plural rules) are a dependency-free local module with no network request, no `Intl` dependency, and no third-party library. |
| Measurable Success | `/healthz` for reliability; the local session history, 7-day stats, optional label breakdown, the weekly focus goal, and the weekly review give users a visible, measurable view of their focus habit, including what each block of time was spent on and how close each label came to their weekly target; the Stats **Weekly goal** row shows that per-label goal share inline; a derived pace projection line under that breakdown makes the remaining per-day requirement measurable at a glance; the **Daily goal** row makes daily output directly measurable against a per-day target and shows today's per-label breakdown and a derived daily pace projection line that answers "will I hit today's goal at this pace?"; the derived current/longest focus streak and today's totals make consistency itself measurable; the derived focus heatmap makes day-to-day consistency over the trailing weeks visible and its best-day range measurable; the derived daily focus trend sparkline makes the last two weeks' direction and min–max range measurable at a glance; the derived 30-day focus summary makes the trailing-30-day totals and the recent-vs-all-time daily average measurable at a glance; and the on-device app badge surfaces today's remaining focused minutes at a glance from the home screen. |
| Reusability | Reuses the standard static-container + Helm deployment template. |
| Innovation Potential | The shipped ambient sound layer shows the in-browser synthesis approach can be extended to more generated soundscapes, and the shipped bundled catalog with bundled locale data shows how the product can add locales, weekday/month names, and plural rules without a build step, a backend, or a third-party dependency; a shipped user-selectable first day of week shows how further local conventions (a fiscal week start, custom week windows) can reuse the same catalogue-and-storage pattern. |

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
