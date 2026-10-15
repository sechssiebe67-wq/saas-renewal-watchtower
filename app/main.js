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
  DEFAULT_AMBIENT,
  normalizeAmbient,
  createNoiseBuffer,
  shouldPlay,
} from "./ambient.js";

import {
  SUPPORTED_LOCALES,
  LOCALE_LABELS,
  DEFAULT_LOCALE,
  normalizeLocale,
  createTranslator,
  formatNumber,
  formatWeekday,
  formatMonth,
  formatDuration,
  pluralise,
} from "./i18n.js";

import {
  DEFAULT_RETENTION_DAYS,
  DEFAULT_WEEK_START,
  WEEK_START_OPTIONS,
  normalizeWeekStart,
  recordSession,
  pruneHistory,
  summarise,
  labelSummary,
  recentSessions,
  normalizeGoal,
  goalProgress,
  normalizeDailyGoal,
  dailyGoalProgress,
  weeklyReview,
  weeklyReviewCsv,
  streaks,
  UNLABELLED,
} from "./history.js";

const STORAGE_KEYS = Object.freeze({
  settings: "focus-flow:settings",
  sessions: "focus-flow:sessions",
  theme: "focus-flow:theme",
  history: "focus-flow:history",
  goal: "focus-flow:goal",
  dailyGoal: "focus-flow:daily-goal",
  ambient: "focus-flow:ambient",
  locale: "focus-flow:locale",
  weekStart: "focus-flow:week-start",
});

const STATS_WINDOW_DAYS = 7;

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
    statsGoalBreakdownTitle: document.getElementById(
      "stats-goal-breakdown-title",
    ),
    statsGoalBreakdown: document.getElementById("stats-goal-breakdown"),
    statsDailyGoal: document.getElementById("stats-daily-goal"),
    statsDailyGoalTarget: document.getElementById("stats-daily-goal-target"),
    statsDailyGoalFocused: document.getElementById("stats-daily-goal-focused"),
    statsDailyGoalPercent: document.getElementById("stats-daily-goal-percent"),
    statsDailyGoalBar: document.getElementById("stats-daily-goal-bar"),
    statsDailyGoalFill: document.getElementById("stats-daily-goal-fill"),
    statsDailyGoalReached: document.getElementById("stats-daily-goal-reached"),
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
    reviewExport: document.getElementById("review-export"),
    clearGoal: document.getElementById("clear-goal"),
    clearDailyGoal: document.getElementById("clear-daily-goal"),
    locale: document.getElementById("locale"),
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
      dailyGoal: document.getElementById("daily-goal"),
      ambientType: document.getElementById("ambient-type"),
      ambientVolume: document.getElementById("ambient-volume"),
      weekStart: document.getElementById("week-start"),
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

  let locale = normalizeLocale(readStorage(STORAGE_KEYS.locale, DEFAULT_LOCALE));
  let t = createTranslator(locale);

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
  let dailyGoal = normalizeDailyGoal(readStorage(STORAGE_KEYS.dailyGoal, null));
  let dailyGoalReached = null;

  let weekStartsOn = normalizeWeekStart(
    readStorage(STORAGE_KEYS.weekStart, DEFAULT_WEEK_START),
  );

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

  function updateThemeButton(theme) {
    if (el.themeToggle) {
      el.themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
    }
    if (el.themeToggleLabel) {
      el.themeToggleLabel.textContent =
        theme === "dark" ? t("theme.dark") : t("theme.light");
    }
    if (el.themeToggleIcon) {
      el.themeToggleIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
  }

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark"
      ? "dark"
      : "light";
  }

  /** Translate every static `data-i18n` / `data-i18n-attr` hook in the shell.
   * The English source strings stay in `index.html` as the no-JS fallback. */
  function applyStaticTranslations() {
    document.documentElement.setAttribute("lang", locale);
    document.title = t("app.title");
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = t(node.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-attr]").forEach((node) => {
      const spec = node.getAttribute("data-i18n-attr");
      for (const pair of spec.split(";")) {
        const separator = pair.indexOf(":");
        if (separator === -1) {
          continue;
        }
        const attr = pair.slice(0, separator).trim();
        const key = pair.slice(separator + 1).trim();
        if (attr && key) {
          node.setAttribute(attr, t(key));
        }
      }
    });
  }

  function populateLocaleSelect() {
    if (!el.locale) {
      return;
    }
    const options = SUPPORTED_LOCALES.map((id) => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = LOCALE_LABELS[id] || id;
      return option;
    });
    el.locale.replaceChildren(...options);
    el.locale.value = locale;
  }

  /** Persist under `focus-flow:locale`; keeping the default removes the key so
   * a default install leaves no trace, matching the ambient-sound behaviour. */
  function persistLocale() {
    if (locale === DEFAULT_LOCALE) {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.locale);
      } catch (error) {
        /* Storage may be unavailable; the in-memory locale still applies. */
      }
      return;
    }
    writeStorage(STORAGE_KEYS.locale, locale);
  }

  /** Apply a locale immediately: persist it, re-render every visible string,
   * and (optionally) announce the change once through the live region. */
  function applyLocale(raw, { announceChange = false } = {}) {
    locale = normalizeLocale(raw);
    t = createTranslator(locale);
    persistLocale();
    if (el.locale) {
      el.locale.value = locale;
    }
    applyStaticTranslations();
    updateThemeButton(currentTheme());
    render(engine.snapshot(), { reason: "locale" });
    renderStats();
    if (announceChange) {
      announce(t("announce.locale", { language: LOCALE_LABELS[locale] }));
    }
  }

  function syncWeekStartControl() {
    if (el.inputs.weekStart) {
      el.inputs.weekStart.value = String(weekStartsOn);
    }
  }

  /** The catalog key for the label of a resolved first day of the week. */
  function weekStartLabelKey(value) {
    const option = WEEK_START_OPTIONS.find((item) => item.value === value);
    return option ? option.labelKey : "settings.weekStartMonday";
  }

  /** Persist under `focus-flow:week-start`; keeping the default Monday removes
   * the key so a default install leaves no trace, matching the ambient-sound
   * and locale behaviour. */
  function persistWeekStart() {
    if (weekStartsOn === DEFAULT_WEEK_START) {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.weekStart);
      } catch (error) {
        /* Storage may be unavailable; the in-memory value still applies. */
      }
      return;
    }
    writeStorage(STORAGE_KEYS.weekStart, weekStartsOn);
  }

  /** Apply a first day of the week immediately: persist it, re-render the
   * week-scoped panels, and (optionally) announce the change once. */
  function applyWeekStart(raw, { announceChange = false } = {}) {
    weekStartsOn = normalizeWeekStart(raw);
    persistWeekStart();
    syncWeekStartControl();
    renderStats();
    if (announceChange) {
      announce(
        t("announce.weekStart", {
          day: t(weekStartLabelKey(weekStartsOn)),
        }),
      );
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
    if (el.inputs.dailyGoal) {
      el.inputs.dailyGoal.value =
        dailyGoal.minutes > 0 ? String(dailyGoal.minutes) : "";
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
          ? t("announce.ambientOff")
          : t("announce.ambientOn", { type: t(`ambient.${ambient.type}`) }),
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
  let announcedBreakdown = false;

  function labelDisplay(label) {
    return label === UNLABELLED ? t("label.unlabelled") : label;
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
      count.textContent = formatNumber(summary.totals[label].sessions, locale);

      button.append(name, count);
      button.addEventListener("click", () => {
        activeLabel = activeLabel === label ? null : label;
        renderStats();
        announce(
          activeLabel === null
            ? t("announce.labelCleared")
            : t("announce.filtered", { label: labelDisplay(activeLabel) }),
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
      const endedAt = new Date(session.endedAt);
      date.textContent = t("stats.recentTimestamp", {
        month: formatMonth(endedAt, locale),
        day: formatNumber(endedAt.getDate(), locale),
      });

      const label = document.createElement("span");
      label.className = "recent-session__label";
      if (session.label) {
        label.textContent = session.label;
      } else {
        label.textContent = t("label.noLabel");
        label.classList.add("recent-session__label--muted");
      }

      const minutes = document.createElement("span");
      minutes.className = "recent-session__minutes";
      minutes.textContent = formatDuration(
        Math.round(session.durationSeconds / 60),
        locale,
      );

      item.append(date, label, minutes);
      return item;
    });
    el.statsRecent.replaceChildren(...items);
  }

  function streakLabel(days) {
    const template = pluralise(
      days,
      { one: t("streak.daysOne"), other: t("streak.daysMany") },
      locale,
    );
    return template.replace("{count}", formatNumber(days, locale));
  }

  function renderStreak() {
    const info = streaks(history, {
      now: Date.now(),
      weekStartsOn,
    });

    if (el.statsStreakCurrent) {
      el.statsStreakCurrent.textContent = streakLabel(info.current);
    }
    if (el.statsStreakLongest) {
      el.statsStreakLongest.textContent = streakLabel(info.longest);
    }
    if (el.statsStreakToday) {
      el.statsStreakToday.textContent = t(
        info.todayCount === 1 ? "stats.todayOne" : "stats.todayMany",
        {
          count: formatNumber(info.todayCount, locale),
          minutes: formatNumber(info.todayMinutes, locale),
        },
      );
    }
    if (el.statsReminder) {
      el.statsReminder.hidden = !(info.todayCount === 0 && goal.minutes > 0);
    }

    if (announcedStreak === null) {
      announcedStreak = info.current;
    } else if (info.current !== announcedStreak) {
      announcedStreak = info.current;
      announce(t("announce.streak", { value: streakLabel(info.current) }));
    }
  }

  function renderStats() {
    const summary = summarise(history, {
      now: Date.now(),
      days: STATS_WINDOW_DAYS,
      label: activeLabel === null ? undefined : activeLabel,
    });

    if (el.statsTotalSessions) {
      el.statsTotalSessions.textContent = formatNumber(
        summary.totalSessions,
        locale,
      );
    }
    if (el.statsTotalMinutes) {
      el.statsTotalMinutes.textContent = formatNumber(summary.totalMinutes, locale);
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
        item.setAttribute(
          "aria-label",
          t("stats.dayLabel", {
            weekday: formatWeekday(day.date, locale),
            count: formatNumber(day.count, locale),
          }),
        );

        const label = document.createElement("span");
        label.className = "stats-day__label";
        label.textContent = formatWeekday(day.date, locale);

        const track = document.createElement("span");
        track.className = "stats-day__track";
        const fill = document.createElement("span");
        fill.className = "stats-day__fill";
        fill.style.width = `${maxCount > 0 ? Math.round((day.count / maxCount) * 100) : 0}%`;
        track.append(fill);

        const count = document.createElement("span");
        count.className = "stats-day__count";
        count.textContent = formatNumber(day.count, locale);

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
    renderDailyGoal();
    renderWeeklyReview();
  }

  function currentGoalProgress() {
    return goalProgress(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label: activeLabel === null ? goal.label : activeLabel,
      weekStartsOn,
    });
  }

  function noteGoalReached(reached) {
    if (reached === null) {
      goalReached = null;
    } else if (goalReached === null) {
      goalReached = reached;
    } else if (reached && !goalReached) {
      goalReached = true;
      announce(t("announce.goalReached"));
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
      hideGoalBreakdown();
      return;
    }

    if (el.statsGoalTarget) {
      el.statsGoalTarget.textContent = formatNumber(progress.targetMinutes, locale);
    }
    if (el.statsGoalFocused) {
      el.statsGoalFocused.textContent = formatNumber(progress.focusedMinutes, locale);
    }
    if (el.statsGoalPercent) {
      el.statsGoalPercent.textContent = formatNumber(progress.percent, locale);
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

    renderGoalBreakdown();
    noteGoalReached(progress.reached);
  }

  function currentDailyGoalProgress() {
    return dailyGoalProgress(history, {
      now: Date.now(),
      minutes: dailyGoal.minutes,
      label: activeLabel === null ? dailyGoal.label : activeLabel,
    });
  }

  /** Announce the daily goal reached state exactly once per completion, the
   * same way the weekly goal is tracked. */
  function noteDailyGoalReached(reached) {
    if (reached === null) {
      dailyGoalReached = null;
    } else if (dailyGoalReached === null) {
      dailyGoalReached = reached;
    } else if (reached && !dailyGoalReached) {
      dailyGoalReached = true;
      announce(t("announce.dailyGoalReached"));
    } else if (!reached) {
      dailyGoalReached = false;
    }
  }

  /**
   * Render the daily goal row from the pure `dailyGoalProgress` helper. The row
   * is hidden when no daily goal is set; otherwise it shows the target, today's
   * focused minutes, a percentage, and a `progressbar`, and switches to the
   * reached state once the target is met.
   */
  function renderDailyGoal() {
    const progress = currentDailyGoalProgress();
    const active = progress.targetMinutes > 0;

    if (el.statsDailyGoal) {
      el.statsDailyGoal.hidden = !active;
    }
    if (!active) {
      dailyGoalReached = null;
      return;
    }

    if (el.statsDailyGoalTarget) {
      el.statsDailyGoalTarget.textContent = formatNumber(
        progress.targetMinutes,
        locale,
      );
    }
    if (el.statsDailyGoalFocused) {
      el.statsDailyGoalFocused.textContent = formatNumber(
        progress.focusedMinutes,
        locale,
      );
    }
    if (el.statsDailyGoalPercent) {
      el.statsDailyGoalPercent.textContent = formatNumber(
        progress.percent,
        locale,
      );
    }
    if (el.statsDailyGoalBar) {
      el.statsDailyGoalBar.setAttribute("aria-valuenow", String(progress.percent));
      el.statsDailyGoalBar.setAttribute("aria-valuemin", "0");
      el.statsDailyGoalBar.setAttribute("aria-valuemax", "100");
      el.statsDailyGoalBar.classList.toggle(
        "stats__goal-bar--reached",
        progress.reached,
      );
    }
    if (el.statsDailyGoalFill) {
      el.statsDailyGoalFill.style.width = `${progress.percent}%`;
    }
    if (el.statsDailyGoalReached) {
      el.statsDailyGoalReached.hidden = !progress.reached;
    }
    if (el.statsDailyGoal) {
      el.statsDailyGoal.classList.toggle(
        "stats__goal--reached",
        progress.reached,
      );
    }

    noteDailyGoalReached(progress.reached);
  }

  /** Hide the per-label breakdown and let it announce again when it returns. */
  function hideGoalBreakdown() {
    if (el.statsGoalBreakdown) {
      el.statsGoalBreakdown.hidden = true;
      el.statsGoalBreakdown.replaceChildren();
    }
    if (el.statsGoalBreakdownTitle) {
      el.statsGoalBreakdownTitle.hidden = true;
    }
    announcedBreakdown = false;
  }

  /**
   * Render the current week's per-label breakdown inside the existing Weekly
   * goal row. The rows come from the pure `weeklyReview` helper (already sorted
   * by minutes descending then label ascending), so no new storage or network
   * access is involved. Labelled and `(unlabelled)` entries are both shown, the
   * existing label filter scopes the list, and the breakdown is hidden — and
   * reset so it can announce again — when the week has no label rows.
   */
  function renderGoalBreakdown() {
    if (!el.statsGoalBreakdown) {
      return;
    }

    const review = currentWeeklyReview();
    const rows = review.perLabel;
    const visible = rows.length > 0;

    el.statsGoalBreakdown.hidden = !visible;
    if (el.statsGoalBreakdownTitle) {
      el.statsGoalBreakdownTitle.hidden = !visible;
    }

    if (!visible) {
      el.statsGoalBreakdown.replaceChildren();
      announcedBreakdown = false;
      return;
    }

    const items = rows.map((row) => {
      const item = document.createElement("li");
      item.className = "stats__goal-label";

      const name = document.createElement("span");
      name.className = "stats__goal-label-name";
      name.textContent = labelDisplay(row.label);

      const stats = document.createElement("span");
      stats.className = "stats__goal-label-stats";
      stats.textContent = t("stats.goalLabelStats", {
        minutes: formatDuration(row.minutes, locale),
        percent: formatNumber(row.percentOfTarget, locale),
      });

      item.append(name, stats);
      return item;
    });
    el.statsGoalBreakdown.replaceChildren(...items);

    if (!announcedBreakdown) {
      announcedBreakdown = true;
      if (review.scoped) {
        const row = rows[0];
        announce(
          t("announce.goalBreakdownScoped", {
            label: labelDisplay(row.label),
            minutes: formatDuration(row.minutes, locale),
          }),
        );
      } else {
        const summaryTemplate = pluralise(
          rows.length,
          {
            one: t("stats.goalBreakdownOne"),
            other: t("stats.goalBreakdownMany"),
          },
          locale,
        );
        const summary = summaryTemplate.replace(
          "{count}",
          formatNumber(rows.length, locale),
        );
        announce(t("announce.goalBreakdown", { summary }));
      }
    }
  }

  /** The current week's review for the active goal / label / week-start. */
  function currentWeeklyReview() {
    return weeklyReview(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label: activeLabel === null ? goal.label : activeLabel,
      weekStartsOn,
    });
  }

  /** Format a timestamp as a local `YYYY-MM-DD` calendar key. */
  function localDateKey(timestamp) {
    const date = new Date(timestamp);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  /**
   * Build the weekly review CSV with the pure helper and hand it to the browser
   * as a `Blob` object URL. The download is entirely local: no request is made,
   * no storage is written, and the object URL is revoked immediately after the
   * download starts.
   */
  function exportWeeklyReview() {
    const review = currentWeeklyReview();
    if (review.perLabel.length === 0) {
      return;
    }
    const csv = weeklyReviewCsv(review, {
      locale,
      unlabelled: t("label.unlabelled"),
    });
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `focus-flow-week-${localDateKey(review.weekStart)}.csv`;
    link.rel = "noopener";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    announce(t("review.exported"));
  }

  function renderWeeklyReview() {
    const review = currentWeeklyReview();

    const hasGoal = review.targetMinutes > 0;
    const hasSessions = review.perLabel.length > 0;

    if (el.reviewExport) {
      el.reviewExport.disabled = !hasSessions;
    }

    if (el.weeklyReviewEmpty) {
      el.weeklyReviewEmpty.hidden = hasSessions;
    }
    if (el.weeklyReviewSummary) {
      el.weeklyReviewSummary.hidden = !hasSessions;
    }
    if (el.weeklyReviewFocused) {
      el.weeklyReviewFocused.textContent = formatNumber(
        review.focusedMinutes,
        locale,
      );
    }
    if (el.weeklyReviewGoalPart) {
      el.weeklyReviewGoalPart.hidden = !hasGoal;
    }
    if (el.weeklyReviewTarget) {
      el.weeklyReviewTarget.textContent = formatNumber(review.targetMinutes, locale);
    }
    if (el.weeklyReviewPercent) {
      el.weeklyReviewPercent.textContent = formatNumber(review.percent, locale);
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
        name.textContent = labelDisplay(row.label);

        const track = document.createElement("span");
        track.className = "weekly-review__label-track";
        const fill = document.createElement("span");
        fill.className = "weekly-review__label-fill";
        fill.style.width = `${hasGoal ? row.percentOfTarget : 0}%`;
        track.append(fill);

        const stats = document.createElement("span");
        stats.className = "weekly-review__label-stats";
        stats.textContent = t(
          hasGoal ? "review.labelStatsWithGoal" : "review.labelStats",
          {
            sessions: formatNumber(row.sessions, locale),
            minutes: formatNumber(row.minutes, locale),
            percent: formatNumber(row.percentOfTarget, locale),
          },
        );

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
        announce(t("announce.goalReached"));
      } else if (progress.targetMinutes > 0) {
        announce(t("announce.goalSaved"));
      } else {
        announce(t("announce.goalCleared"));
      }
    }
  }

  /** Persist under `focus-flow:daily-goal`; a `0`/empty goal removes the key so
   * a default install leaves no trace. */
  function persistDailyGoal() {
    if (dailyGoal.minutes > 0) {
      writeStorage(STORAGE_KEYS.dailyGoal, dailyGoal);
      return;
    }
    try {
      window.localStorage.removeItem(STORAGE_KEYS.dailyGoal);
    } catch (error) {
      /* Storage may be unavailable; the in-memory goal still applies. */
    }
  }

  function applyDailyGoal(rawMinutes, { announceChange = false } = {}) {
    const parsed = Number.parseInt(rawMinutes, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      dailyGoal = normalizeDailyGoal({ minutes: 0 });
    } else {
      dailyGoal = normalizeDailyGoal({
        minutes: parsed,
        label: activeLabel === null ? dailyGoal.label : activeLabel,
      });
    }
    persistDailyGoal();
    syncForm(engine.settings);
    dailyGoalReached = null;
    renderStats();
    if (announceChange) {
      const progress = currentDailyGoalProgress();
      if (progress.targetMinutes > 0 && progress.reached) {
        announce(t("announce.dailyGoalReached"));
      } else if (progress.targetMinutes > 0) {
        announce(t("announce.dailyGoalSaved"));
      } else {
        announce(t("announce.dailyGoalCleared"));
      }
    }
  }

  function render(state, meta = {}) {
    const phaseName = t(`phase.${state.phase}`);
    el.display.textContent = formatTime(state.remainingSeconds);
    el.display.dataset.phase = state.phase;
    el.phaseLabel.textContent = phaseName;
    el.phaseLabel.dataset.phase = state.phase;
    el.sessionCount.textContent = String(state.completedWorkSessions);
    el.startPause.textContent = t(
      state.running ? "controls.pause" : "controls.start",
    );
    el.startPause.setAttribute("aria-pressed", String(state.running));

    document.title = `${formatTime(state.remainingSeconds)} · ${phaseName} · Focus Flow`;

    if (meta.reason === "phase-complete") {
      const finished =
        meta.previousPhase && PHASE_LABELS[meta.previousPhase]
          ? t(`phase.${meta.previousPhase}`)
          : t("phase.unknown");
      announce(
        t("announce.phaseFinished", { finished, next: phaseName }),
      );
      if (state.settings.sound) {
        playChime();
      }
    } else if (meta.reason === "start") {
      announce(t("announce.timerStarted", { phase: phaseName }));
    } else if (meta.reason === "pause") {
      announce(
        t("announce.timerPaused", {
          time: formatTime(state.remainingSeconds),
        }),
      );
    } else if (meta.reason === "reset") {
      announce(t("announce.timerReset", { phase: phaseName }));
    } else if (meta.reason === "settings") {
      announce(t("announce.settingsSaved"));
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

  populateLocaleSelect();
  applyStaticTranslations();
  updateThemeButton(initialTheme);
  syncForm(engine.settings);
  syncAmbientControls();
  syncWeekStartControl();
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

  if (el.clearDailyGoal) {
    el.clearDailyGoal.addEventListener("click", () => {
      applyDailyGoal(0, { announceChange: true });
    });
  }

  el.form.addEventListener("submit", (event) => {
    event.preventDefault();
    const settings = readForm();
    engine.setSettings(settings);
    writeStorage(STORAGE_KEYS.settings, settings);
    const nextGoal = el.inputs.goal ? el.inputs.goal.value : 0;
    const nextDailyGoal = el.inputs.dailyGoal ? el.inputs.dailyGoal.value : 0;
    applyGoal(nextGoal, { announceChange: true });
    applyDailyGoal(nextDailyGoal, { announceChange: true });
    syncForm(engine.settings);
    if (el.settingsStatus) {
      el.settingsStatus.textContent = t("settings.saved");
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

  if (el.locale) {
    el.locale.addEventListener("change", () => {
      applyLocale(el.locale.value, { announceChange: true });
    });
  }

  if (el.inputs.weekStart) {
    el.inputs.weekStart.addEventListener("change", () => {
      applyWeekStart(el.inputs.weekStart.value, { announceChange: true });
    });
  }

  if (el.reviewExport) {
    el.reviewExport.addEventListener("click", exportWeeklyReview);
  }

  el.themeToggle.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
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
