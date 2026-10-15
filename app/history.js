/**
 * Focus Flow session history.
 *
 * Pure, dependency-free helpers for the local focus-session log. This module
 * has no access to the page, the storage layer, or the network: it only maps
 * plain data to plain data, so the DOM layer (main.js) owns all side effects
 * and the logic here can be reasoned about and tested on its own.
 *
 * A log entry is `{ endedAt, phase, durationSeconds, label? }`. Only completed
 * work phases are recorded; breaks are ignored. `endedAt` is an ISO string and
 * `label` is an optional trimmed string of at most `MAX_LABEL_LENGTH`
 * characters. Version 2 of the schema adds the optional `label` field; version
 * 1 entries (no `label`) stay valid and remain unlabelled.
 *
 * The module also owns the pure maths for the optional **weekly focus goal**: a
 * locally stored `{ minutes, label? }` target. `weekWindow` finds the current
 * week, `goalProgress` measures the logged focus time against the target,
 * `weeklyReview` adds a per-label breakdown of the same week, and
 * `normalizeGoal` coerces arbitrary stored input into the canonical shape.
 * `weeklyReviewCsv` serialises a `weeklyReview` result to an RFC 4180 CSV
 * string for the local, offline **weekly review export**. None of these touch
 * the DOM, the storage layer, or the network.
 */

export const HISTORY_VERSION = 2;
export const MAX_ENTRIES = 500;
export const DEFAULT_RETENTION_DAYS = 90;
export const MAX_LABEL_LENGTH = 40;
export const UNLABELLED = "(unlabelled)";

/** Shape version for the `focus-flow:goal` storage entry. Version 1 is the
 * initial `{ minutes, label? }` object; older or malformed values are coerced
 * by `normalizeGoal`. */
export const GOAL_STORAGE_SHAPE_VERSION = 1;

/** Lowest / highest meaningful weekly goal. A goal is minutes focused per
 * week; the ceiling is a full week (7 × 24 × 60). */
export const MIN_GOAL_MINUTES = 0;
export const MAX_GOAL_MINUTES = 7 * 24 * 60;

/** Default first day of the week (Monday), matching `Date#getDay` numbering
 * where Sunday is `0`. */
export const DEFAULT_WEEK_START = 1;

/** Shape version for the `focus-flow:week-start` storage entry. Version 1
 * stores the first day of the week as a bare integer (`0` = Sunday,
 * `1` = Monday); arbitrary input is coerced by `normalizeWeekStart`. */
export const WEEK_START_STORAGE_SHAPE_VERSION = 1;

/** The selectable first days of the week, in display order, each paired with
 * the catalog key for its label. The DOM layer renders these through the
 * bundled `app/i18n.js` catalog, so no label is hard-coded in English. */
export const WEEK_START_OPTIONS = Object.freeze([
  Object.freeze({ value: 1, labelKey: "settings.weekStartMonday" }),
  Object.freeze({ value: 0, labelKey: "settings.weekStartSunday" }),
]);

const DAY_MS = 24 * 60 * 60 * 1000;
const WORK_PHASE = "work";

function toTimestamp(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.length > 0) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function dateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function startOfDay(timestamp) {
  const date = new Date(timestamp);
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

/** Shift a `YYYY-MM-DD` calendar key by whole local days. Uses calendar
 * arithmetic rather than adding `DAY_MS` so DST transitions (23h/25h days)
 * never desynchronise the day keys. */
function shiftDayKey(dayKey, delta) {
  const [year, month, day] = dayKey.split("-").map(Number);
  return dateKey(new Date(year, month - 1, day + delta));
}

/** Normalise an optional label: trim it, drop it when empty, and cap its
 * length so a single entry can never bloat local storage. */
function normalizeLabel(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim().slice(0, MAX_LABEL_LENGTH);
}

/** Coerce an arbitrary value into a canonical work entry, or null if it is
 * not a usable completed-work record. */
function normalizeEntry(entry) {
  if (!entry || typeof entry !== "object") {
    return null;
  }
  if (entry.phase !== WORK_PHASE) {
    return null;
  }
  const duration = Number(entry.durationSeconds);
  if (!Number.isFinite(duration) || duration < 0) {
    return null;
  }
  const endedAt =
    entry.endedAt === undefined || entry.endedAt === null
      ? new Date().toISOString()
      : entry.endedAt;
  const timestamp = toTimestamp(endedAt);
  if (timestamp === null) {
    return null;
  }
  const normalized = {
    endedAt: new Date(timestamp).toISOString(),
    phase: WORK_PHASE,
    durationSeconds: Math.round(duration),
  };
  const label = normalizeLabel(entry.label);
  if (label.length > 0) {
    normalized.label = label;
  }
  return normalized;
}

/** Collect the normalised work entries inside the trailing `days`-day range
 * that ends today. Shared by `summarise` and `labelSummary` so the range rules
 * live in exactly one place. */
function collectWindow(history, { now, days }) {
  const spanDays = Math.max(1, Math.floor(days));
  const log = Array.isArray(history) ? history : [];
  const todayStart = startOfDay(now);
  const rangeStart = todayStart - (spanDays - 1) * DAY_MS;

  const entries = [];
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (
      timestamp === null ||
      timestamp < rangeStart ||
      timestamp >= todayStart + DAY_MS
    ) {
      continue;
    }
    entries.push({ ...normalized, timestamp });
  }
  return { spanDays, rangeStart, entries };
}

/**
 * Append a completed work entry to the log. Returns a new array; the input is
 * never mutated. Invalid entries and non-work phases are ignored, and the log
 * is capped at `MAX_ENTRIES` so local storage cannot grow unbounded.
 */
export function recordSession(history, entry) {
  const log = Array.isArray(history) ? history.slice() : [];
  const normalized = normalizeEntry(entry);
  if (!normalized) {
    return log;
  }
  log.push(normalized);
  return log.length > MAX_ENTRIES ? log.slice(log.length - MAX_ENTRIES) : log;
}

/**
 * Drop entries older than the retention period and enforce the entry cap.
 * Returns a new array. `now` and `retentionDays` are injectable for tests.
 */
export function pruneHistory(
  history,
  { now = Date.now(), retentionDays = DEFAULT_RETENTION_DAYS } = {},
) {
  const log = Array.isArray(history) ? history : [];
  const cutoff = now - Math.max(0, retentionDays) * DAY_MS;
  const kept = log.filter((entry) => {
    const timestamp = toTimestamp(entry && entry.endedAt);
    return timestamp !== null && timestamp >= cutoff;
  });
  return kept.length > MAX_ENTRIES ? kept.slice(kept.length - MAX_ENTRIES) : kept;
}

/**
 * Summarise completed work sessions over the trailing `days`-day period that
 * ends today. Returns `{ days, totalSessions, totalMinutes, perDay, empty }`
 * where `perDay` is a zero-filled list of `{ date, label, count, minutes }`
 * buckets in chronological order. `date` is the `YYYY-MM-DD` calendar key and
 * `label` mirrors it; the buckets no longer carry a language-specific weekday
 * name, so the DOM layer localises the weekday from `date` through the catalog.
 * When `label` is provided, only entries matching it are counted; pass
 * `UNLABELLED` to count entries without a label. Purely data in, data out.
 */
export function summarise(history, { now = Date.now(), days = 7, label } = {}) {
  const { spanDays, rangeStart, entries } = collectWindow(history, { now, days });
  const filter = label === undefined || label === null ? null : String(label);

  const buckets = new Map();
  for (let offset = 0; offset < spanDays; offset += 1) {
    const date = new Date(rangeStart + offset * DAY_MS);
    const key = dateKey(date);
    buckets.set(key, {
      date: key,
      label: key,
      count: 0,
      minutes: 0,
    });
  }

  let totalSessions = 0;
  let totalSeconds = 0;
  for (const entry of entries) {
    if (filter !== null && (entry.label || UNLABELLED) !== filter) {
      continue;
    }
    const bucket = buckets.get(dateKey(new Date(entry.timestamp)));
    if (!bucket) {
      continue;
    }
    bucket.count += 1;
    bucket.minutes += Math.round(entry.durationSeconds / 60);
    totalSessions += 1;
    totalSeconds += entry.durationSeconds;
  }

  return {
    days: spanDays,
    totalSessions,
    totalMinutes: Math.round(totalSeconds / 60),
    perDay: Array.from(buckets.values()),
    empty: totalSessions === 0,
  };
}

/**
 * Summarise labelled sessions over the trailing `days`-day period. Returns
 * `{ labels, totals }`:
 *
 * - `labels` is the sorted, de-duplicated list of labels present in the range.
 * - `totals` maps every label (plus an `UNLABELLED` bucket) to
 *   `{ sessions, minutes }`.
 *
 * The optional `labels` argument acts as an allow-list, so callers can ask for
 * a single label's totals. Without it every label in the range is returned.
 */
export function labelSummary(
  history,
  { now = Date.now(), days = 7, labels } = {},
) {
  const { entries } = collectWindow(history, { now, days });
  const allow =
    Array.isArray(labels) && labels.length > 0 ? new Set(labels) : null;

  const totals = new Map();
  let unlabelled = { sessions: 0, minutes: 0 };

  for (const entry of entries) {
    if (entry.label) {
      if (allow && !allow.has(entry.label)) {
        continue;
      }
      const bucket = totals.get(entry.label) || { sessions: 0, minutes: 0 };
      bucket.sessions += 1;
      bucket.minutes += Math.round(entry.durationSeconds / 60);
      totals.set(entry.label, bucket);
    } else {
      if (allow && !allow.has(UNLABELLED)) {
        continue;
      }
      unlabelled.sessions += 1;
      unlabelled.minutes += Math.round(entry.durationSeconds / 60);
    }
  }

  const result = {};
  const present = Array.from(totals.keys()).sort((a, b) => a.localeCompare(b));
  for (const key of present) {
    result[key] = totals.get(key);
  }
  result[UNLABELLED] = unlabelled;

  return { labels: present, totals: result };
}

/**
 * Return the newest `limit` normalised entries, newest first, each shaped as
 * `{ endedAt, label, durationSeconds }`. `label` is absent for unlabelled
 * entries so the caller can render its own placeholder.
 */
export function recentSessions(history, { limit = 5 } = {}) {
  const log = Array.isArray(history) ? history : [];
  const entries = [];
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (normalized) {
      entries.push(normalized);
    }
  }
  const max = Math.max(0, Math.floor(limit));
  return entries
    .map((entry) => ({ ...entry, _ts: toTimestamp(entry.endedAt) || 0 }))
    .sort((a, b) => b._ts - a._ts)
    .slice(0, max)
    .map(({ endedAt, label, durationSeconds }) => ({
      endedAt,
      label,
      durationSeconds,
    }));
}

/** Clamp an arbitrary value to the goal bounds, rounding to whole minutes. */
function clampGoalMinutes(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return MIN_GOAL_MINUTES;
  }
  return Math.min(
    MAX_GOAL_MINUTES,
    Math.max(MIN_GOAL_MINUTES, Math.round(parsed)),
  );
}

/**
 * Coerce arbitrary stored input into a canonical `{ minutes, label? }` goal.
 * `minutes` is clamped to `0..MAX_GOAL_MINUTES` (a full week) and rounded to a
 * whole number; `label` is trimmed to `MAX_LABEL_LENGTH` and dropped when it is
 * empty. Never throws and never mutates its input.
 */
export function normalizeGoal(raw) {
  let source;
  if (typeof raw === "number") {
    source = { minutes: raw };
  } else if (raw && typeof raw === "object") {
    source = raw;
  } else {
    source = {};
  }
  const goal = { minutes: clampGoalMinutes(source.minutes) };
  const label = normalizeLabel(source.label);
  if (label.length > 0) {
    goal.label = label;
  }
  return goal;
}

/**
 * Coerce arbitrary stored input into a supported first day of the week.
 *
 * Accepts a bare number (`0` = Sunday, `1` = Monday), a numeric string, a
 * `{ weekStartsOn }` object, or anything else. Values outside `{0, 1}` and
 * malformed input fall back to `DEFAULT_WEEK_START` (Monday), and this function
 * never throws and never mutates its input.
 */
export function normalizeWeekStart(raw) {
  let candidate = raw;
  if (raw && typeof raw === "object") {
    candidate = raw.weekStartsOn;
  }
  let parsed;
  if (typeof candidate === "number") {
    parsed = candidate;
  } else if (typeof candidate === "string" && candidate.trim() !== "") {
    parsed = Number(candidate.trim());
  } else {
    return DEFAULT_WEEK_START;
  }
  return parsed === 0 || parsed === 1 ? parsed : DEFAULT_WEEK_START;
}

/**
 * Return the current week's boundaries as `{ start, end }` timestamps, where
 * `start` is inclusive and `end` is exclusive. `weekStartsOn` uses
 * `Date#getDay` numbering (0 = Sunday); it defaults to `DEFAULT_WEEK_START`
 * (Monday) and is normalised into `0..6`. `now` is injectable for tests.
 */
export function weekWindow({
  now = Date.now(),
  weekStartsOn = DEFAULT_WEEK_START,
} = {}) {
  const resolved = toTimestamp(now);
  const base = startOfDay(resolved === null ? Date.now() : resolved);
  const requested = Number(weekStartsOn);
  const startDay = Number.isFinite(requested)
    ? ((Math.floor(requested) % 7) + 7) % 7
    : DEFAULT_WEEK_START;
  const day = new Date(base).getDay();
  const offset = (((day - startDay) % 7) + 7) % 7;
  const start = base - offset * DAY_MS;
  return { start, end: start + 7 * DAY_MS };
}

/**
 * Measure recent focus time against a weekly goal. Returns
 * `{ targetMinutes, focusedMinutes, remainingMinutes, percent, reached,
 * weekStart }`:
 *
 * - `targetMinutes` is the goal clamped to `0..MAX_GOAL_MINUTES`.
 * - `focusedMinutes` sums completed work entries in the current week, using the
 *   same label-matching rule as `summarise`/`labelSummary` (`UNLABELLED` counts
 *   entries without a label).
 * - `percent` is clamped to `0..100`; with no goal (`0`) it is `100` by
 *   definition rather than through division by zero.
 * - `reached` is only `true` when the target is positive and met.
 *
 * Pure: the input log is never mutated, and malformed entries are ignored.
 */
export function goalProgress(
  history,
  { now = Date.now(), minutes = 0, label, weekStartsOn = DEFAULT_WEEK_START } = {},
) {
  const { start, end } = weekWindow({ now, weekStartsOn });
  const targetMinutes = clampGoalMinutes(minutes);
  const filter = label === undefined || label === null ? null : String(label);
  const log = Array.isArray(history) ? history : [];

  let focusedMinutes = 0;
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null || timestamp < start || timestamp >= end) {
      continue;
    }
    if (filter !== null && (normalized.label || UNLABELLED) !== filter) {
      continue;
    }
    focusedMinutes += Math.round(normalized.durationSeconds / 60);
  }

  const reached = targetMinutes > 0 && focusedMinutes >= targetMinutes;
  const percent =
    targetMinutes <= 0
      ? 100
      : Math.min(
          100,
          Math.max(0, Math.round((focusedMinutes / targetMinutes) * 100)),
        );

  return {
    targetMinutes,
    focusedMinutes,
    remainingMinutes: Math.max(0, targetMinutes - focusedMinutes),
    percent,
    reached,
    weekStart: start,
  };
}

/**
 * Build a **weekly review** that lines the weekly focus goal up against the
 * per-label breakdown for the current week. Returns
 * `{ weekStart, targetMinutes, focusedMinutes, remainingMinutes, percent,
 * reached, labels, perLabel }`:
 *
 * - `targetMinutes` is the goal clamped to `0..MAX_GOAL_MINUTES`.
 * - `focusedMinutes` sums completed work entries in the current week, using the
 *   same label-matching rule as `goalProgress` (`UNLABELLED` counts entries
 *   without a label). Passing `label` scopes the whole review to it; without it
 *   every label seen this week is covered.
 * - `percent` is clamped to `0..100`; with no goal (`0`) it is `100`, matching
 *   `goalProgress`.
 * - `reached` is only `true` when the target is positive and met.
 * - `perLabel` covers every label seen in the (scoped) week plus an
 *   `UNLABELLED` bucket when applicable, each shaped as
 *   `{ label, sessions, minutes, percentOfTarget }`, sorted by minutes
 *   descending then label ascending. `percentOfTarget` is clamped to `0..100`
 *   and is `0` when there is no target.
 * - `labels` is the list of label names in `perLabel` order.
 *
 * Pure: the input log is never mutated, and malformed entries are ignored.
 */
export function weeklyReview(
  history,
  { now = Date.now(), minutes = 0, label, weekStartsOn = DEFAULT_WEEK_START } = {},
) {
  const { start, end } = weekWindow({ now, weekStartsOn });
  const targetMinutes = clampGoalMinutes(minutes);
  const filter = label === undefined || label === null ? null : String(label);
  const log = Array.isArray(history) ? history : [];

  const buckets = new Map();
  let focusedMinutes = 0;

  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null || timestamp < start || timestamp >= end) {
      continue;
    }
    const key = normalized.label || UNLABELLED;
    if (filter !== null && key !== filter) {
      continue;
    }
    const entryMinutes = Math.round(normalized.durationSeconds / 60);
    focusedMinutes += entryMinutes;
    const bucket = buckets.get(key) || { label: key, sessions: 0, minutes: 0 };
    bucket.sessions += 1;
    bucket.minutes += entryMinutes;
    buckets.set(key, bucket);
  }

  const perLabel = Array.from(buckets.values())
    .map((bucket) => ({
      label: bucket.label,
      sessions: bucket.sessions,
      minutes: bucket.minutes,
      percentOfTarget:
        targetMinutes <= 0
          ? 0
          : Math.min(
              100,
              Math.max(0, Math.round((bucket.minutes / targetMinutes) * 100)),
            ),
    }))
    .sort((a, b) => b.minutes - a.minutes || a.label.localeCompare(b.label));

  const reached = targetMinutes > 0 && focusedMinutes >= targetMinutes;
  const percent =
    targetMinutes <= 0
      ? 100
      : Math.min(
          100,
          Math.max(0, Math.round((focusedMinutes / targetMinutes) * 100)),
        );

  return {
    weekStart: start,
    targetMinutes,
    focusedMinutes,
    remainingMinutes: Math.max(0, targetMinutes - focusedMinutes),
    percent,
    reached,
    labels: perLabel.map((item) => item.label),
    perLabel,
  };
}

/** Quote a single CSV field per RFC 4180. A field containing a comma, a double
 * quote, or a line break is wrapped in double quotes and its internal quotes
 * are doubled; every other value is returned unchanged. `null` and `undefined`
 * become an empty field, and this helper never throws. */
function csvField(value) {
  const text = value === undefined || value === null ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Coerce an arbitrary value to a non-negative whole number for a CSV cell.
 * Malformed, negative, or non-finite input becomes `0`. */
function csvCount(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return 0;
  }
  return Math.round(parsed);
}

/**
 * Serialise a `weeklyReview(...)` result as an **RFC 4180 CSV** text.
 *
 * The output starts with a header row (`Label, Sessions, Minutes, Share of
 * target (%)`), then one row per `perLabel` entry, and ends with a `Total` row
 * that carries the summed sessions plus the review's `focusedMinutes` and
 * `percent`. The unlabelled bucket is rendered with `options.unlabelled` when a
 * non-empty string is provided (the DOM layer passes the localised catalog
 * string there) and with the shared `UNLABELLED` label otherwise, matching the
 * Weekly review panel. `options.locale` is accepted for API compatibility with
 * that layer.
 *
 * Deterministic and total: the input is never mutated, malformed shapes (a
 * missing `perLabel`, non-object rows, `null`, or `undefined`) degrade to an
 * empty review rather than throwing, and there is **no DOM, no storage, and no
 * network access**.
 */
export function weeklyReviewCsv(review, { locale, unlabelled } = {}) {
  void locale;
  const source = review && typeof review === "object" ? review : {};
  const rows = Array.isArray(source.perLabel)
    ? source.perLabel.filter((row) => row && typeof row === "object")
    : [];
  const unlabelledLabel =
    typeof unlabelled === "string" && unlabelled.length > 0
      ? unlabelled
      : UNLABELLED;

  const lines = [["Label", "Sessions", "Minutes", "Share of target (%)"]];
  let totalSessions = 0;

  for (const row of rows) {
    totalSessions += csvCount(row.sessions);
    const label = row.label === UNLABELLED ? unlabelledLabel : row.label;
    lines.push([
      label === undefined || label === null ? "" : label,
      csvCount(row.sessions),
      csvCount(row.minutes),
      csvCount(row.percentOfTarget),
    ]);
  }

  lines.push([
    "Total",
    totalSessions,
    csvCount(source.focusedMinutes),
    csvCount(source.percent),
  ]);

  return `${lines.map((cells) => cells.map(csvField).join(",")).join("\n")}\n`;
}

/**
 * Derive **focus streaks** from the local session log. Pure: no DOM, no
 * storage, and the input is never mutated. Returns
 * `{ current, longest, todayCount, todayMinutes, lastActiveDay }`:
 *
 * - `current` is the number of consecutive calendar days with at least one
 *   completed work entry, counting back from today. If today has no entry but
 *   yesterday does, the streak is still considered active and `current` counts
 *   from yesterday; otherwise it is `0`.
 * - `longest` is the longest such run anywhere in the retained history.
 * - `todayCount` / `todayMinutes` summarise today's completed work entries.
 * - `lastActiveDay` is the `YYYY-MM-DD` key of the most recent day with an
 *   entry, or `null` when there are none.
 *
 * Malformed entries and non-work phases are ignored exactly as in `summarise`.
 * `weekStartsOn` is accepted for signature consistency with the other weekly
 * helpers and normalised the same way as `weekWindow`; streaks are day-based,
 * so the value does not otherwise change the result.
 */
export function streaks(
  history,
  { now = Date.now(), weekStartsOn = DEFAULT_WEEK_START } = {},
) {
  void weekStartsOn;
  const resolved = toTimestamp(now);
  const todayStart = startOfDay(resolved === null ? Date.now() : resolved);
  const todayDate = new Date(todayStart);
  const todayKey = dateKey(todayDate);
  const tomorrowStart = new Date(
    todayDate.getFullYear(),
    todayDate.getMonth(),
    todayDate.getDate() + 1,
  ).getTime();
  const log = Array.isArray(history) ? history : [];

  const days = new Set();
  let todayCount = 0;
  let todaySeconds = 0;
  let lastTimestamp = null;

  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null) {
      continue;
    }
    days.add(dateKey(new Date(timestamp)));
    if (timestamp >= todayStart && timestamp < tomorrowStart) {
      todayCount += 1;
      todaySeconds += normalized.durationSeconds;
    }
    if (lastTimestamp === null || timestamp > lastTimestamp) {
      lastTimestamp = timestamp;
    }
  }

  const sortedDays = Array.from(days).sort();

  let longest = 0;
  let run = 0;
  let previous = null;
  for (const dayKeyValue of sortedDays) {
    const isConsecutive =
      previous !== null && dayKeyValue === shiftDayKey(previous, 1);
    run = isConsecutive ? run + 1 : 1;
    if (run > longest) {
      longest = run;
    }
    previous = dayKeyValue;
  }

  const yesterdayKey = shiftDayKey(todayKey, -1);
  let cursor = null;
  if (days.has(todayKey)) {
    cursor = todayKey;
  } else if (days.has(yesterdayKey)) {
    cursor = yesterdayKey;
  }

  let current = 0;
  while (cursor !== null && days.has(cursor)) {
    current += 1;
    cursor = shiftDayKey(cursor, -1);
  }

  return {
    current,
    longest,
    todayCount,
    todayMinutes: Math.round(todaySeconds / 60),
    lastActiveDay:
      lastTimestamp === null ? null : dateKey(new Date(lastTimestamp)),
  };
}
