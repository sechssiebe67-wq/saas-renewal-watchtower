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

const STORAGE_KEYS = Object.freeze({
  settings: "focus-flow:settings",
  sessions: "focus-flow:sessions",
  theme: "focus-flow:theme",
});

const THEME_LABELS = Object.freeze({
  dark: { button: "Dark theme", next: "light" },
  light: { button: "Light theme", next: "dark" },
});

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
    }
  });

  syncForm(engine.settings);

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
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init());
  } else {
    init();
  }
}
