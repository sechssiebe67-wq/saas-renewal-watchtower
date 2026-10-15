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
        self.assertEqual(html.count("<button"), 5)
        self.assertIn('type="button"', html)

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

    def test_main_js_references_history_module(self):
        js = read_app_file("main.js")
        self.assertIn("./history.js", js)
        self.assertIn('"focus-flow:history"', js)
        for symbol in ("recordSession", "pruneHistory", "summarise"):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

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
