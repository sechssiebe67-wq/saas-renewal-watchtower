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
 * `recentLabels` derives the newest distinct labels from the log (trimmed,
 * case-insensitively de-duplicated, newest first) to power the keyboard
 * accessible session-label autocomplete; it reads no storage of its own and
 * makes no network request.
 *
 * The module also owns the pure maths for the optional **weekly focus goal**: a
 * locally stored `{ minutes, label? }` target. `weekWindow` finds the current
 * week, `goalProgress` measures the logged focus time against the target,
 * `weeklyReview` adds a per-label breakdown of the same week, and
 * `normalizeGoal` coerces arbitrary stored input into the canonical shape.
 * `weeklyReviewCsv` serialises a `weeklyReview` result to an RFC 4180 CSV
 * string for the local, offline **weekly review export**, and `goalPace` turns
 * a `weeklyReview` result into the forward-looking **weekly goal pace
 * projection** (remaining minutes, remaining calendar days, per-day pace, and
 * an on-track flag). `weeklyTrend` derives the **weekly focus trend
 * sparkline** — one total-minute point per week over the trailing `weeks`
 * weeks — from the same log. `labelShare` turns a `weeklyReview` result into
 * the **focus share** donut data (`{ total, slices, empty }`), one
 * `{ label, minutes, percent }` segment per label ranked by minutes descending
 * then label ascending. None of these touch the DOM, the storage layer, or the
 * network.
 *
 * It additionally owns the pure maths for the optional **daily focus goal**: a
 * `{ minutes, label? }` target for the current local calendar day.
 * `dailyGoalProgress` measures today's logged focus time against that target
 * using the same label-matching rule as `goalProgress`, `dailyReview` adds a
 * per-label breakdown of today (mirroring `weeklyReview`), and
 * `normalizeDailyGoal` coerces arbitrary stored input into the canonical shape
 * (clamped to a single day). `badgeState` turns a daily goal plus a
 * `dailyReview` result into the on-device **app badge** decision (the remaining
 * focused minutes, or `null`), leaving the feature-detected platform badge
 * calls to the DOM layer. These are pure too: no DOM, no storage, no network.
 *
 * Finally it owns the pure maths for the local **backup / restore** capability:
 * `exportBackup` / `backupToJson` turn already-read storage values into a
 * deterministic JSON envelope and `parseBackup` validates and normalises a
 * backup string back into canonical state through the existing pure helpers.
 * `backupFileName` derives the download name. These read no storage of their
 * own, make no network request, and never touch the DOM; the only sibling
 * modules they lean on (`normalizeAmbient`, `normalizeLocale`) are themselves
 * pure and dependency-free.
 *
 * It also owns the pure maths for the optional, device-only **session tag
 * aliases**: a `{ [canonicalLabel]: aliasLabel }` map that renames labels in
 * every derived view without rewriting history. `normalizeSessionTags` coerces
 * arbitrary stored input (an object, an array of `{ from, to }` pairs, or
 * anything else) into the canonical map (trimmed, non-empty, length-capped,
 * case-insensitively de-duplicated, entry-capped) and never throws;
 * `applyAliases` returns the alias for a label when one is present and the
 * original label otherwise. The `tags` option is threaded through `summarise`,
 * `labelSummary`, `recentSessions`, `recentLabels`, `goalProgress`,
 * `weeklyReview`, `weeklyTrend`, `dailyGoalProgress`, and `streaks` so callers
 * can get aliased labels back, while omitting it keeps the previous behaviour
 * byte-for-byte.
 * The map lives only in device storage under `focus-flow:session-tags`; this
 * module never touches the storage layer, the DOM, or the network.
 */

import { normalizeAmbient } from "./ambient.js";
import { normalizeLocale } from "./i18n.js";

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

/** Shape version for the `focus-flow:daily-goal` storage entry. Version 1 is
 * the initial `{ minutes, label? }` object; older or malformed values are
 * coerced by `normalizeDailyGoal`. */
export const DAILY_GOAL_STORAGE_SHAPE_VERSION = 1;

/** Lowest / highest meaningful daily goal. A goal is minutes focused per day;
 * the ceiling is a full day (24 × 60). */
export const MIN_DAILY_GOAL_MINUTES = 0;
export const MAX_DAILY_GOAL_MINUTES = 24 * 60;

/** Default first day of the week (Monday), matching `Date#getDay` numbering
 * where Sunday is `0`. */
export const DEFAULT_WEEK_START = 1;

/** Default number of weeks (including the current, partial week) covered by the
 * `weeklyTrend` sparkline. */
export const TREND_WEEKS = 8;

/** Default number of trailing weeks (including the current, partial week)
 * covered by the `focusHeatmap`. */
export const HEATMAP_WEEKS = 12;

/** Number of shading levels a heatmap day can use: `0` (no focused minutes)
 * through `4` (the range's current best day). */
export const HEATMAP_MAX_LEVEL = 4;

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

/** Shape version for the `focus-flow:session-tags` storage entry. Version 1 is
 * the initial `{ [canonicalLabel]: aliasLabel }` map; older or malformed values
 * are coerced by `normalizeSessionTags`. */
export const SESSION_TAGS_STORAGE_SHAPE_VERSION = 1;

/** The most alias entries kept in one map. Extra entries are dropped so the
 * map can never grow unbounded. */
export const SESSION_TAGS_MAX_ENTRIES = 50;

/** The longest accepted alias (the display label). A longer value is truncated
 * so one alias can never bloat device storage. */
export const SESSION_TAGS_MAX_ALIAS_LENGTH = MAX_LABEL_LENGTH;

/** Format version for the local backup JSON produced by `exportBackup`. Starts
 * at `1`; `parseBackup` refuses any version greater than this so a file written
 * by a future Focus Flow is never silently misinterpreted. */
export const BACKUP_FORMAT_VERSION = 1;

/** The stored entries captured by a backup, in the canonical order used
 * by the backup `data` object. Each name mirrors a `focus-flow:*` key owned by
 * the DOM layer (`settings` → `focus-flow:settings`, `history` →
 * `focus-flow:history`, and so on). Frozen so the contract cannot be reordered
 * or extended by accident. */
export const BACKUP_KEYS = Object.freeze([
  "settings",
  "history",
  "goal",
  "dailyGoal",
  "ambient",
  "locale",
  "weekStart",
  "sessionTags",
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

/** The `YYYY-MM-DD` key of the local week start that contains `timestamp`,
 * using `weekStartsOn` (`0` = Sunday, `1` = Monday). Uses calendar arithmetic
 * only, so a 23h/25h daylight-saving transition never shifts the bucket. */
function weekStartKeyOf(timestamp, weekStartsOn) {
  const base = startOfDay(timestamp);
  const day = new Date(base).getDay();
  const requested = Number(weekStartsOn);
  const startDay = Number.isFinite(requested)
    ? ((Math.floor(requested) % 7) + 7) % 7
    : DEFAULT_WEEK_START;
  const offset = (((day - startDay) % 7) + 7) % 7;
  return shiftDayKey(dateKey(new Date(base)), -offset);
}

/** Normalise an optional label: trim it, drop it when empty, and cap its
 * length so a single entry can never bloat local storage. */
function normalizeLabel(value) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim().slice(0, MAX_LABEL_LENGTH);
}

/** Trim a session-tag value to a non-empty, length-capped string (`max`
 * characters). Non-string or blank input becomes an empty string. */
function normalizeTagValue(value, max) {
  if (typeof value !== "string") {
    return "";
  }
  return value.trim().slice(0, max);
}

/**
 * Coerce arbitrary stored input into a canonical session-tag alias map.
 *
 * Accepts a `{ [canonicalLabel]: aliasLabel }` object, an array of
 * `{ from, to }` pairs, or anything else. Every label (the canonical key) is
 * trimmed and capped to `MAX_LABEL_LENGTH`, every alias (the display value) to
 * `SESSION_TAGS_MAX_ALIAS_LENGTH`; blank labels, blank aliases, and no-op
 * aliases (where the alias equals the label) are dropped, keys are
 * de-duplicated case-insensitively (the newest alias wins), and the map is
 * capped at `SESSION_TAGS_MAX_ENTRIES`. Never throws and never mutates its
 * input.
 */
export function normalizeSessionTags(raw) {
  const result = {};
  const seen = new Map();
  let count = 0;

  const assign = (rawLabel, rawAlias) => {
    const label = normalizeTagValue(rawLabel, MAX_LABEL_LENGTH);
    const alias = normalizeTagValue(rawAlias, SESSION_TAGS_MAX_ALIAS_LENGTH);
    if (label.length === 0 || alias.length === 0 || label === alias) {
      return;
    }
    const key = label.toLowerCase();
    const existing = seen.get(key);
    if (existing !== undefined) {
      result[existing] = alias;
      return;
    }
    if (count >= SESSION_TAGS_MAX_ENTRIES) {
      return;
    }
    seen.set(key, label);
    result[label] = alias;
    count += 1;
  };

  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (item && typeof item === "object") {
        assign(item.from, item.to);
      }
    }
  } else if (raw && typeof raw === "object") {
    for (const label of Object.keys(raw)) {
      assign(label, raw[label]);
    }
  }

  return result;
}

/**
 * Return the alias for `label` when `tags` (a map produced by
 * `normalizeSessionTags`) has one, and `label` itself otherwise. The lookup is
 * case-insensitive, so a stored label matches regardless of the casing used in
 * the map, and malformed input is returned unchanged. Both `(label, tags)` and
 * `(tags, label)` call orders are tolerated, and this function never throws.
 */
export function applyAliases(label, tags) {
  if ((!tags || typeof tags !== "object") && label && typeof label === "object") {
    const swapped = label;
    label = tags;
    tags = swapped;
  }
  if (typeof label !== "string" || label.length === 0) {
    return label;
  }
  if (!tags || typeof tags !== "object") {
    return label;
  }
  let alias;
  if (Object.prototype.hasOwnProperty.call(tags, label)) {
    alias = tags[label];
  } else {
    const lower = label.toLowerCase();
    for (const key of Object.keys(tags)) {
      if (key.toLowerCase() === lower) {
        alias = tags[key];
        break;
      }
    }
  }
  return typeof alias === "string" && alias.length > 0 ? alias : label;
}

/** De-duplicate a list of labels case-insensitively, keeping the first (newest)
 * occurrence of each. Shared by `recentLabels` so aliased suggestions collapse. */
function uniqueLabels(labels) {
  const seen = new Set();
  const result = [];
  for (const label of labels) {
    const key = label.toLowerCase();
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(label);
  }
  return result;
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
 * `UNLABELLED` to count entries without a label. When `tags` is provided (a
 * `normalizeSessionTags` map) each entry's label is matched through
 * `applyAliases`, so a filter expressed as a display alias still finds its
 * sessions. Purely data in, data out.
 */
export function summarise(
  history,
  { now = Date.now(), days = 7, label, tags } = {},
) {
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
    const entryLabel = applyAliases(entry.label, tags);
    if (filter !== null && (entryLabel || UNLABELLED) !== filter) {
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
 * When `tags` is provided the group keys are the aliased display labels, so
 * several stored labels that share an alias are merged into one bucket.
 */
export function labelSummary(
  history,
  { now = Date.now(), days = 7, labels, tags } = {},
) {
  const { entries } = collectWindow(history, { now, days });
  const allow =
    Array.isArray(labels) && labels.length > 0 ? new Set(labels) : null;

  const totals = new Map();
  let unlabelled = { sessions: 0, minutes: 0 };

  for (const entry of entries) {
    if (entry.label) {
      const display = applyAliases(entry.label, tags);
      if (allow && !allow.has(display)) {
        continue;
      }
      const bucket = totals.get(display) || { sessions: 0, minutes: 0 };
      bucket.sessions += 1;
      bucket.minutes += Math.round(entry.durationSeconds / 60);
      totals.set(display, bucket);
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
 * entries so the caller can render its own placeholder. When `tags` is provided
 * each returned label is run through `applyAliases`.
 */
export function recentSessions(history, { limit = 5, tags } = {}) {
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
      label: applyAliases(label, tags),
      durationSeconds,
    }));
}

/**
 * Return the most recently used distinct session labels as a list of strings,
 * newest first by `endedAt`, capped at `limit`.
 *
 * This powers the **session-label autocomplete**: it derives suggestions only
 * from the already-local `focus-flow:history` log, so it adds no new storage
 * key, makes no network request, and never leaves the device.
 *
 * Rules:
 *
 * - Only completed work entries with a non-empty label contribute.
 * - Labels are trimmed and capped to `MAX_LABEL_LENGTH` by `normalizeLabel`.
 * - De-duplication is **case-insensitive**; the casing of the most recently
 *   used occurrence is kept (e.g. `Thesis chapter 3`).
 * - Entries with a malformed or future (`endedAt > now`) timestamp are ignored,
 *   so a skewed clock cannot surface a session that has not ended yet.
 * - `limit` is coerced to a non-negative integer; malformed input becomes `0`.
 *
 * When `tags` is provided the returned labels are run through `applyAliases`
 * and de-duplicated again, so two stored labels that share a display alias
 * appear once.
 *
 * Pure: it never touches the DOM, storage, or the network, never mutates the
 * input log, and never throws on malformed input.
 */
export function recentLabels(
  history,
  { limit = 8, now = Date.now(), tags } = {},
) {
  const log = Array.isArray(history) ? history : [];
  const requested = Number(limit);
  const max = Number.isFinite(requested) ? Math.max(0, Math.floor(requested)) : 0;
  const reference = toTimestamp(now);
  const cutoff = reference === null ? Date.now() : reference;

  const latest = new Map();
  for (const entry of log) {
    if (!entry || typeof entry !== "object" || entry.phase !== WORK_PHASE) {
      continue;
    }
    const label = normalizeLabel(entry.label);
    if (label.length === 0) {
      continue;
    }
    const timestamp = toTimestamp(entry.endedAt);
    if (timestamp === null || timestamp > cutoff) {
      continue;
    }
    const key = label.toLowerCase();
    const seen = latest.get(key);
    if (!seen || timestamp > seen.timestamp) {
      latest.set(key, { label, timestamp });
    }
  }

  return uniqueLabels(
    Array.from(latest.values())
      .sort((a, b) => b.timestamp - a.timestamp)
      .map((item) => applyAliases(item.label, tags)),
  ).slice(0, max);
}

/** Clamp an arbitrary value to `0..max`, rounding to whole minutes. Malformed
 * or non-finite input becomes `0`. */
function clampMinutes(value, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.min(max, Math.max(0, Math.round(parsed)));
}

/** Clamp an arbitrary value to the weekly goal bounds, rounding to whole
 * minutes. */
function clampGoalMinutes(value) {
  return clampMinutes(value, MAX_GOAL_MINUTES);
}

/** Clamp an arbitrary value to the daily goal bounds (a single day),
 * rounding to whole minutes. */
function clampDailyGoalMinutes(value) {
  return clampMinutes(value, MAX_DAILY_GOAL_MINUTES);
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
 * Coerce arbitrary stored input into a canonical daily `{ minutes, label? }`
 * goal. `minutes` is clamped to `0..MAX_DAILY_GOAL_MINUTES` (a full day) and
 * rounded to a whole number; `label` is trimmed to `MAX_LABEL_LENGTH` and
 * dropped when it is empty. Never throws and never mutates its input.
 */
export function normalizeDailyGoal(raw) {
  let source;
  if (typeof raw === "number") {
    source = { minutes: raw };
  } else if (raw && typeof raw === "object") {
    source = raw;
  } else {
    source = {};
  }
  const goal = { minutes: clampDailyGoalMinutes(source.minutes) };
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
 * When `tags` is provided each entry's label is matched through
 * `applyAliases`, so a label-scoped goal expressed as a display alias still
 * finds its sessions. Pure: the input log is never mutated, and malformed
 * entries are ignored.
 */
export function goalProgress(
  history,
  {
    now = Date.now(),
    minutes = 0,
    label,
    weekStartsOn = DEFAULT_WEEK_START,
    tags,
  } = {},
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
    if (
      filter !== null &&
      (applyAliases(normalized.label, tags) || UNLABELLED) !== filter
    ) {
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
 * Measure today's focus time against a **daily** goal. Returns
 * `{ targetMinutes, focusedMinutes, remainingMinutes, percent, reached,
 * dayStart }`:
 *
 * - `targetMinutes` is the goal clamped to `0..MAX_DAILY_GOAL_MINUTES`.
 * - `focusedMinutes` sums completed work entries whose `endedAt` falls on the
 *   current **local calendar day**, using the same label-matching rule as
 *   `goalProgress` (`UNLABELLED` counts entries without a label).
 * - `percent` is clamped to `0..100`; with no goal (`0`) it is `100` by
 *   definition rather than through division by zero.
 * - `reached` is only `true` when the target is positive and met.
 * - `dayStart` is the inclusive start of today (local midnight).
 *
 * The day span is computed with local calendar arithmetic, so a 23h/25h
 * daylight-saving transition never drops or duplicates entries. When `tags` is
 * provided each entry's label is matched through `applyAliases`, so a
 * label-scoped goal expressed as a display alias still finds its sessions.
 * Pure: the input log is never mutated, malformed entries and non-work phases
 * are ignored, and there is no DOM, storage, or network access.
 */
export function dailyGoalProgress(
  history,
  { now = Date.now(), minutes = 0, label, tags } = {},
) {
  const resolved = toTimestamp(now);
  const base = resolved === null ? Date.now() : resolved;
  const baseDate = new Date(base);
  const dayStart = new Date(
    baseDate.getFullYear(),
    baseDate.getMonth(),
    baseDate.getDate(),
  ).getTime();
  const dayEnd = new Date(
    baseDate.getFullYear(),
    baseDate.getMonth(),
    baseDate.getDate() + 1,
  ).getTime();
  const targetMinutes = clampDailyGoalMinutes(minutes);
  const filter = label === undefined || label === null ? null : String(label);
  const log = Array.isArray(history) ? history : [];

  let focusedMinutes = 0;
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (
      timestamp === null ||
      timestamp < dayStart ||
      timestamp >= dayEnd
    ) {
      continue;
    }
    if (
      filter !== null &&
      (applyAliases(normalized.label, tags) || UNLABELLED) !== filter
    ) {
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
    dayStart,
  };
}

/**
 * Build a **daily review** that lines the daily focus goal up against the
 * per-label breakdown for the current local calendar day. Returns
 * `{ dayStart, targetMinutes, focusedMinutes, remainingMinutes, percent,
 * reached, scoped, labels, perLabel }`:
 *
 * - `targetMinutes` is `goal.minutes` clamped to `0..MAX_DAILY_GOAL_MINUTES`.
 * - `focusedMinutes` sums completed work entries on the current local calendar
 *   day, using the same label-matching rule as `dailyGoalProgress` (`UNLABELLED`
 *   counts entries without a label). The optional `goal.label` scopes the whole
 *   review to it; without it every label seen today is covered.
 * - `percent` is clamped to `0..100`; with no goal (`0`) it is `100`, matching
 *   `dailyGoalProgress`.
 * - `reached` is only `true` when the target is positive and met.
 * - `perLabel` covers every label seen today plus an `UNLABELLED` bucket when
 *   applicable, each shaped as `{ label, sessions, minutes, percentOfTarget }`,
 *   sorted by minutes descending then label ascending. `percentOfTarget` is
 *   clamped to `0..100` and is `0` when there is no target.
 * - `labels` is the list of label names in `perLabel` order.
 * - `scoped` is `true` when the goal carries a `label`, so the DOM layer can
 *   label the breakdown as a single-label view without inspecting `perLabel`.
 *
 * When `tags` is provided each entry's label is run through `applyAliases`, so
 * the breakdown groups by display alias and a label-scoped goal expressed as an
 * alias still matches. The day span is computed with local calendar arithmetic,
 * so a 23h/25h daylight-saving transition never drops or duplicates entries.
 * Pure: the input log is never mutated, malformed entries and non-work phases
 * are ignored, and there is no DOM, storage, or network access.
 */
export function dailyReview(history, { now = Date.now(), goal, tags } = {}) {
  const resolvedGoal = normalizeDailyGoal(goal);
  const filter =
    resolvedGoal.label === undefined ? null : String(resolvedGoal.label);
  const progress = dailyGoalProgress(history, {
    now,
    minutes: resolvedGoal.minutes,
    label: filter === null ? undefined : filter,
    tags,
  });

  const resolvedNow = toTimestamp(now);
  const base = resolvedNow === null ? Date.now() : resolvedNow;
  const baseDate = new Date(base);
  const dayEnd = new Date(
    baseDate.getFullYear(),
    baseDate.getMonth(),
    baseDate.getDate() + 1,
  ).getTime();

  const log = Array.isArray(history) ? history : [];
  const buckets = new Map();
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (
      timestamp === null ||
      timestamp < progress.dayStart ||
      timestamp >= dayEnd
    ) {
      continue;
    }
    const key = applyAliases(normalized.label, tags) || UNLABELLED;
    if (filter !== null && key !== filter) {
      continue;
    }
    const entryMinutes = Math.round(normalized.durationSeconds / 60);
    const bucket = buckets.get(key) || { label: key, sessions: 0, minutes: 0 };
    bucket.sessions += 1;
    bucket.minutes += entryMinutes;
    buckets.set(key, bucket);
  }

  const targetMinutes = progress.targetMinutes;
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

  return {
    dayStart: progress.dayStart,
    targetMinutes,
    focusedMinutes: progress.focusedMinutes,
    remainingMinutes: progress.remainingMinutes,
    percent: progress.percent,
    reached: progress.reached,
    scoped: filter !== null,
    labels: perLabel.map((item) => item.label),
    perLabel,
  };
}

/**
 * Decide the value for the on-device **app badge** from the daily goal and a
 * `dailyReview` result.
 *
 * Returns `null` when no daily goal is set, when the review is missing or
 * malformed, or when the goal has been reached; otherwise it returns the
 * remaining focused minutes, clamped to `>= 0`. Pure and injectable: it reads
 * no DOM, no storage, and no platform API, so the DOM layer owns the
 * feature-detected badge calls and unsupported browsers are unaffected.
 */
export function badgeState({ goal, review } = {}) {
  const resolvedGoal = normalizeDailyGoal(goal);
  if (resolvedGoal.minutes <= 0) {
    return null;
  }
  if (!review || typeof review !== "object") {
    return null;
  }
  const target = clampDailyGoalMinutes(review.targetMinutes);
  if (target <= 0) {
    return null;
  }
  const focusedValue = Number(review.focusedMinutes);
  const focused = Number.isFinite(focusedValue)
    ? Math.max(0, Math.round(focusedValue))
    : 0;
  if (review.reached === true || focused >= target) {
    return null;
  }
  return Math.max(0, target - focused);
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
 * - `scoped` is `true` when a `label` filter was supplied, so the DOM layer can
 *   label the breakdown as a single-label view without inspecting `perLabel`.
 *
 * When `tags` is provided each entry's label is run through `applyAliases`, so
 * the breakdown groups by display alias and a label filter expressed as an
 * alias still matches. Pure: the input log is never mutated, and malformed
 * entries are ignored.
 */
export function weeklyReview(
  history,
  {
    now = Date.now(),
    minutes = 0,
    label,
    weekStartsOn = DEFAULT_WEEK_START,
    tags,
  } = {},
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
    const key = applyAliases(normalized.label, tags) || UNLABELLED;
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
    scoped: filter !== null,
    labels: perLabel.map((item) => item.label),
    perLabel,
  };
}

/**
 * Project the **weekly goal pace** from a `weeklyReview` result.
 *
 * Returns `{ remainingMinutes, remainingDays, perDayMinutes, onTrack }`, or
 * `null` when there is no usable goal (so the DOM layer can simply hide the
 * line):
 *
 * - `remainingMinutes` is `max(0, targetMinutes − focusedMinutes)`.
 * - `remainingDays` is the number of local calendar days left in the current
 *   week **including today**, counted with calendar arithmetic so a 23h/25h
 *   daylight-saving transition never desynchronises the count.
 * - `perDayMinutes` is the rounded per-remaining-day requirement, and is `0`
 *   once the goal is met.
 * - `onTrack` is `true` when the goal is already met or the current daily
 *   average (focused minutes divided by the elapsed days, today included) meets
 *   the required pace.
 *
 * The week bounds come from `weekWindow` using the caller's `weekStart`
 * preference (coerced by `normalizeWeekStart`), so the projection lines up with
 * the `weekStartsOn` used to build the review. `now` is injectable for tests.
 * Pure: it touches no DOM, no storage, and no network, never mutates its input,
 * and never throws on malformed input.
 */
export function goalPace(
  review,
  { now = Date.now(), weekStart, weekStartsOn } = {},
) {
  if (!review || typeof review !== "object") {
    return null;
  }
  const targetValue = Number(review.targetMinutes);
  if (!Number.isFinite(targetValue) || targetValue <= 0) {
    return null;
  }
  const targetMinutes = Math.round(targetValue);
  if (targetMinutes <= 0) {
    return null;
  }
  const focusedValue = Number(review.focusedMinutes);
  const focusedMinutes = Number.isFinite(focusedValue)
    ? Math.max(0, Math.round(focusedValue))
    : 0;
  const remainingMinutes = Math.max(0, targetMinutes - focusedMinutes);

  const resolvedNow = toTimestamp(now);
  const base = resolvedNow === null ? Date.now() : resolvedNow;
  const preference =
    weekStartsOn === undefined || weekStartsOn === null
      ? weekStart
      : weekStartsOn;
  const resolvedWeekStart =
    preference === undefined || preference === null
      ? DEFAULT_WEEK_START
      : normalizeWeekStart(preference);
  const { start } = weekWindow({
    now: base,
    weekStartsOn: resolvedWeekStart,
  });

  // Count the remaining days with calendar arithmetic (never `DAY_MS`), so a
  // 23h/25h daylight-saving day cannot add or drop a day. The week start itself
  // comes from the shared `weekWindow` helper.
  const firstKey = dateKey(new Date(start));
  const lastKey = shiftDayKey(firstKey, 6);
  const todayKey = dateKey(new Date(base));

  let remainingDays = 0;
  if (todayKey <= lastKey) {
    let cursor = todayKey;
    while (true) {
      remainingDays += 1;
      if (cursor === lastKey) {
        break;
      }
      const next = shiftDayKey(cursor, 1);
      if (next === cursor || next > lastKey) {
        break;
      }
      cursor = next;
    }
  }

  let elapsedDays = 0;
  if (todayKey >= firstKey) {
    let cursor = firstKey;
    while (true) {
      elapsedDays += 1;
      if (cursor === todayKey) {
        break;
      }
      const next = shiftDayKey(cursor, 1);
      if (next === cursor || next > todayKey) {
        break;
      }
      cursor = next;
    }
  }
  if (elapsedDays <= 0) {
    elapsedDays = 1;
  }

  const perDayMinutes =
    remainingMinutes === 0
      ? 0
      : remainingDays > 0
        ? Math.round(remainingMinutes / remainingDays)
        : remainingMinutes;

  const currentAverage = focusedMinutes / elapsedDays;
  const onTrack = remainingMinutes === 0 || currentAverage >= perDayMinutes;

  return { remainingMinutes, remainingDays, perDayMinutes, onTrack };
}

/** Classify a series of weekly totals as trending `"up"`, `"down"`, or
 * `"flat"` by comparing the newest week with the week before it. Fewer than
 * two points is `"flat"`. */
function trendDirection(values) {
  const count = Array.isArray(values) ? values.length : 0;
  if (count < 2) {
    return "flat";
  }
  const latest = values[count - 1];
  const previous = values[count - 2];
  if (latest > previous) {
    return "up";
  }
  if (latest < previous) {
    return "down";
  }
  return "flat";
}

/**
 * Compute the **weekly focus trend** over the trailing `weeks` weeks
 * (including the current, partial week).
 *
 * Returns `{ weeks, points, min, max, direction, empty }`:
 *
 * - `points` is one `{ weekStart, minutes }` bucket per week in chronological
 *   order (oldest first), where `weekStart` is the `YYYY-MM-DD` key of that
 *   week's first day and `minutes` is the rounded total focused minutes.
 * - `min` / `max` are the smallest and largest weekly totals (`0` when there
 *   are no points).
 * - `direction` is `"up"`, `"down"`, or `"flat"`, taken from the newest week
 *   compared with the week before it.
 * - `empty` is `true` when every bucket is zero, so the DOM layer can show the
 *   localised empty-state message instead of an empty chart.
 *
 * The week boundaries follow the user's **Week starts on** preference
 * (`weekStart` / `weekStartsOn`, coerced by `normalizeWeekStart`) and are
 * computed with local calendar arithmetic, so daylight-saving transitions never
 * shift, drop, or duplicate a bucket. The active label filter is honoured and
 * labels are resolved through the optional `tags` map exactly as
 * `weeklyReview` does (`UNLABELLED` matches unlabelled entries). `now` is
 * injectable for tests. The requested `weeks` is clamped to `1..26`, so a
 * caller can never force an unbounded bucket array. Pure: it reads no storage,
 * makes no network request, never mutates its input, and never throws on
 * malformed input.
 */
export function weeklyTrend(
  history,
  {
    now = Date.now(),
    weeks = TREND_WEEKS,
    weekStart,
    weekStartsOn,
    label,
    tags,
  } = {},
) {
  const preference =
    weekStartsOn === undefined || weekStartsOn === null ? weekStart : weekStartsOn;
  const resolvedWeekStart =
    preference === undefined || preference === null
      ? DEFAULT_WEEK_START
      : normalizeWeekStart(preference);

  const resolvedNow = toTimestamp(now);
  const base = resolvedNow === null ? Date.now() : resolvedNow;

  const requested = Number(weeks);
  const count = Number.isFinite(requested)
    ? Math.min(26, Math.max(1, Math.floor(requested)))
    : TREND_WEEKS;

  const currentKey = weekStartKeyOf(base, resolvedWeekStart);
  const keys = [];
  for (let back = count - 1; back >= 0; back -= 1) {
    keys.push(shiftDayKey(currentKey, -7 * back));
  }
  const included = new Set(keys);

  const filter = label === undefined || label === null ? null : String(label);
  const totals = new Map();
  const log = Array.isArray(history) ? history : [];

  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null) {
      continue;
    }
    const key = weekStartKeyOf(timestamp, resolvedWeekStart);
    if (!included.has(key)) {
      continue;
    }
    const entryLabel = applyAliases(normalized.label, tags) || UNLABELLED;
    if (filter !== null && entryLabel !== filter) {
      continue;
    }
    const minutes = Math.round(normalized.durationSeconds / 60);
    totals.set(key, (totals.get(key) || 0) + minutes);
  }

  const points = keys.map((key) => ({
    weekStart: key,
    minutes: totals.get(key) || 0,
  }));

  const values = points.map((point) => point.minutes);
  const min = values.length === 0 ? 0 : Math.min(...values);
  const max = values.length === 0 ? 0 : Math.max(...values);

  return {
    weeks: points.length,
    points,
    min,
    max,
    direction: trendDirection(values),
    empty: values.every((value) => value === 0),
  };
}

/** Map a day's focused minutes onto a `0..HEATMAP_MAX_LEVEL` shade. A day with
 * no minutes (or a range whose best day is `0`) is always level `0`; every
 * positive day gets at least level `1` and the best day gets the top level. */
function heatmapLevel(minutes, maxMinutes) {
  if (maxMinutes <= 0 || minutes <= 0) {
    return 0;
  }
  const ratio = minutes / maxMinutes;
  return Math.min(
    HEATMAP_MAX_LEVEL,
    Math.max(1, Math.ceil(ratio * HEATMAP_MAX_LEVEL)),
  );
}

/**
 * Build the **focus heatmap** view over the trailing `weeks` weeks (including
 * the current, partial week).
 *
 * Returns `{ weeks, days, maxMinutes, empty }`:
 *
 * - `days` is one `{ date, minutes, sessions, level }` bucket per **local
 *   calendar day** in chronological order (oldest first, today last), exactly
 *   `weeks * 7` buckets. `date` is the `YYYY-MM-DD` calendar key, `minutes` is
 *   the rounded total focused minutes and `sessions` the number of completed
 *   work entries on that day; both are zero-filled. `level` is an integer
 *   `0..HEATMAP_MAX_LEVEL` derived from `minutes / maxMinutes`, so the range's
 *   best day gets the top shade.
 * - `maxMinutes` is the largest daily total in the range (`0` when there are
 *   none), i.e. the user's current best day.
 * - `empty` is `true` when `maxMinutes` is `0`, so the DOM layer can show the
 *   localised empty-state message instead of an all-zero grid. With
 *   `maxMinutes === 0` every day is `level: 0`.
 *
 * The day buckets are built with local calendar arithmetic (`dateKey` /
 * `shiftDayKey`), so daylight-saving transitions never shift, drop, or
 * duplicate a bucket. The active label filter is honoured and labels are
 * resolved through the optional `tags` map exactly as `weeklyReview` does
 * (`UNLABELLED` matches unlabelled entries). `weeks` is clamped to `1..26`, so
 * a caller can never force an unbounded bucket array; `weekStartsOn` is
 * accepted for symmetry with the week-scoped views and reserved for the DOM
 * grid alignment. `now` is injectable for tests. Pure: it reads no storage,
 * makes no network request, never mutates its input, and never throws on
 * malformed input.
 */
export function focusHeatmap(
  history,
  { now = Date.now(), weeks = HEATMAP_WEEKS, weekStartsOn, label, tags } = {},
) {
  void weekStartsOn;

  const resolvedNow = toTimestamp(now);
  const base = resolvedNow === null ? Date.now() : resolvedNow;

  const requested = Number(weeks);
  const count = Number.isFinite(requested)
    ? Math.min(26, Math.max(1, Math.floor(requested)))
    : HEATMAP_WEEKS;
  const totalDays = count * 7;

  const todayKey = dateKey(new Date(startOfDay(base)));
  const keys = [];
  for (let offset = totalDays - 1; offset >= 0; offset -= 1) {
    keys.push(shiftDayKey(todayKey, -offset));
  }

  const filter = label === undefined || label === null ? null : String(label);
  const log = Array.isArray(history) ? history : [];
  const buckets = new Map();
  for (const key of keys) {
    buckets.set(key, { date: key, minutes: 0, sessions: 0 });
  }

  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null) {
      continue;
    }
    const key = dateKey(new Date(timestamp));
    const bucket = buckets.get(key);
    if (!bucket) {
      continue;
    }
    const entryLabel = applyAliases(normalized.label, tags) || UNLABELLED;
    if (filter !== null && entryLabel !== filter) {
      continue;
    }
    bucket.sessions += 1;
    bucket.minutes += Math.round(normalized.durationSeconds / 60);
  }

  const days = keys.map((key) => buckets.get(key));
  const maxMinutes = days.reduce(
    (max, day) => Math.max(max, day.minutes),
    0,
  );
  for (const day of days) {
    day.level = heatmapLevel(day.minutes, maxMinutes);
  }

  return {
    weeks: count,
    days,
    maxMinutes,
    empty: maxMinutes === 0,
  };
}

/** Compare two labels for the minutes-descending / label-ascending ranking used
 * by the per-label views. Non-string labels are coerced so a malformed row can
 * never throw. */
function compareLabels(a, b) {
  return String(a).localeCompare(String(b));
}

/**
 * Derive the **focus share** donut from a `weeklyReview` result.
 *
 * The Stats panel uses this to answer *"where did my focused time go this
 * week?"* at a glance: one ring segment per session label seen in the current
 * week (plus the `UNLABELLED` bucket when unlabelled sessions exist), sized by
 * each label's share of the week's total focused minutes.
 *
 * Returns `{ total, slices, empty }`:
 *
 * - `total` is the summed focused minutes across every slice (identical to the
 *   review's `focusedMinutes`).
 * - `slices` is one `{ label, minutes, percent }` entry per `perLabel` row,
 *   ranked by minutes descending then label ascending. `percent` is the rounded
 *   share of `total` (clamped to `0..100`) and is `0` when `total` is `0`.
 * - `empty` is `true` when there are no label rows, so the DOM layer can show
 *   the localised empty state instead of an empty ring.
 *
 * It reads the already-computed `weeklyReview` result only — so the label
 * filter and the alias map are already applied — and touches no DOM, no
 * storage, and no network. Total: `null`, `undefined`, and malformed rows
 * degrade to `{ total: 0, slices: [], empty: true }` instead of throwing, the
 * input is never mutated, and missing or non-finite minutes are treated as `0`.
 */
export function labelShare(review) {
  const source = review && typeof review === "object" ? review : {};
  const rows = Array.isArray(source.perLabel)
    ? source.perLabel.filter((row) => row && typeof row === "object")
    : [];

  const slices = [];
  let total = 0;
  for (const row of rows) {
    const parsed = Number(row.minutes);
    const minutes = Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0;
    total += minutes;
    slices.push({ label: row.label, minutes });
  }

  const ranked = slices
    .map((slice) => ({
      label: slice.label,
      minutes: slice.minutes,
      percent:
        total > 0
          ? Math.min(100, Math.max(0, Math.round((slice.minutes / total) * 100)))
          : 0,
    }))
    .sort((a, b) => b.minutes - a.minutes || compareLabels(a.label, b.label));

  return { total, slices: ranked, empty: ranked.length === 0 };
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

/** True when `value` is a positive whole number, used to guard a backup's
 * `version` field. */
function isPositiveInteger(value) {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

/**
 * Build the in-memory backup envelope from already-read storage values.
 *
 * `state` is a plain object keyed by `BACKUP_KEYS` — the values the DOM layer
 * reads from device storage. Returns `{ version, exportedAt, data }`, where
 * `data` carries the same keys in canonical `BACKUP_KEYS` order and
 * `exportedAt` is an ISO timestamp. `options.now` is injectable so tests can
 * pin the timestamp and assert byte-for-byte determinism. Pure: it touches no
 * DOM, no storage, and no network, and it never mutates its input.
 */
export function exportBackup(state, { now = Date.now() } = {}) {
  const source = state && typeof state === "object" ? state : {};
  const data = {};
  for (const key of BACKUP_KEYS) {
    data[key] = source[key] === undefined ? null : source[key];
  }
  const resolved = toTimestamp(now);
  return {
    version: BACKUP_FORMAT_VERSION,
    exportedAt: new Date(
      resolved === null ? Date.now() : resolved,
    ).toISOString(),
    data,
  };
}

/**
 * Serialise `exportBackup(state)` to a deterministic, diff-friendly JSON string
 * (2-space indent, stable key order). `options` is forwarded to `exportBackup`,
 * so callers can pin `now`. Pure and non-mutating: the same input always
 * produces the same bytes.
 */
export function backupToJson(state, options) {
  return JSON.stringify(exportBackup(state, options), null, 2);
}

/**
 * Parse a backup JSON string into a normalised state object, or `null` when the
 * text is not a usable Focus Flow backup.
 *
 * Accepts both the full `{ version, exportedAt, data }` envelope produced by
 * `exportBackup` and a bare, `data`-shaped object. A `version` that is not a
 * positive integer, or is greater than `BACKUP_FORMAT_VERSION`, is rejected as
 * a forward-compatibility guard. Every field is run through the existing pure
 * normalisers (`pruneHistory`, `normalizeGoal`, `normalizeDailyGoal`,
 * `normalizeAmbient`, `normalizeLocale`, `normalizeWeekStart`,
 * `normalizeSessionTags`), so the result is canonical; `settings` is carried
 * through untouched for the DOM layer to normalise. Total: bad JSON, wrong
 * types, missing fields, and `null` all return `null` instead of throwing.
 * `now` and `retentionDays` are injectable for tests.
 */
export function parseBackup(
  text,
  { now = Date.now(), retentionDays = DEFAULT_RETENTION_DAYS } = {},
) {
  if (typeof text !== "string" || text.length === 0) {
    return null;
  }
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch (error) {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    return null;
  }

  let data;
  if (Object.prototype.hasOwnProperty.call(parsed, "data")) {
    if (
      !parsed.data ||
      typeof parsed.data !== "object" ||
      Array.isArray(parsed.data)
    ) {
      return null;
    }
    if (
      !isPositiveInteger(parsed.version) ||
      parsed.version > BACKUP_FORMAT_VERSION
    ) {
      return null;
    }
    data = parsed.data;
  } else if (Object.prototype.hasOwnProperty.call(parsed, "version")) {
    return null;
  } else {
    data = parsed;
  }

  return {
    settings:
      data.settings && typeof data.settings === "object"
        ? data.settings
        : null,
    history: pruneHistory(data.history, { now, retentionDays }),
    goal: normalizeGoal(data.goal),
    dailyGoal: normalizeDailyGoal(data.dailyGoal),
    ambient: normalizeAmbient(data.ambient),
    locale: normalizeLocale(data.locale),
    weekStart: normalizeWeekStart(data.weekStart),
    sessionTags: normalizeSessionTags(data.sessionTags),
  };
}

/**
 * The download name for a backup taken at `now`:
 * `focus-flow-backup-<YYYY-MM-DD>.json`, using the same local-calendar date key
 * as the rest of the module.
 */
export function backupFileName(now = Date.now()) {
  const resolved = toTimestamp(now);
  const date = new Date(resolved === null ? Date.now() : resolved);
  return `focus-flow-backup-${dateKey(date)}.json`;
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
 * so the value does not otherwise change the result. `tags` is likewise
 * accepted for signature consistency with the other derived views; a streak
 * aggregates whole days rather than labels, so it does not change the result.
 */
export function streaks(
  history,
  { now = Date.now(), weekStartsOn = DEFAULT_WEEK_START, tags } = {},
) {
  void weekStartsOn;
  void tags;
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
