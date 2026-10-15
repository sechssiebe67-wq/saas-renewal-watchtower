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
  DEFAULT_RETENTION_DAYS,
  recordSession,
  pruneHistory,
  summarise,
  labelSummary,
  recentSessions,
  UNLABELLED,
} from "./history.js";

const STORAGE_KEYS = Object.freeze({
  settings: "focus-flow:settings",
  sessions: "focus-flow:sessions",
  theme: "focus-flow:theme",
  history: "focus-flow:history",
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

  el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const settings = readForm();
    engine.setSettings(settings);
    writeStorage(STORAGE_KEYS.settings, settings);
    syncForm(engine.settings);
    if (el.settingsStatus) {
      el.settingsStatus.textContent = "Saved.";
      window.setTimeout(() => {
        el.settingsStatus.textContent = "";
      }, 2000);
    }
  });

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
