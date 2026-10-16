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
  "label.suggestionsLabel": "Previously used session labels",
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
  "settings.dailyGoal": "Daily focus goal (minutes)",
  "settings.dailyGoalPlaceholder": "0 = no goal",
  "settings.dailyGoalHint":
    "Minutes for today, optionally scoped to the selected label. Stored only on this device. Set 0 to clear.",
  "settings.clearDailyGoal": "Clear daily goal",
  "settings.sessionTags": "Label aliases",
  "settings.sessionTagsHint":
    "Rename session labels in every view without changing the sessions you already saved. Stored only on this device.",
  "settings.sessionTagsFrom": "Original label",
  "settings.sessionTagsTo": "Display as",
  "settings.sessionTagsAdd": "Add alias",
  "settings.sessionTagsEntry": "{label} → {alias}",
  "settings.sessionTagsListLabel": "Current label aliases",
  "settings.sessionTagsEmpty": "No label aliases yet.",
  "settings.sessionTagsRemove": "Remove",
  "settings.sessionTagsRemoveLabel": "Remove alias for {label}",
  "settings.save": "Save settings",
  "settings.saved": "Saved.",
  "settings.language": "Language",
  "settings.weekStart": "Week starts on",
  "settings.weekStartMonday": "Monday",
  "settings.weekStartSunday": "Sunday",
  "settings.backup": "Backup & restore",
  "settings.backupHint":
    "Export a local JSON copy of your settings, history, and goals, or restore one. Files stay on this device.",
  "settings.exportBackup": "Export backup",
  "settings.exportBackupHint":
    "Downloads a JSON file with your settings, history, and goals. Nothing is uploaded.",
  "settings.restoreBackup": "Restore backup",
  "settings.restoreBackupHint":
    "Replaces your local data with a backup file you choose. Nothing is uploaded.",
  "settings.restoreBackupFile": "Backup file to restore",
  "settings.backupInvalid":
    "That file is not a valid Focus Flow backup. Your data was not changed.",
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
  "stats.dailyGoal": "Daily goal",
  "stats.dailyGoalBarLabel": "Daily focus goal progress",
  "stats.dailyGoalReached": "✓ Daily goal reached",
  "stats.goalBreakdown": "By label this week",
  "stats.goalBreakdownLabel":
    "Focused minutes by session label against the weekly goal",
  "stats.goalBreakdownOne": "{count} label",
  "stats.goalBreakdownMany": "{count} labels",
  "stats.goalLabelStats": "{minutes} · {percent}% of goal",
  "stats.goalPaceLabel": "Weekly goal pace projection",
  "stats.goalPaceLine": "≈ {minutes}/day for {days}",
  "stats.goalPaceDaysOne": "{count} more day",
  "stats.goalPaceDaysMany": "{count} more days",
  "stats.goalPaceOnTrack": "On track",
  "stats.goalPaceBehind": "Behind pace",
  "stats.trendHeading": "Focus trend",
  "stats.trendChartLabel": "Weekly focused minutes over the last 8 weeks",
  "stats.trendUp": "Trending up",
  "stats.trendDown": "Trending down",
  "stats.trendFlat": "Steady",
  "stats.trendRange": "{min}–{max} min",
  "stats.trendEmpty": "No focus sessions in the last few weeks.",
  "stats.dailyTrendHeading": "Daily focus trend",
  "stats.dailyTrendChartLabel": "Daily focused minutes over the last 14 days",
  "stats.dailyTrendUp": "Trending up",
  "stats.dailyTrendDown": "Trending down",
  "stats.dailyTrendFlat": "Steady",
  "stats.dailyTrendRange": "{min}–{max} min",
  "stats.dailyTrendEmpty": "No focus sessions in the last two weeks.",
  "stats.heatmapHeading": "Focus heatmap",
  "stats.heatmapLabel": "Daily focused minutes over the last 12 weeks",
  "stats.heatmapRange": "{min}–{max} min per day",
  "stats.heatmapDay": "{weekday} {month} {day}: {minutes} min",
  "stats.heatmapLess": "Less",
  "stats.heatmapMore": "More",
  "stats.heatmapEmpty":
    "No focus sessions yet — the heatmap fills in as you work.",
  "stats.shareHeading": "Focus share",
  "stats.shareChartLabel": "Share of this week's focused minutes by label",
  "stats.shareSummary": "{minutes} · {labels}",
  "stats.shareLabelsOne": "{count} label",
  "stats.shareLabelsMany": "{count} labels",
  "stats.shareSlice": "{label}: {minutes} · {percent}%",
  "stats.shareEmpty":
    "No focus sessions yet this week — the focus share fills in as you work.",
  "stats.dailyBreakdown": "By label today",
  "stats.dailyBreakdownLabel":
    "Focused minutes by session label against the daily goal",
  "stats.dailyLabelStats": "{minutes} · {percent}% of daily goal",
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
  "announce.labelSuggestion": "Label: {label}.",
  "announce.streak": "Streak: {value}.",
  "announce.goalReached": "Weekly goal reached.",
  "announce.goalBreakdown": "Weekly goal by label: {summary}.",
  "announce.goalPace": "Weekly goal pace: {summary}.",
  "announce.trend": "Focus trend: {summary}.",
  "announce.dailyTrend": "Daily focus trend: {summary}.",
  "announce.heatmap": "Focus heatmap: {summary}.",
  "announce.share": "Focus share: {summary}.",
  "announce.goalBreakdownScoped": "Weekly goal for {label}: {minutes}.",
  "announce.dailyBreakdown": "Daily goal by label: {summary}.",
  "announce.dailyBreakdownScoped": "Daily goal for {label}: {minutes}.",
  "announce.badge": "App badge: {minutes} remaining.",
  "announce.goalSaved": "Weekly goal saved.",
  "announce.goalCleared": "Weekly goal cleared.",
  "announce.dailyGoalReached": "Daily goal reached.",
  "announce.dailyGoalSaved": "Daily goal saved.",
  "announce.dailyGoalCleared": "Daily goal cleared.",
  "announce.sessionTagsSaved": "Alias saved: {label} is now shown as {alias}.",
  "announce.sessionTagsRemoved": "Alias removed for {label}.",
  "announce.sessionTagsCleared": "Alias cleared for {label}.",
  "announce.sessionTagsInvalid":
    "Enter both a label and a replacement to add an alias.",
  "announce.locale": "Language: {language}.",
  "announce.weekStart": "Week starts on {day}.",
  "announce.backupExported": "Backup exported.",
  "announce.backupRestored": "Backup restored.",
  "announce.backupFailed":
    "Backup restore failed. Your data was not changed.",
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
  "label.suggestionsLabel": "Zuvor verwendete Sitzungsbezeichnungen",
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
  "settings.dailyGoal": "Tägliches Fokusziel (Minuten)",
  "settings.dailyGoalPlaceholder": "0 = kein Ziel",
  "settings.dailyGoalHint":
    "Minuten für heute, optional auf die ausgewählte Bezeichnung beschränkt. Nur auf diesem Gerät gespeichert. Auf 0 setzen zum Löschen.",
  "settings.clearDailyGoal": "Tagesziel löschen",
  "settings.sessionTags": "Bezeichnungs-Aliase",
  "settings.sessionTagsHint":
    "Benenne Sitzungsbezeichnungen in jeder Ansicht um, ohne bereits gespeicherte Sitzungen zu ändern. Nur auf diesem Gerät gespeichert.",
  "settings.sessionTagsFrom": "Ursprüngliche Bezeichnung",
  "settings.sessionTagsTo": "Anzeigen als",
  "settings.sessionTagsAdd": "Alias hinzufügen",
  "settings.sessionTagsEntry": "{label} → {alias}",
  "settings.sessionTagsListLabel": "Aktuelle Bezeichnungs-Aliase",
  "settings.sessionTagsEmpty": "Noch keine Bezeichnungs-Aliase.",
  "settings.sessionTagsRemove": "Entfernen",
  "settings.sessionTagsRemoveLabel": "Alias für {label} entfernen",
  "settings.save": "Einstellungen speichern",
  "settings.saved": "Gespeichert.",
  "settings.language": "Sprache",
  "settings.weekStart": "Woche beginnt am",
  "settings.weekStartMonday": "Montag",
  "settings.weekStartSunday": "Sonntag",
  "settings.backup": "Sichern & wiederherstellen",
  "settings.backupHint":
    "Exportiere eine lokale JSON-Kopie deiner Einstellungen, deines Verlaufs und deiner Ziele oder stelle eine wieder her. Dateien bleiben auf diesem Gerät.",
  "settings.exportBackup": "Sicherung exportieren",
  "settings.exportBackupHint":
    "Lädt eine JSON-Datei mit deinen Einstellungen, deinem Verlauf und deinen Zielen herunter. Es wird nichts hochgeladen.",
  "settings.restoreBackup": "Sicherung wiederherstellen",
  "settings.restoreBackupHint":
    "Ersetzt deine lokalen Daten durch eine von dir gewählte Sicherungsdatei. Es wird nichts hochgeladen.",
  "settings.restoreBackupFile": "Wiederherzustellende Sicherungsdatei",
  "settings.backupInvalid":
    "Diese Datei ist keine gültige Focus-Flow-Sicherung. Deine Daten wurden nicht geändert.",
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
  "stats.dailyGoal": "Tagesziel",
  "stats.dailyGoalBarLabel": "Fortschritt des täglichen Fokusziels",
  "stats.dailyGoalReached": "✓ Tagesziel erreicht",
  "stats.goalBreakdown": "Nach Bezeichnung diese Woche",
  "stats.goalBreakdownLabel":
    "Fokussierte Minuten nach Sitzungsbezeichnung im Verhältnis zum Wochenziel",
  "stats.goalBreakdownOne": "{count} Bezeichnung",
  "stats.goalBreakdownMany": "{count} Bezeichnungen",
  "stats.goalLabelStats": "{minutes} · {percent} % des Ziels",
  "stats.goalPaceLabel": "Prognose zum Tempo des Wochenziels",
  "stats.goalPaceLine": "≈ {minutes}/Tag für {days}",
  "stats.goalPaceDaysOne": "noch {count} Tag",
  "stats.goalPaceDaysMany": "noch {count} Tage",
  "stats.goalPaceOnTrack": "Im Plan",
  "stats.goalPaceBehind": "Hinter dem Tempo",
  "stats.trendHeading": "Fokustrend",
  "stats.trendChartLabel": "Wöchentliche Fokusminuten der letzten 8 Wochen",
  "stats.trendUp": "Aufwärtstrend",
  "stats.trendDown": "Abwärtstrend",
  "stats.trendFlat": "Stetig",
  "stats.trendRange": "{min}–{max} Min.",
  "stats.trendEmpty": "Keine Fokussitzungen in den letzten Wochen.",
  "stats.dailyTrendHeading": "Täglicher Fokustrend",
  "stats.dailyTrendChartLabel": "Tägliche Fokusminuten der letzten 14 Tage",
  "stats.dailyTrendUp": "Aufwärtstrend",
  "stats.dailyTrendDown": "Abwärtstrend",
  "stats.dailyTrendFlat": "Stetig",
  "stats.dailyTrendRange": "{min}–{max} Min.",
  "stats.dailyTrendEmpty": "Keine Fokussitzungen in den letzten zwei Wochen.",
  "stats.heatmapHeading": "Fokus-Heatmap",
  "stats.heatmapLabel": "Tägliche Fokusminuten der letzten 12 Wochen",
  "stats.heatmapRange": "{min}–{max} Min. pro Tag",
  "stats.heatmapDay": "{weekday}, {month} {day}: {minutes} Min.",
  "stats.heatmapLess": "Weniger",
  "stats.heatmapMore": "Mehr",
  "stats.heatmapEmpty":
    "Noch keine Fokussitzungen — die Heatmap füllt sich, während du arbeitest.",
  "stats.shareHeading": "Fokusverteilung",
  "stats.shareChartLabel":
    "Anteil der Fokusminuten dieser Woche nach Bezeichnung",
  "stats.shareSummary": "{minutes} · {labels}",
  "stats.shareLabelsOne": "{count} Bezeichnung",
  "stats.shareLabelsMany": "{count} Bezeichnungen",
  "stats.shareSlice": "{label}: {minutes} · {percent} %",
  "stats.shareEmpty":
    "Diese Woche noch keine Fokussitzungen — die Fokusverteilung füllt sich, während du arbeitest.",
  "stats.dailyBreakdown": "Nach Bezeichnung heute",
  "stats.dailyBreakdownLabel":
    "Fokussierte Minuten nach Sitzungsbezeichnung im Verhältnis zum Tagesziel",
  "stats.dailyLabelStats": "{minutes} · {percent} % des Tagesziels",
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
  "announce.labelSuggestion": "Bezeichnung: {label}.",
  "announce.streak": "Serie: {value}.",
  "announce.goalReached": "Wochenziel erreicht.",
  "announce.goalBreakdown": "Wochenziel nach Bezeichnung: {summary}.",
  "announce.goalPace": "Tempo des Wochenziels: {summary}.",
  "announce.trend": "Fokustrend: {summary}.",
  "announce.dailyTrend": "Täglicher Fokustrend: {summary}.",
  "announce.heatmap": "Fokus-Heatmap: {summary}.",
  "announce.share": "Fokusverteilung: {summary}.",
  "announce.goalBreakdownScoped": "Wochenziel für {label}: {minutes}.",
  "announce.dailyBreakdown": "Tagesziel nach Bezeichnung: {summary}.",
  "announce.dailyBreakdownScoped": "Tagesziel für {label}: {minutes}.",
  "announce.badge": "App-Symbol: {minutes} verbleibend.",
  "announce.goalSaved": "Wochenziel gespeichert.",
  "announce.goalCleared": "Wochenziel gelöscht.",
  "announce.dailyGoalReached": "Tagesziel erreicht.",
  "announce.dailyGoalSaved": "Tagesziel gespeichert.",
  "announce.dailyGoalCleared": "Tagesziel gelöscht.",
  "announce.sessionTagsSaved":
    "Alias gespeichert: {label} wird jetzt als {alias} angezeigt.",
  "announce.sessionTagsRemoved": "Alias für {label} entfernt.",
  "announce.sessionTagsCleared": "Alias für {label} gelöscht.",
  "announce.sessionTagsInvalid":
    "Gib sowohl eine Bezeichnung als auch eine Ersetzung ein, um einen Alias hinzuzufügen.",
  "announce.locale": "Sprache: {language}.",
  "announce.weekStart": "Woche beginnt am {day}.",
  "announce.backupExported": "Sicherung exportiert.",
  "announce.backupRestored": "Sicherung wiederhergestellt.",
  "announce.backupFailed":
    "Wiederherstellung der Sicherung fehlgeschlagen. Deine Daten wurden nicht geändert.",
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
  "label.suggestionsLabel": "Etiquetas de sesión usadas anteriormente",
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
  "settings.dailyGoal": "Objetivo de concentración diario (minutos)",
  "settings.dailyGoalPlaceholder": "0 = sin objetivo",
  "settings.dailyGoalHint":
    "Minutos para hoy, opcionalmente limitados a la etiqueta seleccionada. Guardado solo en este dispositivo. Pon 0 para borrarlo.",
  "settings.clearDailyGoal": "Borrar objetivo diario",
  "settings.sessionTags": "Alias de etiquetas",
  "settings.sessionTagsHint":
    "Cambia el nombre de las etiquetas de sesión en todas las vistas sin modificar las sesiones que ya guardaste. Guardado solo en este dispositivo.",
  "settings.sessionTagsFrom": "Etiqueta original",
  "settings.sessionTagsTo": "Mostrar como",
  "settings.sessionTagsAdd": "Añadir alias",
  "settings.sessionTagsEntry": "{label} → {alias}",
  "settings.sessionTagsListLabel": "Alias de etiquetas actuales",
  "settings.sessionTagsEmpty": "Aún no hay alias de etiquetas.",
  "settings.sessionTagsRemove": "Quitar",
  "settings.sessionTagsRemoveLabel": "Quitar el alias de {label}",
  "settings.save": "Guardar ajustes",
  "settings.saved": "Guardado.",
  "settings.language": "Idioma",
  "settings.weekStart": "La semana comienza el",
  "settings.weekStartMonday": "lunes",
  "settings.weekStartSunday": "domingo",
  "settings.backup": "Copia de seguridad y restauración",
  "settings.backupHint":
    "Exporta una copia local en JSON de tus ajustes, tu historial y tus objetivos, o restaura una. Los archivos permanecen en este dispositivo.",
  "settings.exportBackup": "Exportar copia de seguridad",
  "settings.exportBackupHint":
    "Descarga un archivo JSON con tus ajustes, tu historial y tus objetivos. No se sube nada.",
  "settings.restoreBackup": "Restaurar copia de seguridad",
  "settings.restoreBackupHint":
    "Reemplaza tus datos locales con un archivo de copia de seguridad que elijas. No se sube nada.",
  "settings.restoreBackupFile": "Archivo de copia de seguridad que restaurar",
  "settings.backupInvalid":
    "Ese archivo no es una copia de seguridad de Focus Flow válida. Tus datos no se modificaron.",
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
  "stats.dailyGoal": "Objetivo diario",
  "stats.dailyGoalBarLabel": "Progreso del objetivo de concentración diario",
  "stats.dailyGoalReached": "✓ Objetivo diario alcanzado",
  "stats.goalBreakdown": "Por etiqueta esta semana",
  "stats.goalBreakdownLabel":
    "Minutos concentrados por etiqueta de sesión frente al objetivo semanal",
  "stats.goalBreakdownOne": "{count} etiqueta",
  "stats.goalBreakdownMany": "{count} etiquetas",
  "stats.goalLabelStats": "{minutes} · {percent} % del objetivo",
  "stats.goalPaceLabel": "Previsión del ritmo del objetivo semanal",
  "stats.goalPaceLine": "≈ {minutes}/día durante {days}",
  "stats.goalPaceDaysOne": "{count} día más",
  "stats.goalPaceDaysMany": "{count} días más",
  "stats.goalPaceOnTrack": "Al día",
  "stats.goalPaceBehind": "Por detrás del ritmo",
  "stats.trendHeading": "Tendencia de concentración",
  "stats.trendChartLabel": "Minutos concentrados por semana en las últimas 8 semanas",
  "stats.trendUp": "Tendencia al alza",
  "stats.trendDown": "Tendencia a la baja",
  "stats.trendFlat": "Estable",
  "stats.trendRange": "{min}–{max} min",
  "stats.trendEmpty": "Sin sesiones de concentración en las últimas semanas.",
  "stats.dailyTrendHeading": "Tendencia diaria de concentración",
  "stats.dailyTrendChartLabel": "Minutos concentrados por día en los últimos 14 días",
  "stats.dailyTrendUp": "Tendencia al alza",
  "stats.dailyTrendDown": "Tendencia a la baja",
  "stats.dailyTrendFlat": "Estable",
  "stats.dailyTrendRange": "{min}–{max} min",
  "stats.dailyTrendEmpty": "Sin sesiones de concentración en las últimas dos semanas.",
  "stats.heatmapHeading": "Mapa de concentración",
  "stats.heatmapLabel": "Minutos concentrados por día en las últimas 12 semanas",
  "stats.heatmapRange": "{min}–{max} min por día",
  "stats.heatmapDay": "{weekday} {month} {day}: {minutes} min",
  "stats.heatmapLess": "Menos",
  "stats.heatmapMore": "Más",
  "stats.heatmapEmpty":
    "Aún no hay sesiones de concentración: el mapa se irá completando mientras trabajas.",
  "stats.shareHeading": "Distribución del foco",
  "stats.shareChartLabel":
    "Proporción de los minutos de concentración de esta semana por etiqueta",
  "stats.shareSummary": "{minutes} · {labels}",
  "stats.shareLabelsOne": "{count} etiqueta",
  "stats.shareLabelsMany": "{count} etiquetas",
  "stats.shareSlice": "{label}: {minutes} · {percent} %",
  "stats.shareEmpty":
    "Aún no hay sesiones de concentración esta semana: la distribución se irá completando mientras trabajas.",
  "stats.dailyBreakdown": "Por etiqueta hoy",
  "stats.dailyBreakdownLabel":
    "Minutos concentrados por etiqueta de sesión frente al objetivo diario",
  "stats.dailyLabelStats": "{minutes} · {percent} % del objetivo diario",
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
  "announce.labelSuggestion": "Etiqueta: {label}.",
  "announce.streak": "Racha: {value}.",
  "announce.goalReached": "Objetivo semanal alcanzado.",
  "announce.goalBreakdown": "Objetivo semanal por etiqueta: {summary}.",
  "announce.goalPace": "Ritmo del objetivo semanal: {summary}.",
  "announce.trend": "Tendencia de concentración: {summary}.",
  "announce.dailyTrend": "Tendencia diaria de concentración: {summary}.",
  "announce.heatmap": "Mapa de concentración: {summary}.",
  "announce.share": "Distribución del foco: {summary}.",
  "announce.goalBreakdownScoped": "Objetivo semanal para {label}: {minutes}.",
  "announce.dailyBreakdown": "Objetivo diario por etiqueta: {summary}.",
  "announce.dailyBreakdownScoped": "Objetivo diario para {label}: {minutes}.",
  "announce.badge": "Insignia de la app: quedan {minutes}.",
  "announce.goalSaved": "Objetivo semanal guardado.",
  "announce.goalCleared": "Objetivo semanal borrado.",
  "announce.dailyGoalReached": "Objetivo diario alcanzado.",
  "announce.dailyGoalSaved": "Objetivo diario guardado.",
  "announce.dailyGoalCleared": "Objetivo diario borrado.",
  "announce.sessionTagsSaved":
    "Alias guardado: {label} ahora se muestra como {alias}.",
  "announce.sessionTagsRemoved": "Alias de {label} eliminado.",
  "announce.sessionTagsCleared": "Alias de {label} borrado.",
  "announce.sessionTagsInvalid":
    "Introduce una etiqueta y un reemplazo para añadir un alias.",
  "announce.locale": "Idioma: {language}.",
  "announce.weekStart": "La semana comienza el {day}.",
  "announce.backupExported": "Copia de seguridad exportada.",
  "announce.backupRestored": "Copia de seguridad restaurada.",
  "announce.backupFailed":
    "No se pudo restaurar la copia de seguridad. Tus datos no se modificaron.",
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
