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
  "label.unlabelled": "(unlabelled)",
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
  "settings.weekStart": "Week starts on",
  "settings.weekStartMonday": "Monday",
  "settings.weekStartSunday": "Sunday",
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
  "stats.dayLabel": "{weekday}: {count} sessions",
  "stats.recentLabel": "Recent focus sessions",
  "stats.recentTimestamp": "{month} {day}",
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
  "review.export": "Export CSV",
  "review.exportHint":
    "Downloads this week's review as a local CSV file. Nothing is uploaded.",
  "review.exported": "Weekly review exported as CSV.",
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
  "announce.weekStart": "Week starts on {day}.",
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
  "label.unlabelled": "(ohne Bezeichnung)",
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
  "settings.weekStart": "Woche beginnt am",
  "settings.weekStartMonday": "Montag",
  "settings.weekStartSunday": "Sonntag",
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
  "stats.dayLabel": "{weekday}: {count} Sitzungen",
  "stats.recentLabel": "Letzte Fokussitzungen",
  "stats.recentTimestamp": "{day}. {month}",
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
  "review.export": "CSV exportieren",
  "review.exportHint":
    "Lädt den Wochenrückblick als lokale CSV-Datei herunter. Es wird nichts hochgeladen.",
  "review.exported": "Wochenrückblick als CSV exportiert.",
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
  "announce.weekStart": "Woche beginnt am {day}.",
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
  "label.unlabelled": "(sin etiqueta)",
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
  "settings.weekStart": "La semana comienza el",
  "settings.weekStartMonday": "lunes",
  "settings.weekStartSunday": "domingo",
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
  "stats.dayLabel": "{weekday}: {count} sesiones",
  "stats.recentLabel": "Sesiones de concentración recientes",
  "stats.recentTimestamp": "{day} {month}",
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
  "review.export": "Exportar CSV",
  "review.exportHint":
    "Descarga la revisión de esta semana como un archivo CSV local. No se sube nada.",
  "review.exported": "Revisión semanal exportada como CSV.",
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
  "announce.weekStart": "La semana comienza el {day}.",
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
 * Pure `pluralCategory` selector shared by `en`, `de`, and `es`.
 *
 * The three shipped locales all use the two-form "one / other" distinction
 * (`1` is singular, everything else — including `0` — is plural). The selector
 * is a plain function so a future locale can plug in a different rule without
 * changing any caller; `pluralise` reads it through `LOCALE_DATA`.
 */
function oneOtherPlural(count) {
  const value = Math.abs(Number(count));
  if (!Number.isFinite(value)) {
    return "other";
  }
  return value === 1 ? "one" : "other";
}

/**
 * Bundled locale data for the derived, non-label strings.
 *
 * Each entry is plain, frozen data (plus the pure `plural` selector) so every
 * weekday name, month name, decimal/group separator, and plural rule ships in
 * this file. Nothing here is fetched and nothing depends on `Intl`, so the
 * module stays offline and dependency-free.
 *
 * - `weekdaysShort` / `weekdaysLong` are indexed by `Date#getDay()` (Sunday = 0).
 * - `monthsShort` / `monthsLong` are indexed by `Date#getMonth()` (January = 0).
 * - `plural` is a `(count) => "one" | "other"` category selector.
 */
export const LOCALE_DATA = Object.freeze({
  en: Object.freeze({
    weekdaysShort: Object.freeze(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]),
    weekdaysLong: Object.freeze([
      "Sunday",
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
    ]),
    monthsShort: Object.freeze([
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ]),
    monthsLong: Object.freeze([
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ]),
    decimalSeparator: ".",
    groupSeparator: ",",
    plural: oneOtherPlural,
  }),
  de: Object.freeze({
    weekdaysShort: Object.freeze(["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]),
    weekdaysLong: Object.freeze([
      "Sonntag",
      "Montag",
      "Dienstag",
      "Mittwoch",
      "Donnerstag",
      "Freitag",
      "Samstag",
    ]),
    monthsShort: Object.freeze([
      "Jan",
      "Feb",
      "Mär",
      "Apr",
      "Mai",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Okt",
      "Nov",
      "Dez",
    ]),
    monthsLong: Object.freeze([
      "Januar",
      "Februar",
      "März",
      "April",
      "Mai",
      "Juni",
      "Juli",
      "August",
      "September",
      "Oktober",
      "November",
      "Dezember",
    ]),
    decimalSeparator: ",",
    groupSeparator: ".",
    plural: oneOtherPlural,
  }),
  es: Object.freeze({
    weekdaysShort: Object.freeze(["dom", "lun", "mar", "mié", "jue", "vie", "sáb"]),
    weekdaysLong: Object.freeze([
      "domingo",
      "lunes",
      "martes",
      "miércoles",
      "jueves",
      "viernes",
      "sábado",
    ]),
    monthsShort: Object.freeze([
      "ene",
      "feb",
      "mar",
      "abr",
      "may",
      "jun",
      "jul",
      "ago",
      "sep",
      "oct",
      "nov",
      "dic",
    ]),
    monthsLong: Object.freeze([
      "enero",
      "febrero",
      "marzo",
      "abril",
      "mayo",
      "junio",
      "julio",
      "agosto",
      "septiembre",
      "octubre",
      "noviembre",
      "diciembre",
    ]),
    decimalSeparator: ",",
    groupSeparator: ".",
    plural: oneOtherPlural,
  }),
});

/** Return the locale data for a locale, falling back to `DEFAULT_LOCALE`. */
function localeData(locale) {
  const resolved = normalizeLocale(locale);
  return LOCALE_DATA[resolved] || LOCALE_DATA[DEFAULT_LOCALE];
}

/** Coerce a value to an integer count, defaulting to `0` for malformed input. */
function normaliseCount(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.trunc(parsed);
}

/** Resolve a Date-like input into a valid `Date`, or `null` when it cannot be
 * understood. Accepts `Date` instances, numeric timestamps, and `YYYY-MM-DD`
 * calendar keys (which are treated as local midnights). */
function toDate(value) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      return null;
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
    if (match) {
      const date = new Date(
        Number(match[1]),
        Number(match[2]) - 1,
        Number(match[3]),
      );
      return Number.isNaN(date.getTime()) ? null : date;
    }
    const parsed = Date.parse(trimmed);
    return Number.isFinite(parsed) ? new Date(parsed) : null;
  }
  return null;
}

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

/**
 * Select the plural category for `count` in `locale`.
 *
 * Uses the locale's pure `plural` selector from `LOCALE_DATA` and falls back to
 * the default locale for unknown input. Never throws; a malformed `count` is
 * treated as `"other"`.
 */
export function pluralCategory(count, locale) {
  const data = localeData(locale);
  if (data && typeof data.plural === "function") {
    return data.plural(count);
  }
  return oneOtherPlural(count);
}

/**
 * Pick the form matching `count`'s plural category from `forms`.
 *
 * `forms` is a plain map of category to template (for the shipped locales a
 * `{ one, other }` pair). The matching form is returned; when it is missing the
 * `other` form is used, then any available form, and finally an empty string.
 * This function only selects — it does not interpolate — so callers stay in
 * control of how `{count}` is filled.
 */
export function pluralise(count, forms, locale) {
  if (!forms || typeof forms !== "object") {
    return "";
  }
  const category = pluralCategory(count, locale);
  if (typeof forms[category] === "string") {
    return forms[category];
  }
  if (typeof forms.other === "string") {
    return forms.other;
  }
  for (const key of Object.keys(forms)) {
    if (typeof forms[key] === "string") {
      return forms[key];
    }
  }
  return "";
}

/**
 * Group the integer part of `value` with the locale's separators.
 *
 * `en` uses `1,234.5`, while `de` and `es` use `1.234,5`. Malformed or
 * non-finite input renders as `"0"` rather than throwing, and the sign is
 * preserved. No `Intl` and no locale database are used.
 */
export function formatNumber(value, locale) {
  const data = localeData(locale);
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "0";
  }
  const negative = numeric < 0;
  const absolute = Math.abs(numeric);
  const raw = absolute.toString();

  let integerPart;
  let fractionPart;
  if (raw.includes("e") || raw.includes("E")) {
    integerPart = absolute.toFixed(0);
    fractionPart = "";
    if (integerPart.includes("e") || integerPart.includes("E")) {
      integerPart = "0";
    }
  } else {
    const parts = raw.split(".");
    integerPart = parts[0];
    fractionPart = parts[1] || "";
  }

  let grouped = "";
  for (let index = 0; index < integerPart.length; index += 1) {
    if (index > 0 && (integerPart.length - index) % 3 === 0) {
      grouped += data.groupSeparator;
    }
    grouped += integerPart[index];
  }

  let result = grouped;
  if (fractionPart.length > 0) {
    result += data.decimalSeparator + fractionPart;
  }
  return negative ? `-${result}` : result;
}

/**
 * Return the localised weekday name for a date.
 *
 * `date` may be a `Date`, a numeric timestamp, or a `YYYY-MM-DD` calendar key.
 * The short name is returned by default; pass `{ long: true }` for the full
 * name. Unknown locales fall back to `en` and unparseable input returns `""`.
 */
export function formatWeekday(date, locale, { long = false } = {}) {
  const resolved = toDate(date);
  if (!resolved) {
    return "";
  }
  const data = localeData(locale);
  const names = long ? data.weekdaysLong : data.weekdaysShort;
  const name = names ? names[resolved.getDay()] : undefined;
  return typeof name === "string" ? name : "";
}

/**
 * Return the localised month name for a date.
 *
 * `date` may be a `Date`, a numeric timestamp, or a `YYYY-MM-DD` calendar key.
 * The short name is returned by default; pass `{ long: true }` for the full
 * name. Unknown locales fall back to `en` and unparseable input returns `""`.
 */
export function formatMonth(date, locale, { long = false } = {}) {
  const resolved = toDate(date);
  if (!resolved) {
    return "";
  }
  const data = localeData(locale);
  const names = long ? data.monthsLong : data.monthsShort;
  const name = names ? names[resolved.getMonth()] : undefined;
  return typeof name === "string" ? name : "";
}

/**
 * Format a whole number of minutes as a localised duration label.
 *
 * The count is grouped with `formatNumber` and the unit label is drawn from the
 * bundled catalog (`recent.minutes`) through the locale's plural selector, so
 * no number or unit is hard-coded in English. Malformed input becomes `0 min`.
 */
export function formatDuration(minutes, locale) {
  const count = normaliseCount(minutes);
  const unit = translate(locale, "recent.minutes");
  const template = pluralise(count, { one: unit, other: unit }, locale) || unit;
  return interpolate(template, { count: formatNumber(count, locale) });
}
