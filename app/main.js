/**
 * Focus Flow — DOM layer.
 *
 * Wires the pure TimerEngine (timer.js) to the page, persists settings and the
 * session count in localStorage, plays a short Web Audio chime, and handles
 * theme switching and keyboard shortcuts.
 */

import {
  TimerEngine,
  PHASES,
  PHASE_LABELS,
  DEFAULT_SETTINGS,
  normalizeSettings,
  formatTime,
} from "./timer.js";

import {
  AMBIENT_LABELS,
  DEFAULT_AMBIENT,
  normalizeAmbient,
  createNoiseBuffer,
  shouldPlay,
} from "./ambient.js";

import {
  DEFAULT_RETENTION_DAYS,
  DEFAULT_WEEK_START,
  recordSession,
  pruneHistory,
  summarise,
  labelSummary,
  recentSessions,
  normalizeGoal,
  goalProgress,
  weeklyReview,
  streaks,
  UNLABELLED,
} from "./history.js";

const STORAGE_KEYS = Object.freeze({
  settings: "focus-flow:settings",
  sessions: "focus-flow:sessions",
  theme: "focus-flow:theme",
  history: "focus-flow:history",
  goal: "focus-flow:goal",
  ambient: "focus-flow:ambient",
});

const STATS_WINDOW_DAYS = 7;

const THEME_LABELS = Object.freeze({
  dark: { button: "Dark theme", next: "light" },
  light: { button: "Light theme", next: "dark" },
});

function isSecureContext() {
  if (window.isSecureContext) {
    return true;
  }
  const { protocol, hostname } = window.location;
  return (
    protocol === "https:" ||
    hostname === "localhost" ||
    hostname === "127.0.0.1" ||
    hostname === "[::1]"
  );
}

/**
 * Register the service worker so Focus Flow is installable and works offline.
 * Failures are logged locally only; registration never throws and never makes
 * a network report.
 */
export function registerServiceWorker() {
  try {
    if (!("serviceWorker" in navigator)) {
      return;
    }
    if (!isSecureContext()) {
      return;
    }
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch((error) => {
        console.warn("Focus Flow: service worker registration failed", error);
      });
    });
  } catch (error) {
    console.warn("Focus Flow: service worker registration failed", error);
  }
}

function readStorage(key, fallback) {
  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch (error) {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    /* Storage may be unavailable (private mode); the app still works. */
  }
}

function getElements() {
  return {
    display: document.getElementById("timer-display"),
    phaseLabel: document.getElementById("phase-label"),
    announcer: document.getElementById("timer-announcer"),
    sessionCount: document.getElementById("session-count"),
    startPause: document.getElementById("start-pause"),
    reset: document.getElementById("reset"),
    skip: document.getElementById("skip"),
    form: document.getElementById("settings-form"),
    settingsStatus: document.getElementById("settings-status"),
    sessionLabel: document.getElementById("session-label"),
    statsTotalSessions: document.getElementById("stats-total-sessions"),
    statsTotalMinutes: document.getElementById("stats-total-minutes"),
    statsLabels: document.getElementById("stats-labels"),
    statsDays: document.getElementById("stats-days"),
    statsRecent: document.getElementById("stats-recent"),
    statsEmpty: document.getElementById("stats-empty"),
    statsStreak: document.getElementById("stats-streak"),
    statsStreakCurrent: document.getElementById("stats-streak-current"),
    statsStreakLongest: document.getElementById("stats-streak-longest"),
    statsStreakToday: document.getElementById("stats-streak-today"),
    statsReminder: document.getElementById("stats-reminder"),
    statsGoal: document.getElementById("stats-goal"),
    statsGoalTarget: document.getElementById("stats-goal-target"),
    statsGoalFocused: document.getElementById("stats-goal-focused"),
    statsGoalPercent: document.getElementById("stats-goal-percent"),
    statsGoalBar: document.getElementById("stats-goal-bar"),
    statsGoalFill: document.getElementById("stats-goal-fill"),
    statsGoalReached: document.getElementById("stats-goal-reached"),
    weeklyReviewEmpty: document.getElementById("weekly-review-empty"),
    weeklyReviewSummary: document.getElementById("weekly-review-summary"),
    weeklyReviewFocused: document.getElementById("weekly-review-focused"),
    weeklyReviewGoalPart: document.getElementById("weekly-review-goal-part"),
    weeklyReviewTarget: document.getElementById("weekly-review-target"),
    weeklyReviewPercent: document.getElementById("weekly-review-percent"),
    weeklyReviewBar: document.getElementById("weekly-review-bar"),
    weeklyReviewFill: document.getElementById("weekly-review-fill"),
    weeklyReviewReached: document.getElementById("weekly-review-reached"),
    weeklyReviewLabels: document.getElementById("weekly-review-labels"),
    clearGoal: document.getElementById("clear-goal"),
    themeToggle: document.getElementById("theme-toggle"),
    themeToggleLabel: document.getElementById("theme-toggle-label"),
    themeToggleIcon: document.querySelector(".theme-toggle__icon"),
    inputs: {
      work: document.getElementById("work-duration"),
      shortBreak: document.getElementById("short-break-duration"),
      longBreak: document.getElementById("long-break-duration"),
      longBreakInterval: document.getElementById("long-break-interval"),
      sound: document.getElementById("sound-enabled"),
      autoStartBreaks: document.getElementById("auto-start-breaks"),
      goal: document.getElementById("weekly-goal"),
      ambientType: document.getElementById("ambient-type"),
      ambientVolume: document.getElementById("ambient-volume"),
    },
  };
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.style.colorScheme = theme;
}

function playChime() {
  const Ctor = window.AudioContext || window.webkitAudioContext;
  if (!Ctor) {
    return;
  }
  try {
    const context = new Ctor();
    const osc = context.createOscillator();
    const gain = context.createGain();
    osc.type = "sine";
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.25, context.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.6);
    osc.connect(gain).connect(context.destination);
    osc.start();
    osc.stop(context.currentTime + 0.65);
    osc.onended = () => context.close();
  } catch (error) {
    /* Audio is a progressive enhancement; failures are non-fatal. */
  }
}

export function init() {
  const el = getElements();

  const storedSettings = normalizeSettings(
    readStorage(STORAGE_KEYS.settings, DEFAULT_SETTINGS),
  );
  const storedSessions = Number.parseInt(
    readStorage(STORAGE_KEYS.sessions, 0),
    10,
  );

  const storedHistory = readStorage(STORAGE_KEYS.history, []);
  let history = pruneHistory(Array.isArray(storedHistory) ? storedHistory : [], {
    now: Date.now(),
    retentionDays: DEFAULT_RETENTION_DAYS,
  });

  const engine = new TimerEngine(storedSettings);
  engine.completedWorkSessions = Number.isFinite(storedSessions)
    ? Math.max(0, storedSessions)
    : 0;

  let goal = normalizeGoal(readStorage(STORAGE_KEYS.goal, null));
  let goalReached = null;

  let ambient = normalizeAmbient(
    readStorage(STORAGE_KEYS.ambient, DEFAULT_AMBIENT),
  );
  let ambientContext = null;
  let ambientSource = null;
  let ambientGain = null;
  let ambientPlaying = false;

  /**
   * Lazily create the single shared AudioContext on the first user gesture that
   * actually needs sound, mirroring the chime's feature detection. Returns
   * `null` when the Web Audio API is unavailable or the context cannot be
   * created; failures are always non-fatal.
   */
  function ensureAudioContext() {
    if (ambientContext) {
      return ambientContext;
    }
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) {
      return null;
    }
    try {
      ambientContext = new Ctor();
    } catch (error) {
      ambientContext = null;
    }
    return ambientContext;
  }

  function stopAmbient() {
    if (ambientSource) {
      try {
        ambientSource.stop();
      } catch (error) {
        /* Already stopped; ignore. */
      }
      try {
        ambientSource.disconnect();
      } catch (error) {
        /* Already disconnected; ignore. */
      }
      ambientSource = null;
    }
    if (ambientGain) {
      try {
        ambientGain.disconnect();
      } catch (error) {
        /* Already disconnected; ignore. */
      }
      ambientGain = null;
    }
    ambientPlaying = false;
  }

  function startAmbient() {
    if (ambient.type === "off") {
      return;
    }
    const context = ensureAudioContext();
    if (!context) {
      return;
    }
    try {
      if (context.state === "suspended" && typeof context.resume === "function") {
        context.resume().catch(() => {});
      }
      stopAmbient();
      const buffer = createNoiseBuffer(context, ambient.type, { seconds: 4 });
      if (!buffer) {
        return;
      }
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.loop = true;
      const gain = context.createGain();
      gain.gain.value = ambient.volume;
      source.connect(gain).connect(context.destination);
      source.start();
      ambientSource = source;
      ambientGain = gain;
      ambientPlaying = true;
    } catch (error) {
      stopAmbient();
      console.warn("Focus Flow: ambient sound failed", error);
    }
  }

  /** Keep the running loop in sync with the timer: play during the phases the
   * helper allows, and always silence when the timer is not running. */
  function syncAmbient(state) {
    const wanted =
      state.running &&
      shouldPlay({
        phase: state.phase,
        type: ambient.type,
        autoStartBreaks: state.settings.autoStartBreaks,
      });
    if (wanted && !ambientPlaying) {
      startAmbient();
    } else if (!wanted && ambientPlaying) {
      stopAmbient();
    }
  }

  const prefersDark =
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  const initialTheme =
    readStorage(STORAGE_KEYS.theme, prefersDark ? "dark" : "light") === "dark"
      ? "dark"
      : "light";
  applyTheme(initialTheme);
  updateThemeButton(initialTheme);

  function updateThemeButton(theme) {
    const config = THEME_LABELS[theme];
    if (el.themeToggle) {
      el.themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
    }
    if (el.themeToggleLabel) {
      el.themeToggleLabel.textContent = config.button;
    }
    if (el.themeToggleIcon) {
      el.themeToggleIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
  }

  function syncForm(settings) {
    if (el.inputs.work) el.inputs.work.value = String(settings.work);
    if (el.inputs.shortBreak) el.inputs.shortBreak.value = String(settings.shortBreak);
    if (el.inputs.longBreak) el.inputs.longBreak.value = String(settings.longBreak);
    if (el.inputs.longBreakInterval) {
      el.inputs.longBreakInterval.value = String(settings.longBreakInterval);
    }
    if (el.inputs.sound) el.inputs.sound.checked = Boolean(settings.sound);
    if (el.inputs.autoStartBreaks) {
      el.inputs.autoStartBreaks.checked = Boolean(settings.autoStartBreaks);
    }
    if (el.inputs.goal) {
      el.inputs.goal.value = goal.minutes > 0 ? String(goal.minutes) : "";
    }
  }

  function readForm() {
    return normalizeSettings({
      work: el.inputs.work.value,
      shortBreak: el.inputs.shortBreak.value,
      longBreak: el.inputs.longBreak.value,
      longBreakInterval: el.inputs.longBreakInterval.value,
      sound: el.inputs.sound.checked,
      autoStartBreaks: el.inputs.autoStartBreaks.checked,
    });
  }

  function syncAmbientControls() {
    if (el.inputs.ambientType) el.inputs.ambientType.value = ambient.type;
    if (el.inputs.ambientVolume) {
      el.inputs.ambientVolume.value = String(ambient.volume);
    }
  }

  function readAmbientControls() {
    return normalizeAmbient({
      type: el.inputs.ambientType ? el.inputs.ambientType.value : ambient.type,
      volume: el.inputs.ambientVolume
        ? el.inputs.ambientVolume.value
        : ambient.volume,
    });
  }

  /** Persist under `focus-flow:ambient`; selecting `off` removes the key so a
   * silent app leaves no trace. */
  function persistAmbient() {
    if (ambient.type === "off") {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.ambient);
      } catch (error) {
        /* Storage may be unavailable; the in-memory value still applies. */
      }
      return;
    }
    writeStorage(STORAGE_KEYS.ambient, ambient);
  }

  function applyAmbient({ announceChange = false } = {}) {
    const previousType = ambient.type;
    ambient = readAmbientControls();
    persistAmbient();
    if (ambient.type !== previousType || ambient.type === "off") {
      stopAmbient();
    } else if (ambientPlaying && ambientGain) {
      try {
        ambientGain.gain.value = ambient.volume;
      } catch (error) {
        /* Non-fatal; the loop keeps its previous gain. */
      }
    }
    syncAmbient(engine.snapshot());
    if (announceChange) {
      announce(
        ambient.type === "off"
          ? "Ambient sound off."
          : `Ambient sound: ${AMBIENT_LABELS[ambient.type]}.`,
      );
    }
  }

  function announce(message) {
    if (!el.announcer || !message) {
      return;
    }
    el.announcer.textContent = "";
    window.requestAnimationFrame(() => {
      el.announcer.textContent = message;
    });
  }

  let activeLabel = null;
  let announcedStreak = null;

  function labelDisplay(label) {
    return label === UNLABELLED ? "No label" : label;
  }

  function renderLabelChips(summary) {
    if (!el.statsLabels) {
      return;
    }
    const chips = summary.labels.filter(
      (label) => summary.totals[label] && summary.totals[label].sessions > 0,
    );
    if (summary.totals[UNLABELLED] && summary.totals[UNLABELLED].sessions > 0) {
      chips.push(UNLABELLED);
    }
    el.statsLabels.hidden = chips.length === 0;

    const items = chips.map((label) => {
      const item = document.createElement("li");

      const button = document.createElement("button");
      button.type = "button";
      button.className = "chip";
      button.dataset.label = label;
      button.setAttribute("aria-pressed", String(activeLabel === label));

      const name = document.createElement("span");
      name.className = "chip__label";
      name.textContent = labelDisplay(label);

      const count = document.createElement("span");
      count.className = "chip__count";
      count.textContent = String(summary.totals[label].sessions);

      button.append(name, count);
      button.addEventListener("click", () => {
        activeLabel = activeLabel === label ? null : label;
        renderStats();
        announce(
          activeLabel === null
            ? "Label filter cleared."
            : `Filtered to ${labelDisplay(activeLabel)}.`,
        );
      });

      item.append(button);
      return item;
    });
    el.statsLabels.replaceChildren(...items);
  }

  function renderRecentSessions() {
    if (!el.statsRecent) {
      return;
    }
    const sessions = recentSessions(history, { limit: 5 });
    el.statsRecent.hidden = sessions.length === 0;

    const items = sessions.map((session) => {
      const item = document.createElement("li");
      item.className = "recent-session";

      const date = document.createElement("span");
      date.className = "recent-session__date";
      date.textContent = new Date(session.endedAt).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });

      const label = document.createElement("span");
      label.className = "recent-session__label";
      if (session.label) {
        label.textContent = session.label;
      } else {
        label.textContent = "No label";
        label.classList.add("recent-session__label--muted");
      }

      const minutes = document.createElement("span");
      minutes.className = "recent-session__minutes";
      minutes.textContent = `${Math.round(session.durationSeconds / 60)} min`;

      item.append(date, label, minutes);
      return item;
    });
    el.statsRecent.replaceChildren(...items);
  }

  function streakLabel(days) {
    return days === 1 ? "1 day" : `${days} days`;
  }

  function renderStreak() {
    const info = streaks(history, {
      now: Date.now(),
      weekStartsOn: DEFAULT_WEEK_START,
    });

    if (el.statsStreakCurrent) {
      el.statsStreakCurrent.textContent = streakLabel(info.current);
    }
    if (el.statsStreakLongest) {
      el.statsStreakLongest.textContent = streakLabel(info.longest);
    }
    if (el.statsStreakToday) {
      const noun = info.todayCount === 1 ? "session" : "sessions";
      el.statsStreakToday.textContent =
        `${info.todayCount} ${noun} · ${info.todayMinutes} min`;
    }
    if (el.statsReminder) {
      el.statsReminder.hidden = !(info.todayCount === 0 && goal.minutes > 0);
    }

    if (announcedStreak === null) {
      announcedStreak = info.current;
    } else if (info.current !== announcedStreak) {
      announcedStreak = info.current;
      announce(`Streak: ${streakLabel(info.current)}.`);
    }
  }

  function renderStats() {
    const summary = summarise(history, {
      now: Date.now(),
      days: STATS_WINDOW_DAYS,
      label: activeLabel === null ? undefined : activeLabel,
    });

    if (el.statsTotalSessions) {
      el.statsTotalSessions.textContent = String(summary.totalSessions);
    }
    if (el.statsTotalMinutes) {
      el.statsTotalMinutes.textContent = String(summary.totalMinutes);
    }
    if (el.statsEmpty) {
      el.statsEmpty.hidden = summary.totalSessions > 0;
    }
    if (el.statsDays) {
      el.statsDays.hidden = summary.totalSessions === 0;
      const maxCount = summary.perDay.reduce(
        (max, day) => Math.max(max, day.count),
        0,
      );
      const items = summary.perDay.map((day) => {
        const item = document.createElement("li");
        item.className = "stats-day";
        item.dataset.count = String(day.count);

        const label = document.createElement("span");
        label.className = "stats-day__label";
        label.textContent = day.label;

        const track = document.createElement("span");
        track.className = "stats-day__track";
        const fill = document.createElement("span");
        fill.className = "stats-day__fill";
        fill.style.width = `${maxCount > 0 ? Math.round((day.count / maxCount) * 100) : 0}%`;
        track.append(fill);

        const count = document.createElement("span");
        count.className = "stats-day__count";
        count.textContent = String(day.count);

        item.append(label, track, count);
        return item;
      });
      el.statsDays.replaceChildren(...items);
    }

    renderLabelChips(
      labelSummary(history, { now: Date.now(), days: STATS_WINDOW_DAYS }),
    );
    renderRecentSessions();
    renderStreak();
    renderGoal();
    renderWeeklyReview();
  }

  function currentGoalProgress() {
    return goalProgress(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label: activeLabel === null ? goal.label : activeLabel,
      weekStartsOn: DEFAULT_WEEK_START,
    });
  }

  function noteGoalReached(reached) {
    if (reached === null) {
      goalReached = null;
    } else if (goalReached === null) {
      goalReached = reached;
    } else if (reached && !goalReached) {
      goalReached = true;
      announce("Weekly goal reached.");
    } else if (!reached) {
      goalReached = false;
    }
  }

  function renderGoal() {
    const progress = currentGoalProgress();
    const active = progress.targetMinutes > 0;

    if (el.statsGoal) {
      el.statsGoal.hidden = !active;
    }
    if (!active) {
      goalReached = null;
      return;
    }

    if (el.statsGoalTarget) {
      el.statsGoalTarget.textContent = String(progress.targetMinutes);
    }
    if (el.statsGoalFocused) {
      el.statsGoalFocused.textContent = String(progress.focusedMinutes);
    }
    if (el.statsGoalPercent) {
      el.statsGoalPercent.textContent = String(progress.percent);
    }
    if (el.statsGoalBar) {
      el.statsGoalBar.setAttribute("aria-valuenow", String(progress.percent));
      el.statsGoalBar.setAttribute("aria-valuemin", "0");
      el.statsGoalBar.setAttribute("aria-valuemax", "100");
      el.statsGoalBar.classList.toggle("stats__goal-bar--reached", progress.reached);
    }
    if (el.statsGoalFill) {
      el.statsGoalFill.style.width = `${progress.percent}%`;
    }
    if (el.statsGoalReached) {
      el.statsGoalReached.hidden = !progress.reached;
    }
    if (el.statsGoal) {
      el.statsGoal.classList.toggle("stats__goal--reached", progress.reached);
    }

    noteGoalReached(progress.reached);
  }

  function renderWeeklyReview() {
    const review = weeklyReview(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label: activeLabel === null ? goal.label : activeLabel,
      weekStartsOn: DEFAULT_WEEK_START,
    });

    const hasGoal = review.targetMinutes > 0;
    const hasSessions = review.perLabel.length > 0;

    if (el.weeklyReviewEmpty) {
      el.weeklyReviewEmpty.hidden = hasSessions;
    }
    if (el.weeklyReviewSummary) {
      el.weeklyReviewSummary.hidden = !hasSessions;
    }
    if (el.weeklyReviewFocused) {
      el.weeklyReviewFocused.textContent = String(review.focusedMinutes);
    }
    if (el.weeklyReviewGoalPart) {
      el.weeklyReviewGoalPart.hidden = !hasGoal;
    }
    if (el.weeklyReviewTarget) {
      el.weeklyReviewTarget.textContent = String(review.targetMinutes);
    }
    if (el.weeklyReviewPercent) {
      el.weeklyReviewPercent.textContent = String(review.percent);
    }
    if (el.weeklyReviewBar) {
      el.weeklyReviewBar.hidden = !hasGoal;
      el.weeklyReviewBar.setAttribute("aria-valuenow", String(review.percent));
      el.weeklyReviewBar.setAttribute("aria-valuemin", "0");
      el.weeklyReviewBar.setAttribute("aria-valuemax", "100");
      el.weeklyReviewBar.classList.toggle(
        "weekly-review__bar--reached",
        review.reached,
      );
    }
    if (el.weeklyReviewFill) {
      el.weeklyReviewFill.style.width = `${review.percent}%`;
    }
    if (el.weeklyReviewReached) {
      el.weeklyReviewReached.hidden = !review.reached;
    }
    if (el.weeklyReviewLabels) {
      el.weeklyReviewLabels.hidden = !hasSessions;
      const items = review.perLabel.map((row) => {
        const item = document.createElement("li");
        item.className = "weekly-review__label";

        const name = document.createElement("span");
        name.className = "weekly-review__label-name";
        name.textContent = row.label === UNLABELLED ? "No label" : row.label;

        const track = document.createElement("span");
        track.className = "weekly-review__label-track";
        const fill = document.createElement("span");
        fill.className = "weekly-review__label-fill";
        fill.style.width = `${hasGoal ? row.percentOfTarget : 0}%`;
        track.append(fill);

        const stats = document.createElement("span");
        stats.className = "weekly-review__label-stats";
        stats.textContent = hasGoal
          ? `${row.sessions} · ${row.minutes} min · ${row.percentOfTarget}%`
          : `${row.sessions} · ${row.minutes} min`;

        item.append(name, track, stats);
        return item;
      });
      el.weeklyReviewLabels.replaceChildren(...items);
    }

    noteGoalReached(hasGoal ? review.reached : null);
  }

  function persistGoal() {
    if (goal.minutes > 0) {
      writeStorage(STORAGE_KEYS.goal, goal);
      return;
    }
    try {
      window.localStorage.removeItem(STORAGE_KEYS.goal);
    } catch (error) {
      /* Storage may be unavailable; the in-memory goal still applies. */
    }
  }

  function applyGoal(rawMinutes, { announceChange = false } = {}) {
    const parsed = Number.parseInt(rawMinutes, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      goal = normalizeGoal({ minutes: 0 });
    } else {
      goal = normalizeGoal({
        minutes: parsed,
        label: activeLabel === null ? goal.label : activeLabel,
      });
    }
    persistGoal();
    syncForm(engine.settings);
    goalReached = null;
    renderStats();
    if (announceChange) {
      const progress = currentGoalProgress();
      if (progress.targetMinutes > 0 && progress.reached) {
        announce("Weekly goal reached.");
      } else if (progress.targetMinutes > 0) {
        announce("Weekly goal saved.");
      } else {
        announce("Weekly goal cleared.");
      }
    }
  }

  function render(state, meta = {}) {
    el.display.textContent = formatTime(state.remainingSeconds);
    el.display.dataset.phase = state.phase;
    el.phaseLabel.textContent = state.label;
    el.phaseLabel.dataset.phase = state.phase;
    el.sessionCount.textContent = String(state.completedWorkSessions);
    el.startPause.textContent = state.running ? "Pause" : "Start";
    el.startPause.setAttribute("aria-pressed", String(state.running));

    document.title = `${formatTime(state.remainingSeconds)} · ${state.label} · Focus Flow`;

    if (meta.reason === "phase-complete") {
      const finished =
        meta.previousPhase && PHASE_LABELS[meta.previousPhase]
          ? PHASE_LABELS[meta.previousPhase]
          : "Phase";
      announce(`${finished} finished. ${state.label} ready.`);
      if (state.settings.sound) {
        playChime();
      }
    } else if (meta.reason === "start") {
      announce(`Timer started. ${state.label}.`);
    } else if (meta.reason === "pause") {
      announce(`Timer paused. ${formatTime(state.remainingSeconds)} remaining.`);
    } else if (meta.reason === "reset") {
      announce(`Timer reset. ${state.label}.`);
    } else if (meta.reason === "settings") {
      announce("Settings saved.");
    }
  }

  engine.subscribe((state, meta) => {
    render(state, meta);
    syncAmbient(state);
    if (meta.reason === "phase-complete") {
      writeStorage(STORAGE_KEYS.sessions, state.completedWorkSessions);
      if (meta.previousPhase === PHASES.WORK && meta.skipped === false) {
        const entry = {
          endedAt: new Date().toISOString(),
          phase: PHASES.WORK,
          durationSeconds: state.settings.work * 60,
        };
        if (el.sessionLabel) {
          entry.label = el.sessionLabel.value;
        }
        history = pruneHistory(recordSession(history, entry), {
          now: Date.now(),
          retentionDays: DEFAULT_RETENTION_DAYS,
        });
        writeStorage(STORAGE_KEYS.history, history);
        if (el.sessionLabel) {
          el.sessionLabel.value = "";
        }
        renderStats();
      }
    }
  });

  syncForm(engine.settings);
  syncAmbientControls();
  renderStats();

  let intervalId = null;
  function startClock() {
    if (intervalId === null) {
      intervalId = window.setInterval(() => engine.tick(), 250);
    }
  }
  startClock();

  el.startPause.addEventListener("click", () => engine.toggle());
  el.reset.addEventListener("click", () => engine.reset());
  el.skip.addEventListener("click", () => engine.skip());

  if (el.clearGoal) {
    el.clearGoal.addEventListener("click", () => {
      applyGoal(0, { announceChange: true });
    });
  }

  el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const settings = readForm();
    engine.setSettings(settings);
    writeStorage(STORAGE_KEYS.settings, settings);
    applyGoal(el.inputs.goal ? el.inputs.goal.value : 0, {
      announceChange: true,
    });
    syncForm(engine.settings);
    if (el.settingsStatus) {
      el.settingsStatus.textContent = "Saved.";
      window.setTimeout(() => {
        el.settingsStatus.textContent = "";
      }, 2000);
    }
  });

  if (el.inputs.ambientType) {
    el.inputs.ambientType.addEventListener("change", () => {
      applyAmbient({ announceChange: true });
    });
  }

  if (el.inputs.ambientVolume) {
    el.inputs.ambientVolume.addEventListener("input", () => {
      applyAmbient();
    });
  }

  el.themeToggle.addEventListener("click", () => {
    const current =
      document.documentElement.getAttribute("data-theme") === "dark"
        ? "dark"
        : "light";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    updateThemeButton(next);
    writeStorage(STORAGE_KEYS.theme, next);
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const typing =
      target instanceof HTMLElement &&
      (target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable);
    if (typing) {
      return;
    }
    if (event.code === "Space" || event.key === " ") {
      event.preventDefault();
      engine.toggle();
    } else if (event.key === "r" || event.key === "R") {
      engine.reset();
    } else if (event.key === "s" || event.key === "S") {
      engine.skip();
    }
  });

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      engine.tick();
    }
  });

  return engine;
}

if (typeof document !== "undefined") {
  registerServiceWorker();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
}
