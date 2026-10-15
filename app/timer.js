/**
 * Focus Flow timer engine.
 *
 * Pure state machine for work / short break / long break cycles. It has no DOM
 * dependencies so it can be reasoned about and tested in isolation. The DOM
 * layer (main.js) subscribes for changes and drives the clock.
 */

export const PHASES = Object.freeze({
  WORK: "work",
  SHORT_BREAK: "shortBreak",
  LONG_BREAK: "longBreak",
});

export const PHASE_LABELS = Object.freeze({
  [PHASES.WORK]: "Work session",
  [PHASES.SHORT_BREAK]: "Short break",
  [PHASES.LONG_BREAK]: "Long break",
});

export const DEFAULT_SETTINGS = Object.freeze({
  work: 25,
  shortBreak: 5,
  longBreak: 15,
  longBreakInterval: 4,
  sound: true,
  autoStartBreaks: true,
});

const LIMITS = Object.freeze({
  work: [1, 180],
  shortBreak: [1, 60],
  longBreak: [1, 120],
  longBreakInterval: [2, 12],
});

export function clampInt(value, min, max, fallback) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, parsed));
}

export function normalizeSettings(raw = {}) {
  const source = { ...DEFAULT_SETTINGS, ...raw };
  return {
    work: clampInt(source.work, ...LIMITS.work, DEFAULT_SETTINGS.work),
    shortBreak: clampInt(
      source.shortBreak,
      ...LIMITS.shortBreak,
      DEFAULT_SETTINGS.shortBreak,
    ),
    longBreak: clampInt(
      source.longBreak,
      ...LIMITS.longBreak,
      DEFAULT_SETTINGS.longBreak,
    ),
    longBreakInterval: clampInt(
      source.longBreakInterval,
      ...LIMITS.longBreakInterval,
      DEFAULT_SETTINGS.longBreakInterval,
    ),
    sound: Boolean(source.sound),
    autoStartBreaks: Boolean(source.autoStartBreaks),
  };
}

export function formatTime(totalSeconds) {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export class TimerEngine {
  constructor(settings = {}, { now = () => Date.now() } = {}) {
    this.settings = normalizeSettings(settings);
    this.now = now;
    this.phase = PHASES.WORK;
    this.completedWorkSessions = 0;
    this.running = false;
    this.remainingSeconds = this.durationFor(this.phase);
    this.listeners = new Set();
    this.endTime = null;
  }

  durationFor(phase) {
    switch (phase) {
      case PHASES.SHORT_BREAK:
        return this.settings.shortBreak * 60;
      case PHASES.LONG_BREAK:
        return this.settings.longBreak * 60;
      case PHASES.WORK:
      default:
        return this.settings.work * 60;
    }
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.snapshot(), { reason: "init" });
    return () => this.listeners.delete(listener);
  }

  snapshot() {
    return {
      phase: this.phase,
      label: PHASE_LABELS[this.phase],
      remainingSeconds: this.remainingSeconds,
      formatted: formatTime(this.remainingSeconds),
      running: this.running,
      completedWorkSessions: this.completedWorkSessions,
      settings: { ...this.settings },
    };
  }

  notify(reason, detail = {}) {
    const state = this.snapshot();
    for (const listener of this.listeners) {
      listener(state, { reason, ...detail });
    }
  }

  setSettings(settings) {
    this.settings = normalizeSettings(settings);
    if (!this.running) {
      this.remainingSeconds = this.durationFor(this.phase);
    }
    this.notify("settings");
  }

  start() {
    if (this.running) {
      return;
    }
    this.running = true;
    this.endTime = this.now() + this.remainingSeconds * 1000;
    this.notify("start");
  }

  pause() {
    if (!this.running) {
      return;
    }
    this.running = false;
    this.endTime = null;
    this.notify("pause");
  }

  toggle() {
    if (this.running) {
      this.pause();
    } else {
      this.start();
    }
  }

  reset() {
    this.running = false;
    this.endTime = null;
    this.remainingSeconds = this.durationFor(this.phase);
    this.notify("reset");
  }

  skip() {
    this.advance({ skipped: true });
  }

  /** Recompute the remaining time from the wall clock. Returns true when the
   * phase completes on this tick. */
  tick() {
    if (!this.running) {
      return false;
    }
    const next = Math.max(0, Math.round((this.endTime - this.now()) / 1000));
    if (next === this.remainingSeconds) {
      return false;
    }
    this.remainingSeconds = next;
    if (next === 0) {
      this.advance({ skipped: false });
      return true;
    }
    this.notify("tick");
    return false;
  }

  nextPhase() {
    if (this.phase === PHASES.WORK) {
      const interval = this.settings.longBreakInterval;
      const dueForLongBreak =
        this.completedWorkSessions > 0 &&
        this.completedWorkSessions % interval === 0;
      return dueForLongBreak ? PHASES.LONG_BREAK : PHASES.SHORT_BREAK;
    }
    return PHASES.WORK;
  }

  advance({ skipped }) {
    const previousPhase = this.phase;
    const wasWork = previousPhase === PHASES.WORK;
    const wasRunning = this.running;

    if (wasWork && !skipped) {
      this.completedWorkSessions += 1;
    }

    this.phase = this.nextPhase();
    this.remainingSeconds = this.durationFor(this.phase);
    this.endTime = null;

    if (skipped) {
      this.running = wasRunning;
    } else if (this.phase === PHASES.WORK) {
      this.running = false;
    } else {
      this.running = Boolean(this.settings.autoStartBreaks);
    }

    if (this.running) {
      this.endTime = this.now() + this.remainingSeconds * 1000;
    }

    this.notify("phase-complete", { previousPhase, skipped });
  }
}
