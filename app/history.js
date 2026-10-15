/**
 * Focus Flow session history.
 *
 * Pure, dependency-free helpers for the local focus-session log. This module
 * has no access to the page, the storage layer, or the network: it only maps
 * plain data to plain data, so the DOM layer (main.js) owns all side effects
 * and the logic here can be reasoned about and tested on its own.
 *
 * A log entry is `{ endedAt, phase, durationSeconds }`. Only completed work
 * phases are recorded; breaks are ignored. `endedAt` is an ISO string.
 */

export const HISTORY_VERSION = 1;
export const MAX_ENTRIES = 500;
export const DEFAULT_RETENTION_DAYS = 90;

const DAY_MS = 24 * 60 * 60 * 1000;
const WORK_PHASE = "work";
const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

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
  return {
    endedAt: new Date(timestamp).toISOString(),
    phase: WORK_PHASE,
    durationSeconds: Math.round(duration),
  };
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
 * buckets in chronological order. Purely data in, data out.
 */
export function summarise(history, { now = Date.now(), days = 7 } = {}) {
  const spanDays = Math.max(1, Math.floor(days));
  const log = Array.isArray(history) ? history : [];
  const todayStart = startOfDay(now);
  const rangeStart = todayStart - (spanDays - 1) * DAY_MS;

  const buckets = new Map();
  for (let offset = 0; offset < spanDays; offset += 1) {
    const date = new Date(rangeStart + offset * DAY_MS);
    const key = dateKey(date);
    buckets.set(key, {
      date: key,
      label: DAY_NAMES[date.getDay()],
      count: 0,
      minutes: 0,
    });
  }

  let totalSessions = 0;
  let totalSeconds = 0;
  for (const entry of log) {
    const normalized = normalizeEntry(entry);
    if (!normalized) {
      continue;
    }
    const timestamp = toTimestamp(normalized.endedAt);
    if (timestamp === null || timestamp < rangeStart || timestamp >= todayStart + DAY_MS) {
      continue;
    }
    const bucket = buckets.get(dateKey(new Date(timestamp)));
    if (!bucket) {
      continue;
    }
    bucket.count += 1;
    bucket.minutes += Math.round(normalized.durationSeconds / 60);
    totalSessions += 1;
    totalSeconds += normalized.durationSeconds;
  }

  return {
    days: spanDays,
    totalSessions,
    totalMinutes: Math.round(totalSeconds / 60),
    perDay: Array.from(buckets.values()),
    empty: totalSessions === 0,
  };
}
