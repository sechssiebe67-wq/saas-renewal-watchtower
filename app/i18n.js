/**
 * Focus Flow internationalisation (i18n).
 *
 * Pure, dependency-free helpers for a tiny bundled message catalog. This module
 * has no access to the page, the storage layer, the network, or any global: it
 * maps plain data to plain data, so the DOM layer (main.js) owns every side
 * effect and the catalog can be reasoned about and tested on its own.
 *
 * Everything ships in this one file — there is no network request, no
 * third-party library, and no runtime download. `normalizeLocale` coerces
 * arbitrary stored input (a string, a `{ locale }` object, or anything else)
 * into a supported locale id without ever throwing, and `translate` falls back
 * to `DEFAULT_LOCALE` and then to the key itself so a missing message can never
 * crash the page.
 */

/** Supported locale ids, in display/switcher order. */
export const SUPPORTED_LOCALES = Object.freeze(["en", "de", "es"]);

/** Human-readable names for each locale id, used by the locale switcher. */
export const LOCALE_LABELS = Object.freeze({
  en: "English",
  de: "Deutsch",
  es: "Español",
});

/** The fallback locale used when nothing else matches. */
export const DEFAULT_LOCALE = "en";

/** Shape version for the `focus-flow:locale` storage entry. Version 1 stores
 * the canonical locale id as a bare string. */
export const LOCALE_STORAGE_SHAPE_VERSION = 1;

const EN_MESSAGES = {
  "app.title": "Focus Flow — Distraction-free focus timer",
  "a11y.skip": "Skip to main content",
  "theme.dark": "Dark theme",
  "theme.light": "Light theme",
  "timer.heading": "Focus timer",
  "phase.work": "Work session",
  "phase.shortBreak": "Short break",
  "phase.longBreak": "Long break",
  "phase.unknown": "Phase",
  "timer.sessionsToday": "Sessions completed today:",
  "controls.label": "Timer controls",
  "controls.start": "Start",
  "controls.pause": "Pause",
  "controls.reset": "Reset",
  "controls.skip": "Skip",
  "label.heading": "Session label (optional)",
  "label.placeholder": "e.g. Thesis chapter 3",
  "label.hint": "Stored only on this device.",
  "label.noLabel": "No label",
  "shortcuts.title": "Shortcuts:",
  "shortcuts.startPause": "start/pause",
  "shortcuts.reset": "reset",
  "shortcuts.skip": "skip",
  "settings.heading": "Settings",
  "settings.work": "Work (minutes)",
  "settings.shortBreak": "Short break (minutes)",
  "settings.longBreak": "Long break (minutes)",
  "settings.longBreakInterval": "Long break after (work sessions)",
  "settings.sound": "Play a sound when a phase ends",
  "settings.autoStart": "Automatically start breaks",
  "settings.ambient": "Ambient sound",
  "settings.ambientHint":
    "Generated in your browser with the Web Audio API. No audio files are downloaded, and your choice is stored only on this device.",
  "settings.ambientVolume": "Ambient volume",
  "settings.ambientVolumeHint":
    "Plays during work sessions (and breaks when they auto-start). Stored only on this device.",
  "settings.goal": "Weekly focus goal (minutes)",
  "settings.goalPlaceholder": "0 = no goal",
  "settings.goalHint":
    "Minutes per week, optionally scoped to the selected label. Stored only on this device. Set 0 to clear.",
  "settings.clearGoal": "Clear goal",
  "settings.save": "Save settings",
  "settings.saved": "Saved.",
  "settings.language": "Language",
  "ambient.off": "Off",
  "ambient.brown": "Brown noise",
  "ambient.pink": "Pink noise",
  "ambient.rain": "Soft rain",
  "stats.heading": "Stats",
  "stats.last7": "Last 7 days:",
  "stats.sessions": "sessions",
  "stats.minFocused": "min focused",
  "stats.empty": "No sessions yet — start your first focus block.",
  "stats.streakCurrent": "Current streak",
  "stats.streakLongest": "Longest streak",
  "stats.today": "Today",
  "stats.reminder": "No focus session logged today yet.",
  "stats.weeklyGoal": "Weekly goal",
  "stats.goalReached": "✓ Goal reached",
  "stats.goalBarLabel": "Weekly focus goal progress",
  "stats.labelsLabel": "Filter the last 7 days by session label",
  "stats.daysLabel": "Completed work sessions in the last 7 days",
  "stats.recentLabel": "Recent focus sessions",
  "recent.minutes": "{count} min",
  "streak.daysOne": "{count} day",
  "streak.daysMany": "{count} days",
  "stats.todayOne": "{count} session · {minutes} min",
  "stats.todayMany": "{count} sessions · {minutes} min",
  "review.heading": "Weekly review",
  "review.empty":
    "No sessions yet this week — start a focus block to build your review.",
  "review.thisWeek": "This week:",
  "review.minFocused": "min focused",
  "review.of": "of",
  "review.minGoal": "min goal",
  "review.barLabel": "Weekly focus goal progress for this week",
  "review.labelsLabel": "Focused minutes by session label this week",
  "review.labelStatsWithGoal": "{sessions} · {minutes} min · {percent}%",
  "review.labelStats": "{sessions} · {minutes} min",
  "footer.text":
    "Focus Flow runs entirely in your browser. Your settings, session count, and focus history stay on this device. No accounts, no tracking, no network.",
  "announce.ambientOff": "Ambient sound off.",
  "announce.ambientOn": "Ambient sound: {type}.",
  "announce.labelCleared": "Label filter cleared.",
  "announce.filtered": "Filtered to {label}.",
  "announce.streak": "Streak: {value}.",
  "announce.goalReached": "Weekly goal reached.",
  "announce.goalSaved": "Weekly goal saved.",
  "announce.goalCleared": "Weekly goal cleared.",
  "announce.locale": "Language: {language}.",
  "announce.phaseFinished": "{finished} finished. {next} ready.",
  "announce.timerStarted": "Timer started. {phase}.",
  "announce.timerPaused": "Timer paused. {time} remaining.",
  "announce.timerReset": "Timer reset. {phase}.",
  "announce.settingsSaved": "Settings saved.",
};

const DE_MESSAGES = {
  "app.title": "Focus Flow — Störungsfreier Fokus-Timer",
  "a11y.skip": "Zum Hauptinhalt springen",
  "theme.dark": "Dunkles Design",
  "theme.light": "Helles Design",
  "timer.heading": "Fokus-Timer",
  "phase.work": "Arbeitsphase",
  "phase.shortBreak": "Kurze Pause",
  "phase.longBreak": "Lange Pause",
  "phase.unknown": "Phase",
  "timer.sessionsToday": "Heute abgeschlossene Sitzungen:",
  "controls.label": "Timer-Steuerung",
  "controls.start": "Start",
  "controls.pause": "Pause",
  "controls.reset": "Zurücksetzen",
  "controls.skip": "Überspringen",
  "label.heading": "Sitzungsbezeichnung (optional)",
  "label.placeholder": "z. B. Dissertation Kapitel 3",
  "label.hint": "Nur auf diesem Gerät gespeichert.",
  "label.noLabel": "Keine Bezeichnung",
  "shortcuts.title": "Tastenkürzel:",
  "shortcuts.startPause": "starten/pausieren",
  "shortcuts.reset": "zurücksetzen",
  "shortcuts.skip": "überspringen",
  "settings.heading": "Einstellungen",
  "settings.work": "Arbeit (Minuten)",
  "settings.shortBreak": "Kurze Pause (Minuten)",
  "settings.longBreak": "Lange Pause (Minuten)",
  "settings.longBreakInterval": "Lange Pause nach (Arbeitsphasen)",
  "settings.sound": "Ton abspielen, wenn eine Phase endet",
  "settings.autoStart": "Pausen automatisch starten",
  "settings.ambient": "Hintergrundgeräusch",
  "settings.ambientHint":
    "In deinem Browser mit der Web Audio API erzeugt. Es werden keine Audiodateien heruntergeladen, und deine Auswahl wird nur auf diesem Gerät gespeichert.",
  "settings.ambientVolume": "Lautstärke des Hintergrundgeräuschs",
  "settings.ambientVolumeHint":
    "Läuft während der Arbeitsphasen (und in Pausen, wenn sie automatisch starten). Nur auf diesem Gerät gespeichert.",
  "settings.goal": "Wöchentliches Fokusziel (Minuten)",
  "settings.goalPlaceholder": "0 = kein Ziel",
  "settings.goalHint":
    "Minuten pro Woche, optional auf die ausgewählte Bezeichnung beschränkt. Nur auf diesem Gerät gespeichert. Auf 0 setzen zum Löschen.",
  "settings.clearGoal": "Ziel löschen",
  "settings.save": "Einstellungen speichern",
  "settings.saved": "Gespeichert.",
  "settings.language": "Sprache",
  "ambient.off": "Aus",
  "ambient.brown": "Braunes Rauschen",
  "ambient.pink": "Rosa Rauschen",
  "ambient.rain": "Sanfter Regen",
  "stats.heading": "Statistik",
  "stats.last7": "Letzte 7 Tage:",
  "stats.sessions": "Sitzungen",
  "stats.minFocused": "Min. fokussiert",
  "stats.empty": "Noch keine Sitzungen — starte deinen ersten Fokusblock.",
  "stats.streakCurrent": "Aktuelle Serie",
  "stats.streakLongest": "Längste Serie",
  "stats.today": "Heute",
  "stats.reminder": "Heute wurde noch keine Fokussitzung erfasst.",
  "stats.weeklyGoal": "Wochenziel",
  "stats.goalReached": "✓ Ziel erreicht",
  "stats.goalBarLabel": "Fortschritt des wöchentlichen Fokusziels",
  "stats.labelsLabel": "Die letzten 7 Tage nach Sitzungsbezeichnung filtern",
  "stats.daysLabel": "Abgeschlossene Arbeitsphasen der letzten 7 Tage",
  "stats.recentLabel": "Letzte Fokussitzungen",
  "recent.minutes": "{count} Min.",
  "streak.daysOne": "{count} Tag",
  "streak.daysMany": "{count} Tage",
  "stats.todayOne": "{count} Sitzung · {minutes} Min.",
  "stats.todayMany": "{count} Sitzungen · {minutes} Min.",
  "review.heading": "Wochenrückblick",
  "review.empty":
    "Diese Woche noch keine Sitzungen — starte einen Fokusblock für deinen Rückblick.",
  "review.thisWeek": "Diese Woche:",
  "review.minFocused": "Min. fokussiert",
  "review.of": "von",
  "review.minGoal": "Min. Ziel",
  "review.barLabel":
    "Fortschritt des wöchentlichen Fokusziels für diese Woche",
  "review.labelsLabel":
    "Fokussierte Minuten nach Sitzungsbezeichnung diese Woche",
  "review.labelStatsWithGoal": "{sessions} · {minutes} Min. · {percent} %",
  "review.labelStats": "{sessions} · {minutes} Min.",
  "footer.text":
    "Focus Flow läuft vollständig in deinem Browser. Deine Einstellungen, dein Sitzungszähler und dein Fokusverlauf bleiben auf diesem Gerät. Keine Konten, kein Tracking, kein Netzwerk.",
  "announce.ambientOff": "Hintergrundgeräusch aus.",
  "announce.ambientOn": "Hintergrundgeräusch: {type}.",
  "announce.labelCleared": "Bezeichnungsfilter gelöscht.",
  "announce.filtered": "Gefiltert nach {label}.",
  "announce.streak": "Serie: {value}.",
  "announce.goalReached": "Wochenziel erreicht.",
  "announce.goalSaved": "Wochenziel gespeichert.",
  "announce.goalCleared": "Wochenziel gelöscht.",
  "announce.locale": "Sprache: {language}.",
  "announce.phaseFinished": "{finished} beendet. {next} bereit.",
  "announce.timerStarted": "Timer gestartet. {phase}.",
  "announce.timerPaused": "Timer pausiert. {time} verbleibend.",
  "announce.timerReset": "Timer zurückgesetzt. {phase}.",
  "announce.settingsSaved": "Einstellungen gespeichert.",
};

const ES_MESSAGES = {
  "app.title": "Focus Flow — Temporizador de concentración sin distracciones",
  "a11y.skip": "Saltar al contenido principal",
  "theme.dark": "Tema oscuro",
  "theme.light": "Tema claro",
  "timer.heading": "Temporizador de concentración",
  "phase.work": "Sesión de trabajo",
  "phase.shortBreak": "Descanso corto",
  "phase.longBreak": "Descanso largo",
  "phase.unknown": "Fase",
  "timer.sessionsToday": "Sesiones completadas hoy:",
  "controls.label": "Controles del temporizador",
  "controls.start": "Iniciar",
  "controls.pause": "Pausar",
  "controls.reset": "Reiniciar",
  "controls.skip": "Omitir",
  "label.heading": "Etiqueta de sesión (opcional)",
  "label.placeholder": "p. ej., Tesis capítulo 3",
  "label.hint": "Guardado solo en este dispositivo.",
  "label.noLabel": "Sin etiqueta",
  "shortcuts.title": "Atajos:",
  "shortcuts.startPause": "iniciar/pausar",
  "shortcuts.reset": "reiniciar",
  "shortcuts.skip": "omitir",
  "settings.heading": "Ajustes",
  "settings.work": "Trabajo (minutos)",
  "settings.shortBreak": "Descanso corto (minutos)",
  "settings.longBreak": "Descanso largo (minutos)",
  "settings.longBreakInterval": "Descanso largo después de (sesiones de trabajo)",
  "settings.sound": "Reproducir un sonido cuando termina una fase",
  "settings.autoStart": "Iniciar los descansos automáticamente",
  "settings.ambient": "Sonido ambiente",
  "settings.ambientHint":
    "Generado en tu navegador con la Web Audio API. No se descargan archivos de audio y tu elección se guarda solo en este dispositivo.",
  "settings.ambientVolume": "Volumen del sonido ambiente",
  "settings.ambientVolumeHint":
    "Suena durante las sesiones de trabajo (y los descansos cuando se inician automáticamente). Guardado solo en este dispositivo.",
  "settings.goal": "Objetivo de concentración semanal (minutos)",
  "settings.goalPlaceholder": "0 = sin objetivo",
  "settings.goalHint":
    "Minutos por semana, opcionalmente limitados a la etiqueta seleccionada. Guardado solo en este dispositivo. Pon 0 para borrarlo.",
  "settings.clearGoal": "Borrar objetivo",
  "settings.save": "Guardar ajustes",
  "settings.saved": "Guardado.",
  "settings.language": "Idioma",
  "ambient.off": "Desactivado",
  "ambient.brown": "Ruido marrón",
  "ambient.pink": "Ruido rosa",
  "ambient.rain": "Lluvia suave",
  "stats.heading": "Estadísticas",
  "stats.last7": "Últimos 7 días:",
  "stats.sessions": "sesiones",
  "stats.minFocused": "min concentrados",
  "stats.empty": "Aún no hay sesiones: inicia tu primer bloque de concentración.",
  "stats.streakCurrent": "Racha actual",
  "stats.streakLongest": "Racha más larga",
  "stats.today": "Hoy",
  "stats.reminder": "Aún no se ha registrado ninguna sesión de concentración hoy.",
  "stats.weeklyGoal": "Objetivo semanal",
  "stats.goalReached": "✓ Objetivo alcanzado",
  "stats.goalBarLabel": "Progreso del objetivo de concentración semanal",
  "stats.labelsLabel": "Filtrar los últimos 7 días por etiqueta de sesión",
  "stats.daysLabel": "Sesiones de trabajo completadas en los últimos 7 días",
  "stats.recentLabel": "Sesiones de concentración recientes",
  "recent.minutes": "{count} min",
  "streak.daysOne": "{count} día",
  "streak.daysMany": "{count} días",
  "stats.todayOne": "{count} sesión · {minutes} min",
  "stats.todayMany": "{count} sesiones · {minutes} min",
  "review.heading": "Revisión semanal",
  "review.empty":
    "Aún no hay sesiones esta semana: inicia un bloque de concentración para crear tu revisión.",
  "review.thisWeek": "Esta semana:",
  "review.minFocused": "min concentrados",
  "review.of": "de",
  "review.minGoal": "min de objetivo",
  "review.barLabel":
    "Progreso del objetivo de concentración semanal de esta semana",
  "review.labelsLabel":
    "Minutos concentrados por etiqueta de sesión esta semana",
  "review.labelStatsWithGoal": "{sessions} · {minutes} min · {percent} %",
  "review.labelStats": "{sessions} · {minutes} min",
  "footer.text":
    "Focus Flow funciona por completo en tu navegador. Tus ajustes, el recuento de sesiones y el historial de concentración permanecen en este dispositivo. Sin cuentas, sin seguimiento, sin red.",
  "announce.ambientOff": "Sonido ambiente desactivado.",
  "announce.ambientOn": "Sonido ambiente: {type}.",
  "announce.labelCleared": "Filtro de etiquetas borrado.",
  "announce.filtered": "Filtrado por {label}.",
  "announce.streak": "Racha: {value}.",
  "announce.goalReached": "Objetivo semanal alcanzado.",
  "announce.goalSaved": "Objetivo semanal guardado.",
  "announce.goalCleared": "Objetivo semanal borrado.",
  "announce.locale": "Idioma: {language}.",
  "announce.phaseFinished": "{finished} finalizada. {next} lista.",
  "announce.timerStarted": "Temporizador iniciado. {phase}.",
  "announce.timerPaused": "Temporizador en pausa. Quedan {time}.",
  "announce.timerReset": "Temporizador reiniciado. {phase}.",
  "announce.settingsSaved": "Ajustes guardados.",
};

/** The bundled message catalog, keyed by locale id. Each value is a flat map
 * of message key to template string; `{name}` placeholders are filled by
 * `translate`. Everything is bundled here, so no network request is ever made. */
export const MESSAGES = Object.freeze({
  en: Object.freeze(EN_MESSAGES),
  de: Object.freeze(DE_MESSAGES),
  es: Object.freeze(ES_MESSAGES),
});

/**
 * Coerce arbitrary stored input into a supported locale id.
 *
 * Accepts a bare locale string, a `{ locale }` object, or anything else.
 * Matching is case-insensitive and a regional tag such as `"de-AT"` resolves to
 * its base language. Unknown, missing, or malformed input falls back to
 * `DEFAULT_LOCALE`, and this function never throws.
 */
export function normalizeLocale(raw) {
  let candidate = raw;
  if (raw && typeof raw === "object") {
    candidate = raw.locale;
  }
  if (typeof candidate !== "string") {
    return DEFAULT_LOCALE;
  }
  const normalized = candidate.trim().toLowerCase();
  if (SUPPORTED_LOCALES.includes(normalized)) {
    return normalized;
  }
  const base = normalized.split("-")[0];
  if (SUPPORTED_LOCALES.includes(base)) {
    return base;
  }
  return DEFAULT_LOCALE;
}

/** Substitute `{name}` placeholders from `params`. Missing or non-object
 * params, and unknown placeholder names, are left untouched rather than
 * throwing. */
function interpolate(template, params) {
  if (!params || typeof params !== "object") {
    return template;
  }
  return template.replace(/\{(\w+)\}/g, (match, name) => {
    if (!Object.prototype.hasOwnProperty.call(params, name)) {
      return match;
    }
    const value = params[name];
    if (value === undefined || value === null) {
      return match;
    }
    return String(value);
  });
}

/**
 * Look up `key` in the requested locale and substitute `params`.
 *
 * Resolution order: the requested locale, then `DEFAULT_LOCALE`, then the key
 * itself, so a missing message can never produce `undefined`. A missing
 * placeholder value is left in place instead of throwing.
 */
export function translate(locale, key, params) {
  const resolved = normalizeLocale(locale);
  const requested = MESSAGES[resolved] || {};
  const fallback = MESSAGES[DEFAULT_LOCALE] || {};
  let template = requested[key];
  if (typeof template !== "string") {
    template = fallback[key];
  }
  if (typeof template !== "string") {
    template = key;
  }
  return interpolate(template, params);
}

/** Return a bound `t(key, params)` function for a locale. The bound locale is
 * normalised once, so `t` is cheap to call in render loops. */
export function createTranslator(locale) {
  const resolved = normalizeLocale(locale);
  return function t(key, params) {
    return translate(resolved, key, params);
  };
}
