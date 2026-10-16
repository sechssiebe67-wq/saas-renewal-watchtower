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
  recentLabels,
  normalizeGoal,
  goalProgress,
  normalizeDailyGoal,
  dailyGoalProgress,
  dailyReview,
  badgeState,
  weeklyReview,
  goalPace,
  weeklyReviewCsv,
  streaks,
  focusTrend,
  normalizeSessionTags,
  applyAliases,
  backupFileName,
  backupToJson,
  parseBackup,
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
  sessionTags: "focus-flow:session-tags",
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
    sessionLabelSuggestions: document.getElementById(
      "session-label-suggestions",
    ),
    statsTotalSessions: document.getElementById("stats-total-sessions"),
    statsTotalMinutes: document.getElementById("stats-total-minutes"),
    statsLabels: document.getElementById("stats-labels"),
    statsDays: document.getElementById("stats-days"),
    statsTrend: document.getElementById("stats-trend"),
    statsTrendSvg: document.getElementById("stats-trend-svg"),
    statsTrendLine: document.getElementById("stats-trend-line"),
    statsTrendSummary: document.getElementById("stats-trend-summary"),
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
    statsGoalPace: document.getElementById("stats-goal-pace"),
    statsGoalPaceText: document.getElementById("stats-goal-pace-text"),
    statsGoalPaceSignal: document.getElementById("stats-goal-pace-signal"),
    statsDailyGoal: document.getElementById("stats-daily-goal"),
    statsDailyGoalTarget: document.getElementById("stats-daily-goal-target"),
    statsDailyGoalFocused: document.getElementById("stats-daily-goal-focused"),
    statsDailyGoalPercent: document.getElementById("stats-daily-goal-percent"),
    statsDailyGoalBar: document.getElementById("stats-daily-goal-bar"),
    statsDailyGoalFill: document.getElementById("stats-daily-goal-fill"),
    statsDailyGoalReached: document.getElementById("stats-daily-goal-reached"),
    statsDailyBreakdownTitle: document.getElementById(
      "stats-daily-breakdown-title",
    ),
    statsDailyBreakdown: document.getElementById("stats-daily-breakdown"),
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
    backupExport: document.getElementById("backup-export"),
    backupRestore: document.getElementById("backup-restore"),
    backupRestoreFile: document.getElementById("backup-restore-file"),
    backupStatus: document.getElementById("backup-status"),
    clearGoal: document.getElementById("clear-goal"),
    clearDailyGoal: document.getElementById("clear-daily-goal"),
    sessionTagFrom: document.getElementById("session-tag-from"),
    sessionTagTo: document.getElementById("session-tag-to"),
    sessionTagAdd: document.getElementById("session-tag-add"),
    sessionTagsList: document.getElementById("session-tags-list"),
    sessionTagsEmpty: document.getElementById("session-tags-empty"),
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

  let sessionTags = normalizeSessionTags(
    readStorage(STORAGE_KEYS.sessionTags, null),
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
    renderSessionTags();
    render(engine.snapshot(), { reason: "locale" });
    announcedTrend = false;
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
    announcedTrend = false;
    renderStats();
    if (announceChange) {
      announce(
        t("announce.weekStart", {
          day: t(weekStartLabelKey(weekStartsOn)),
        }),
      );
    }
  }

  /** The alias map as a list of `{ from, to }` pairs, for the normaliser. */
  function sessionTagEntries() {
    return Object.entries(sessionTags).map(([from, to]) => ({ from, to }));
  }

  /** Persist under `focus-flow:session-tags`; an empty map removes the key so a
   * default install leaves no trace, matching the other optional preferences. */
  function persistSessionTags() {
    if (Object.keys(sessionTags).length === 0) {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.sessionTags);
      } catch (error) {
        /* Storage may be unavailable; the in-memory map still applies. */
      }
      return;
    }
    writeStorage(STORAGE_KEYS.sessionTags, sessionTags);
  }

  /** Render the current alias map as a list with a remove button per row. */
  function renderSessionTags() {
    if (!el.sessionTagsList) {
      return;
    }
    const entries = sessionTagEntries();
    el.sessionTagsList.hidden = entries.length === 0;
    if (el.sessionTagsEmpty) {
      el.sessionTagsEmpty.hidden = entries.length !== 0;
    }
    const items = entries.map(({ from, to }) => {
      const item = document.createElement("li");
      item.className = "session-tag";

      const text = document.createElement("span");
      text.className = "session-tag__text";
      text.textContent = t("settings.sessionTagsEntry", {
        label: from,
        alias: to,
      });

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "control session-tag__remove";
      remove.textContent = t("settings.sessionTagsRemove");
      remove.setAttribute(
        "aria-label",
        t("settings.sessionTagsRemoveLabel", { label: from }),
      );
      remove.addEventListener("click", () => removeSessionTag(from));

      item.append(text, remove);
      return item;
    });
    el.sessionTagsList.replaceChildren(...items);
  }

  /** Replace the alias map, persist it, and re-render every affected view. */
  function applySessionTags(raw) {
    sessionTags = normalizeSessionTags(raw);
    persistSessionTags();
    renderSessionTags();
    if (el.sessionLabelSuggestions && !el.sessionLabelSuggestions.hidden) {
      renderLabelSuggestions();
    }
    announcedTrend = false;
    renderStats();
  }

  /** Add the alias currently typed into the two Settings fields. */
  function addSessionTag(announceChange = true) {
    if (!el.sessionTagFrom || !el.sessionTagTo) {
      return;
    }
    const label = String(el.sessionTagFrom.value || "").trim();
    const alias = String(el.sessionTagTo.value || "").trim();
    if (label.length === 0 || alias.length === 0) {
      announce(t("announce.sessionTagsInvalid"));
      return;
    }
    const entries = sessionTagEntries();
    entries.push({ from: label, to: alias });
    applySessionTags(entries);
    if (el.sessionTagFrom) {
      el.sessionTagFrom.value = "";
    }
    if (el.sessionTagTo) {
      el.sessionTagTo.value = "";
    }
    if (announceChange) {
      announce(t("announce.sessionTagsSaved", { label, alias }));
    }
  }

  /** Drop the alias whose canonical label is `from`. */
  function removeSessionTag(from, announceChange = true) {
    applySessionTags(sessionTagEntries().filter((entry) => entry.from !== from));
    if (announceChange) {
      announce(
        Object.keys(sessionTags).length === 0
          ? t("announce.sessionTagsCleared", { label: from })
          : t("announce.sessionTagsRemoved", { label: from }),
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
  let announcedDailyBreakdown = false;
  let announcedGoalPace = false;
  let announcedGoalPaceReached = false;
  let announcedTrend = false;
  let lastBadgeValue;

  function labelDisplay(label) {
    return label === UNLABELLED ? t("label.unlabelled") : label;
  }

  /** How many previously used labels the session-label field suggests. */
  const LABEL_SUGGESTION_LIMIT = 8;
  let labelSuggestions = [];
  let activeSuggestion = -1;

  /** Hide the autocomplete list and reset its state. Safe to call at any time. */
  function closeLabelSuggestions() {
    labelSuggestions = [];
    activeSuggestion = -1;
    if (el.sessionLabelSuggestions) {
      el.sessionLabelSuggestions.hidden = true;
      el.sessionLabelSuggestions.replaceChildren();
    }
    if (el.sessionLabel) {
      el.sessionLabel.setAttribute("aria-expanded", "false");
      el.sessionLabel.removeAttribute("aria-activedescendant");
    }
  }

  /** Build the `<li role="option">` items for the current suggestion labels. */
  function renderLabelSuggestionItems(labels) {
    return labels.map((label, index) => {
      const item = document.createElement("li");
      item.id = `session-label-option-${index}`;
      item.className = "label-suggestion";
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", "false");
      item.dataset.label = label;
      item.textContent = label;
      /* Keep focus on the input so the click accepts without a blur race. */
      item.addEventListener("mousedown", (event) => event.preventDefault());
      item.addEventListener("click", () => acceptLabelSuggestion(index));
      return item;
    });
  }

  /**
   * Populate the suggestion list from the already-local history. When the user
   * has typed a partial label the list narrows to matching suggestions; the
   * free-text value is never changed here, so typing an unknown label still
   * works exactly as before. The list stays hidden when there is nothing to
   * suggest, so a fresh install shows no autocomplete at all.
   */
  function renderLabelSuggestions() {
    if (!el.sessionLabelSuggestions || !el.sessionLabel) {
      return;
    }
    const query = String(el.sessionLabel.value || "").trim().toLowerCase();
    const labels = recentLabels(history, {
      limit: LABEL_SUGGESTION_LIMIT,
      tags: sessionTags,
    });
    const suggestions = query
      ? labels.filter(
          (label) =>
            label.toLowerCase().includes(query) &&
            label.toLowerCase() !== query,
        )
      : labels;
    if (suggestions.length === 0) {
      closeLabelSuggestions();
      return;
    }
    labelSuggestions = suggestions;
    activeSuggestion = -1;
    el.sessionLabelSuggestions.replaceChildren(
      ...renderLabelSuggestionItems(suggestions),
    );
    el.sessionLabelSuggestions.hidden = false;
    el.sessionLabel.setAttribute("aria-expanded", "true");
    el.sessionLabel.removeAttribute("aria-activedescendant");
  }

  /** Move the highlight to `index` (wrapping) and expose it to assistive tech. */
  function setActiveSuggestion(index) {
    if (!el.sessionLabelSuggestions || !el.sessionLabel) {
      return;
    }
    const items = Array.from(el.sessionLabelSuggestions.children);
    if (items.length === 0) {
      return;
    }
    const next = ((index % items.length) + items.length) % items.length;
    activeSuggestion = next;
    items.forEach((item, position) => {
      const selected = position === next;
      item.setAttribute("aria-selected", String(selected));
      item.classList.toggle("label-suggestion--active", selected);
    });
    const activeItem = items[next];
    if (activeItem) {
      el.sessionLabel.setAttribute("aria-activedescendant", activeItem.id);
    }
  }

  /** Fill the input with a suggestion, close the list, and announce it once. */
  function acceptLabelSuggestion(index) {
    if (index < 0 || index >= labelSuggestions.length) {
      return;
    }
    const label = labelSuggestions[index];
    if (el.sessionLabel) {
      el.sessionLabel.value = label;
    }
    closeLabelSuggestions();
    announce(t("announce.labelSuggestion", { label }));
  }

  /** Keyboard handling for the listbox; falls through for plain free text. */
  function handleLabelSuggestionKeydown(event) {
    if (!el.sessionLabelSuggestions || el.sessionLabelSuggestions.hidden) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveSuggestion(activeSuggestion + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveSuggestion(activeSuggestion - 1);
    } else if (event.key === "Enter" || event.key === "Tab") {
      if (activeSuggestion >= 0) {
        event.preventDefault();
        acceptLabelSuggestion(activeSuggestion);
      }
    } else if (event.key === "Escape") {
      event.preventDefault();
      closeLabelSuggestions();
    }
  }

  function wireLabelSuggestions() {
    if (!el.sessionLabel) {
      return;
    }
    el.sessionLabel.addEventListener("focus", () => {
      renderLabelSuggestions();
    });
    el.sessionLabel.addEventListener("input", () => {
      renderLabelSuggestions();
    });
    el.sessionLabel.addEventListener("keydown", handleLabelSuggestionKeydown);
    el.sessionLabel.addEventListener("blur", () => {
      window.setTimeout(() => {
        if (document.activeElement !== el.sessionLabel) {
          closeLabelSuggestions();
        }
      }, 150);
    });
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
        announcedTrend = false;
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
    const sessions = recentSessions(history, { limit: 5, tags: sessionTags });
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
      tags: sessionTags,
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

  const TREND_VIEW_WIDTH = 280;
  const TREND_VIEW_HEIGHT = 60;
  const TREND_VIEW_PADDING = 4;

  /**
   * Build the SVG `points` attribute for the trend sparkline from the pure
   * `focusTrend` result. The x-axis spaces the days evenly and the y-axis maps
   * each day's minutes into the view box, so the shape of the week is visible
   * at a glance. A `0`-minute day sits on the baseline and an all-zero window
   * is a flat line. Pure geometry: no storage and no network access.
   */
  function trendPointsAttribute(points, max) {
    const count = points.length;
    if (count === 0) {
      return "";
    }
    const usableWidth = TREND_VIEW_WIDTH - TREND_VIEW_PADDING * 2;
    const usableHeight = TREND_VIEW_HEIGHT - TREND_VIEW_PADDING * 2;
    const peak = max > 0 ? max : 1;
    const step = count > 1 ? usableWidth / (count - 1) : 0;
    return points
      .map((point, index) => {
        const x =
          count > 1
            ? TREND_VIEW_PADDING + index * step
            : TREND_VIEW_PADDING + usableWidth / 2;
        const ratio = Math.max(0, Math.min(1, point.minutes / peak));
        const y = TREND_VIEW_PADDING + usableHeight - ratio * usableHeight;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(" ");
  }

  /**
   * Render the **7-day focus trend sparkline** inside the Stats panel from the
   * pure `focusTrend` helper. It draws the daily focused minutes as an inline
   * SVG polyline, sets the accessible name and the `visually-hidden` summary
   * (highest day, lowest day, and total) from the bundled catalog, and
   * announces the trend once through the existing live region on first render
   * or after a filter / language / week-start change. The section is hidden
   * (matching the `stats.empty` behaviour) when the trailing window has no
   * completed work sessions. It respects the active label filter and the
   * `tags` alias map, reads only the existing `focus-flow:history` key, and
   * adds no new storage key, no network request, and no third-party dependency.
   */
  function renderFocusTrend() {
    if (
      !el.statsTrend ||
      !el.statsTrendSvg ||
      !el.statsTrendLine ||
      !el.statsTrendSummary
    ) {
      return;
    }

    const trend = focusTrend(history, {
      now: Date.now(),
      days: STATS_WINDOW_DAYS,
      label: activeLabel === null ? undefined : activeLabel,
      tags: sessionTags,
    });

    if (trend.empty) {
      el.statsTrend.hidden = true;
      el.statsTrendLine.setAttribute("points", "");
      el.statsTrendSummary.textContent = t("stats.trendEmpty");
      announcedTrend = false;
      return;
    }

    el.statsTrend.hidden = false;
    el.statsTrendSvg.setAttribute("aria-label", t("stats.trendLabel"));
    el.statsTrendLine.setAttribute(
      "points",
      trendPointsAttribute(trend.points, trend.max),
    );

    const highest =
      trend.points.find((point) => point.minutes === trend.max) ||
      trend.points[0];
    const lowest =
      trend.points.find((point) => point.minutes === trend.min) ||
      trend.points[0];
    const highestText = t("stats.trendHighest", {
      minutes: formatDuration(trend.max, locale),
      day: formatWeekday(highest.date, locale),
    });
    const lowestText = t("stats.trendLowest", {
      minutes: formatDuration(trend.min, locale),
      day: formatWeekday(lowest.date, locale),
    });
    const summary = t("stats.trendSummary", {
      highest: highestText,
      lowest: lowestText,
      total: formatDuration(trend.totalMinutes, locale),
    });
    el.statsTrendSummary.textContent = summary;

    if (!announcedTrend) {
      announcedTrend = true;
      announce(t("announce.trend", { summary }));
    }
  }

  function renderStats() {
    const summary = summarise(history, {
      now: Date.now(),
      days: STATS_WINDOW_DAYS,
      label: activeLabel === null ? undefined : activeLabel,
      tags: sessionTags,
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
      labelSummary(history, {
        now: Date.now(),
        days: STATS_WINDOW_DAYS,
        tags: sessionTags,
      }),
    );
    renderRecentSessions();
    renderStreak();
    renderFocusTrend();
    renderGoal();
    renderDailyGoal();
    renderWeeklyReview();
    syncBadge();
  }

  function currentGoalProgress() {
    return goalProgress(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label:
        activeLabel === null
          ? applyAliases(goal.label, sessionTags)
          : activeLabel,
      weekStartsOn,
      tags: sessionTags,
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
      hideGoalPace();
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
    renderGoalPace();
    noteGoalReached(progress.reached);
  }

  function currentDailyGoalProgress() {
    return dailyGoalProgress(history, {
      now: Date.now(),
      minutes: dailyGoal.minutes,
      label:
        activeLabel === null
          ? applyAliases(dailyGoal.label, sessionTags)
          : activeLabel,
      tags: sessionTags,
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
      hideDailyBreakdown();
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

    renderDailyBreakdown();
    noteDailyGoalReached(progress.reached);
  }

  /** Hide the per-label daily breakdown and let it announce again when it
   * returns. */
  function hideDailyBreakdown() {
    if (el.statsDailyBreakdown) {
      el.statsDailyBreakdown.hidden = true;
      el.statsDailyBreakdown.replaceChildren();
    }
    if (el.statsDailyBreakdownTitle) {
      el.statsDailyBreakdownTitle.hidden = true;
    }
    announcedDailyBreakdown = false;
  }

  /** The current day's review for the active daily goal / label / alias map. */
  function currentDailyReview() {
    return dailyReview(history, {
      now: Date.now(),
      goal: {
        minutes: dailyGoal.minutes,
        label:
          activeLabel === null
            ? applyAliases(dailyGoal.label, sessionTags)
            : activeLabel,
      },
      tags: sessionTags,
    });
  }

  /**
   * Render today's per-label breakdown inside the existing Daily goal row. The
   * rows come from the pure `dailyReview` helper (already sorted by minutes
   * descending then label ascending), so no new storage or network access is
   * involved. Labelled and `(unlabelled)` entries are both shown, the existing
   * label filter scopes the list, and the breakdown is hidden — and reset so it
   * can announce again — when today has no label rows.
   */
  function renderDailyBreakdown() {
    if (!el.statsDailyBreakdown) {
      return;
    }

    const review = currentDailyReview();
    const rows = review.perLabel;
    const visible = rows.length > 0;

    el.statsDailyBreakdown.hidden = !visible;
    if (el.statsDailyBreakdownTitle) {
      el.statsDailyBreakdownTitle.hidden = !visible;
    }

    if (!visible) {
      el.statsDailyBreakdown.replaceChildren();
      announcedDailyBreakdown = false;
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
      stats.textContent = t("stats.dailyLabelStats", {
        minutes: formatDuration(row.minutes, locale),
        percent: formatNumber(row.percentOfTarget, locale),
      });

      item.append(name, stats);
      return item;
    });
    el.statsDailyBreakdown.replaceChildren(...items);

    if (!announcedDailyBreakdown) {
      announcedDailyBreakdown = true;
      if (review.scoped) {
        const row = rows[0];
        announce(
          t("announce.dailyBreakdownScoped", {
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
        announce(t("announce.dailyBreakdown", { summary }));
      }
    }
  }

  /**
   * Push the on-device **app badge** to the platform from the pure
   * `badgeState` helper. The feature is detected before any call, so a browser
   * without `setAppBadge` is a no-op and never throws; the badge shows today's
   * remaining focused minutes and is cleared once the daily goal is reached or
   * unset. The state is announced once through the live region only when it
   * actually changes. No storage key and no network request is involved.
   */
  function syncBadge() {
    if (
      typeof navigator === "undefined" ||
      typeof navigator.setAppBadge !== "function"
    ) {
      return;
    }
    const value = badgeState({
      goal: dailyGoal,
      review: currentDailyReview(),
    });
    if (value === lastBadgeValue) {
      return;
    }
    lastBadgeValue = value;
    try {
      if (value === null) {
        if (typeof navigator.clearAppBadge === "function") {
          const clearing = navigator.clearAppBadge();
          if (clearing && typeof clearing.catch === "function") {
            clearing.catch(() => {});
          }
        }
        return;
      }
      const setting = navigator.setAppBadge(value);
      if (setting && typeof setting.catch === "function") {
        setting.catch(() => {});
      }
    } catch (error) {
      return;
    }
    announce(t("announce.badge", { minutes: formatDuration(value, locale) }));
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

  /** Hide the pace projection and let it announce again when it returns. */
  function hideGoalPace() {
    if (el.statsGoalPace) {
      el.statsGoalPace.hidden = true;
      el.statsGoalPace.classList.remove(
        "stats__goal-pace--on-track",
        "stats__goal-pace--behind",
      );
    }
    if (el.statsGoalPaceText) {
      el.statsGoalPaceText.textContent = "";
    }
    if (el.statsGoalPaceSignal) {
      el.statsGoalPaceSignal.textContent = "";
    }
    announcedGoalPace = false;
    announcedGoalPaceReached = false;
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

  /**
   * Render the forward-looking **weekly goal pace projection** under the
   * per-label weekly breakdown, using the pure `goalPace` helper on the same
   * `weeklyReview` result. It shows the rounded per-day pace needed for the
   * remaining local calendar days (today included) plus a neutral on-track /
   * behind-pace signal, and hides itself when no goal is set. It respects the
   * active label filter (through `currentWeeklyReview`) and the **Week starts
   * on** preference, reads only the existing history and goal keys, and
   * announces itself once through the live region when it first appears or the
   * goal is reached.
   */
  function renderGoalPace() {
    if (!el.statsGoalPace) {
      return;
    }

    const pace = goalPace(currentWeeklyReview(), {
      now: Date.now(),
      weekStart: weekStartsOn,
    });

    if (!pace) {
      hideGoalPace();
      return;
    }

    const daysTemplate = pluralise(
      pace.remainingDays,
      {
        one: t("stats.goalPaceDaysOne"),
        other: t("stats.goalPaceDaysMany"),
      },
      locale,
    );
    const days = daysTemplate.replace(
      "{count}",
      formatNumber(pace.remainingDays, locale),
    );
    const line = t("stats.goalPaceLine", {
      minutes: formatDuration(pace.perDayMinutes, locale),
      days,
    });
    const signal = t(
      pace.onTrack ? "stats.goalPaceOnTrack" : "stats.goalPaceBehind",
    );

    if (el.statsGoalPaceText) {
      el.statsGoalPaceText.textContent = line;
    }
    if (el.statsGoalPaceSignal) {
      el.statsGoalPaceSignal.textContent = signal;
    }

    el.statsGoalPace.hidden = false;
    el.statsGoalPace.classList.toggle(
      "stats__goal-pace--on-track",
      pace.onTrack,
    );
    el.statsGoalPace.classList.toggle(
      "stats__goal-pace--behind",
      !pace.onTrack,
    );

    const reached = pace.remainingMinutes === 0;
    if (!announcedGoalPace) {
      announcedGoalPace = true;
      announcedGoalPaceReached = reached;
      announce(t("announce.goalPace", { summary: `${line} — ${signal}` }));
    } else if (reached && !announcedGoalPaceReached) {
      announcedGoalPaceReached = true;
      announce(t("announce.goalPace", { summary: `${line} — ${signal}` }));
    } else if (!reached) {
      announcedGoalPaceReached = false;
    }
  }

  /** The current week's review for the active goal / label / week-start. */
  function currentWeeklyReview() {
    return weeklyReview(history, {
      now: Date.now(),
      minutes: goal.minutes,
      label:
        activeLabel === null
          ? applyAliases(goal.label, sessionTags)
          : activeLabel,
      weekStartsOn,
      tags: sessionTags,
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

  /** Snapshot the current in-memory state for a backup. The values are the
   * already-read (and normalised) storage values, so `exportBackup` stays
   * pure. */
  function readBackupState() {
    return {
      settings: engine.settings,
      history,
      goal,
      dailyGoal,
      ambient,
      locale,
      weekStart: weekStartsOn,
      sessionTags,
    };
  }

  /**
   * Export the whole local state as a JSON file. The file is produced by the
   * pure `backupToJson` helper and handed to the browser as a `Blob` object
   * URL, so nothing is uploaded and no storage key is written.
   */
  function exportBackupFile() {
    const json = backupToJson(readBackupState(), { now: Date.now() });
    const blob = new Blob([json], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = backupFileName();
    link.rel = "noopener";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    announce(t("announce.backupExported"));
  }

  /** Show a non-destructive inline error and announce it. Existing data is
   * never touched on a rejected file. */
  function showBackupError(message) {
    if (el.backupStatus) {
      el.backupStatus.textContent = message;
      window.setTimeout(() => {
        if (el.backupStatus.textContent === message) {
          el.backupStatus.textContent = "";
        }
      }, 4000);
    }
    announce(message);
  }

  /**
   * Write a validated backup back to `localStorage`. Keys whose normalised
   * value is empty/default are removed, matching the "a default install leaves
   * no trace" rule used everywhere else. The whole UI is re-rendered at the
   * end.
   */
  function applyRestoredBackup(parsed) {
    if (parsed.settings) {
      engine.setSettings(parsed.settings);
      writeStorage(STORAGE_KEYS.settings, engine.settings);
    }

    history = pruneHistory(parsed.history, {
      now: Date.now(),
      retentionDays: DEFAULT_RETENTION_DAYS,
    });
    if (history.length > 0) {
      writeStorage(STORAGE_KEYS.history, history);
    } else {
      try {
        window.localStorage.removeItem(STORAGE_KEYS.history);
      } catch (error) {
        /* Storage may be unavailable; the in-memory history still applies. */
      }
    }

    goal = normalizeGoal(parsed.goal);
    persistGoal();
    dailyGoal = normalizeDailyGoal(parsed.dailyGoal);
    persistDailyGoal();

    const nextAmbient = normalizeAmbient(parsed.ambient);
    const ambientChanged =
      nextAmbient.type !== ambient.type ||
      nextAmbient.volume !== ambient.volume;
    ambient = nextAmbient;
    persistAmbient();
    if (ambientChanged) {
      stopAmbient();
    }
    syncAmbient(engine.snapshot());

    locale = normalizeLocale(parsed.locale);
    t = createTranslator(locale);
    persistLocale();
    if (el.locale) {
      el.locale.value = locale;
    }

    weekStartsOn = normalizeWeekStart(parsed.weekStart);
    persistWeekStart();

    sessionTags = normalizeSessionTags(parsed.sessionTags);
    persistSessionTags();

    goalReached = null;
    dailyGoalReached = null;
    activeLabel = null;
    announcedStreak = null;
    announcedBreakdown = false;
    announcedDailyBreakdown = false;
    announcedGoalPace = false;
    announcedGoalPaceReached = false;
    lastBadgeValue = undefined;

    applyStaticTranslations();
    updateThemeButton(currentTheme());
    syncForm(engine.settings);
    syncAmbientControls();
    syncWeekStartControl();
    renderSessionTags();
    render(engine.snapshot());
    renderStats();
  }

  /** Validate and apply a backup string; returns `true` on success. A rejected
   * file leaves all existing data untouched. */
  function restoreBackupText(text) {
    const parsed = parseBackup(text, {
      now: Date.now(),
      retentionDays: DEFAULT_RETENTION_DAYS,
    });
    if (!parsed) {
      showBackupError(t("settings.backupInvalid"));
      return false;
    }
    applyRestoredBackup(parsed);
    announce(t("announce.backupRestored"));
    return true;
  }

  /** Read a chosen file with the browser's `FileReader` and restore it. The
   * read is entirely local; a read error is reported without touching data. */
  function handleBackupFile(file) {
    if (!file) {
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      restoreBackupText(typeof reader.result === "string" ? reader.result : "");
    };
    reader.onerror = () => {
      showBackupError(t("announce.backupFailed"));
    };
    try {
      reader.readAsText(file);
    } catch (error) {
      showBackupError(t("announce.backupFailed"));
    }
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
        closeLabelSuggestions();
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
  renderSessionTags();
  wireLabelSuggestions();
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

  if (el.sessionTagAdd) {
    el.sessionTagAdd.addEventListener("click", () => addSessionTag());
  }
  for (const input of [el.sessionTagFrom, el.sessionTagTo]) {
    if (input) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          addSessionTag();
        }
      });
    }
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

  if (el.backupExport) {
    el.backupExport.addEventListener("click", exportBackupFile);
  }

  if (el.backupRestore && el.backupRestoreFile) {
    el.backupRestore.addEventListener("click", () => {
      el.backupRestoreFile.click();
    });
    el.backupRestoreFile.addEventListener("change", () => {
      const file =
        el.backupRestoreFile.files && el.backupRestoreFile.files[0];
      handleBackupFile(file);
      el.backupRestoreFile.value = "";
    });
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
