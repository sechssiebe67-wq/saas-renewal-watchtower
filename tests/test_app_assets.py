"""Static product tests for the Focus Flow web app.

These tests do not need a browser or any JavaScript runtime: they assert that
the static assets exist and that the markup, styles and scripts contain the
structural elements the product relies on.
"""

import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "app")


def read_app_file(name):
    path = os.path.join(APP_DIR, name)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class AppAssetTests(unittest.TestCase):
    def test_required_assets_exist(self):
        for name in (
            "index.html",
            "styles.css",
            "main.js",
            "timer.js",
            "history.js",
            "ambient.js",
            "i18n.js",
            "healthz",
            "manifest.webmanifest",
            "service-worker.js",
            "icons/icon-192.png",
            "icons/icon-512.png",
            "icons/icon-maskable-512.png",
        ):
            path = os.path.join(APP_DIR, name)
            self.assertTrue(os.path.isfile(path), "missing app asset: %s" % name)

    def test_html_links_manifest_and_theme_color(self):
        html = read_app_file("index.html")
        self.assertIn('rel="manifest"', html)
        self.assertIn('href="manifest.webmanifest"', html)
        self.assertIn('name="theme-color"', html)

    def test_main_js_registers_service_worker(self):
        js = read_app_file("main.js")
        self.assertIn("registerServiceWorker", js)
        self.assertIn('"serviceWorker" in navigator', js)
        self.assertIn("./service-worker.js", js)
        self.assertIn("console.warn", js)

    def test_healthz_reports_ok(self):
        self.assertEqual(read_app_file("healthz").strip(), "ok")

    def test_html_has_semantic_landmarks(self):
        html = read_app_file("index.html")
        for fragment in ("<header", "<main", "<footer", "<section", "<h1"):
            self.assertIn(fragment, html, "missing landmark: %s" % fragment)

    def test_html_has_timer_display_and_controls(self):
        html = read_app_file("index.html")
        expectations = {
            "timer display": 'id="timer-display"',
            "phase label": 'id="phase-label"',
            "session counter": 'id="session-count"',
            "start/pause control": 'id="start-pause"',
            "reset control": 'id="reset"',
            "skip control": 'id="skip"',
            "settings form": 'id="settings-form"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))

    def test_html_has_aria_live_region_for_timer(self):
        html = read_app_file("index.html")
        self.assertIn('aria-live="polite"', html)
        self.assertIn('id="timer-announcer"', html)

    def test_controls_are_real_buttons(self):
        html = read_app_file("index.html")
        self.assertEqual(html.count("<button"), 10)
        self.assertIn('type="button"', html)
        self.assertIn('id="review-export"', html)
        self.assertIn('id="backup-export"', html)
        self.assertIn('id="backup-restore"', html)

    def test_settings_expose_configurable_durations(self):
        html = read_app_file("index.html")
        for field in (
            "work-duration",
            "short-break-duration",
            "long-break-duration",
            "long-break-interval",
        ):
            self.assertIn('id="%s"' % field, html, "missing setting: %s" % field)

    def test_styles_are_accessible_and_responsive(self):
        css = read_app_file("styles.css")
        checks = {
            "focus-visible outline": ":focus-visible",
            "visually hidden helper": ".visually-hidden",
            "responsive breakpoint": "@media (min-width: 768px)",
            "dark theme": '[data-theme="dark"]',
            "reduced motion": "prefers-reduced-motion",
        }
        for label, fragment in checks.items():
            self.assertIn(fragment, css, "missing CSS %s" % label)

    def test_main_js_persists_and_handles_shortcuts(self):
        js = read_app_file("main.js")
        self.assertIn("localStorage", js)
        self.assertIn("STORAGE_KEYS", js)
        self.assertIn('"Space"', js)
        for key in ('"r"', '"R"', '"s"', '"S"'):
            self.assertIn(key, js, "missing keyboard shortcut: %s" % key)

    def test_html_has_stats_section(self):
        html = read_app_file("index.html")
        expectations = {
            "stats section": 'id="stats"',
            "stats heading": 'id="stats-heading"',
            "stats total sessions": 'id="stats-total-sessions"',
            "stats total minutes": 'id="stats-total-minutes"',
            "stats day list": 'id="stats-days"',
            "stats empty state": 'id="stats-empty"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn("No sessions yet", html)

    def test_html_has_session_label_and_stats_tagging(self):
        html = read_app_file("index.html")
        expectations = {
            "session label input": 'id="session-label"',
            "stats label chips": 'id="stats-labels"',
            "stats recent list": 'id="stats-recent"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn('maxlength="40"', html)
        self.assertIn("on this device", html)

    def test_html_has_ambient_controls(self):
        html = read_app_file("index.html")
        expectations = {
            "ambient type select": 'id="ambient-type"',
            "ambient volume slider": 'id="ambient-volume"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        for option in ("off", "brown", "pink", "rain"):
            self.assertRegex(html, r'value="%s"' % option)
        self.assertIn('type="range"', html)
        self.assertIn('min="0"', html)
        self.assertIn('max="1"', html)
        self.assertIn('step="0.05"', html)
        self.assertIn('for="ambient-type"', html)
        self.assertIn('for="ambient-volume"', html)
        self.assertIn("stored only on this device", html)
        self.assertIn("Web Audio API", html)

    def test_main_js_references_ambient_module(self):
        js = read_app_file("main.js")
        self.assertIn("./ambient.js", js)
        self.assertIn('"focus-flow:ambient"', js)
        for symbol in (
            "normalizeAmbient",
            "createNoiseBuffer",
            "shouldPlay",
            "DEFAULT_AMBIENT",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_main_js_references_history_module(self):
        js = read_app_file("main.js")
        self.assertIn("./history.js", js)
        self.assertIn('"focus-flow:history"', js)
        for symbol in (
            "recordSession",
            "pruneHistory",
            "summarise",
            "labelSummary",
            "recentSessions",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_html_has_weekly_goal_field_and_progressbar(self):
        html = read_app_file("index.html")
        expectations = {
            "weekly goal field": 'id="weekly-goal"',
            "stats goal region": 'id="stats-goal"',
            "goal progressbar": 'id="stats-goal-bar"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn('role="progressbar"', html)
        self.assertIn("aria-valuenow", html)
        self.assertIn("aria-valuemin", html)
        self.assertIn("aria-valuemax", html)
        self.assertIn('min="0"', html)
        self.assertIn('max="10080"', html)
        self.assertIn('step="15"', html)

    def test_main_js_uses_goal_helpers_and_storage(self):
        js = read_app_file("main.js")
        self.assertIn('"focus-flow:goal"', js)
        self.assertIn("goalProgress", js)
        self.assertIn("normalizeGoal", js)
        self.assertIn("announce.goalReached", js)

    def test_html_has_daily_goal_field_and_progressbar(self):
        html = read_app_file("index.html")
        expectations = {
            "daily goal field": 'id="daily-goal"',
            "clear daily goal control": 'id="clear-daily-goal"',
            "stats daily goal region": 'id="stats-daily-goal"',
            "stats daily goal bar": 'id="stats-daily-goal-bar"',
            "stats daily goal reached": 'id="stats-daily-goal-reached"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn('name="dailyGoal"', html)
        self.assertIn('max="1440"', html)
        self.assertIn('role="progressbar"', html)
        self.assertIn("aria-valuenow", html)
        self.assertRegex(
            html,
            r'<div\s+id="stats-daily-goal"[\s\S]*?hidden',
            "the stats daily goal row must start hidden",
        )

    def test_main_js_uses_daily_goal_helpers_and_storage(self):
        js = read_app_file("main.js")
        self.assertIn('"focus-flow:daily-goal"', js)
        self.assertIn("dailyGoalProgress", js)
        self.assertIn("normalizeDailyGoal", js)
        self.assertIn("renderDailyGoal", js)
        self.assertIn("announce.dailyGoalReached", js)

    def test_html_has_stats_goal_breakdown(self):
        html = read_app_file("index.html")
        expectations = {
            "goal breakdown title": 'id="stats-goal-breakdown-title"',
            "goal breakdown list": 'id="stats-goal-breakdown"',
            "goal breakdown heading hook": 'data-i18n="stats.goalBreakdown"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn('data-i18n-attr="aria-label:stats.goalBreakdownLabel"', html)
        self.assertIn('id="stats-goal"', html)
        self.assertRegex(
            html,
            r'<ul\s+id="stats-goal-breakdown"[\s\S]*?hidden',
            "the goal breakdown list must start hidden",
        )

    def test_main_js_renders_goal_breakdown(self):
        js = read_app_file("main.js")
        for symbol in (
            "renderGoalBreakdown",
            "hideGoalBreakdown",
            "stats-goal-breakdown",
            "stats.goalLabelStats",
            "announce.goalBreakdown",
            "announce.goalBreakdownScoped",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_html_has_weekly_review_section(self):
        html = read_app_file("index.html")
        expectations = {
            "weekly review section": 'id="weekly-review"',
            "weekly review heading": 'id="weekly-review-heading"',
            "weekly review summary": 'id="weekly-review-summary"',
            "weekly review progressbar": 'id="weekly-review-bar"',
            "weekly review label list": 'id="weekly-review-labels"',
            "weekly review empty state": 'id="weekly-review-empty"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "missing %s (%s)" % (label, fragment))
        self.assertIn('role="progressbar"', html)
        self.assertIn("aria-valuenow", html)
        self.assertIn("aria-valuemin", html)
        self.assertIn("aria-valuemax", html)
        self.assertIn("No sessions yet this week", html)

    def test_main_js_uses_weekly_review_helper(self):
        js = read_app_file("main.js")
        self.assertIn("weeklyReview", js)
        self.assertIn("renderWeeklyReview", js)

    def test_main_js_clears_label_only_on_completed_work(self):
        js = read_app_file("main.js")
        self.assertIn("session-label", js)
        self.assertIn("labelSummary", js)
        self.assertIn("recentSessions", js)
        self.assertIn("skipped === false", js)

    def test_timer_engine_implements_state_machine(self):
        js = read_app_file("timer.js")
        for fragment in (
            "PHASES",
            "WORK",
            "SHORT_BREAK",
            "LONG_BREAK",
            "longBreakInterval",
            "completedWorkSessions",
            "formatTime",
        ):
            self.assertIn(fragment, js, "timer engine missing: %s" % fragment)


class ContainerAssetTests(unittest.TestCase):
    def test_dockerfile_exists(self):
        self.assertTrue(
            os.path.isfile(os.path.join(REPO_ROOT, "Dockerfile")),
            "missing Dockerfile",
        )

    def test_dockerfile_serves_app_and_healthcheck(self):
        with open(os.path.join(REPO_ROOT, "Dockerfile"), encoding="utf-8") as handle:
            dockerfile = handle.read()
        self.assertIn("COPY app/", dockerfile)
        self.assertIn("/healthz", dockerfile)
        self.assertIn("nginx", dockerfile.lower())
        self.assertIn("PORT", dockerfile)


if __name__ == "__main__":
    unittest.main()
