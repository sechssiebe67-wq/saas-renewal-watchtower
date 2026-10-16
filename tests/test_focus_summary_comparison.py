"""Tests for the Focus Flow ``focusSummaryComparison`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``focusSummaryComparison``,
   that ``app/index.html`` carries the per-label comparison markup, that
   ``app/main.js`` renders the extra line and reads the new catalog keys, and
   that ``app/styles.css`` styles it.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``focusSummaryComparison``
   helper is exercised against real ``focusSummary`` results so the null /
   scoped / malformed shapes and the trend pass-through are verified for real,
   and ``focusSummary``'s no-label output is checked to stay unchanged.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from history_harness_support import copy_history_dependencies

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "app")
HISTORY_PATH = os.path.join(APP_DIR, "history.js")
I18N_PATH = os.path.join(APP_DIR, "i18n.js")
INDEX_PATH = os.path.join(APP_DIR, "index.html")
MAIN_PATH = os.path.join(APP_DIR, "main.js")
STYLES_PATH = os.path.join(APP_DIR, "styles.css")
NODE_BIN = shutil.which("node")

NEW_I18N_KEYS = (
    "stats.summaryScopedUp",
    "stats.summaryScopedDown",
    "stats.summaryScopedSteady",
    "announce.summaryScoped",
)

HARNESS = textwrap.dedent(
    """
    import { focusSummary, focusSummaryComparison } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const DAY = 24 * HOUR;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function iso(timestamp) {
      return new Date(timestamp).toISOString();
    }

    function entry(timestamp, minutes, label) {
      const row = {
        endedAt: iso(timestamp),
        phase: "work",
        durationSeconds: minutes * 60,
      };
      if (label !== undefined) row.label = label;
      return row;
    }

    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026

    // --- no label means no comparison --------------------------------------
    const summary = focusSummary([entry(now - HOUR, 30, "Thesis")], { now });
    check(
      "no label yields null",
      focusSummaryComparison(summary, {}) === null,
    );
    check(
      "an empty label yields null",
      focusSummaryComparison(summary, { label: "" }) === null,
    );
    check(
      "a null label yields null",
      focusSummaryComparison(summary, { label: null }) === null,
    );

    // --- the scoped summary is echoed back ---------------------------------
    const log = [
      entry(now - 40 * DAY, 100, "Thesis"),
      entry(now - HOUR, 300, "Thesis"),
      entry(now - HOUR, 50, "Admin"),
    ];
    const scopedSummary = focusSummary(log, { now, label: "Thesis" });
    const comparison = focusSummaryComparison(scopedSummary, {
      label: "Thesis",
    });
    check("the comparison is an object", comparison !== null);
    check(
      "the comparison keeps the window sessions",
      comparison.window.sessions === scopedSummary.window.sessions,
    );
    check(
      "the comparison keeps the window minutes",
      comparison.window.minutes === scopedSummary.window.minutes,
    );
    check(
      "the comparison keeps the all-time sessions",
      comparison.allTime.sessions === scopedSummary.allTime.sessions,
    );
    check(
      "the comparison keeps the all-time minutes",
      comparison.allTime.minutes === scopedSummary.allTime.minutes,
    );
    check(
      "the comparison keeps the trend",
      comparison.trend === scopedSummary.trend,
    );
    check(
      "the label filter scoped the window to one session",
      comparison.window.sessions === 1,
    );
    check(
      "the label filter kept the earlier session all-time",
      comparison.allTime.sessions === 2,
    );

    // --- a raw log is scoped with the same label rules ---------------------
    const fromLog = focusSummaryComparison(log, { label: "Thesis", now });
    check(
      "a raw log is scoped to the label window",
      fromLog.window.sessions === 1,
    );
    check(
      "a raw log keeps the earlier label session all-time",
      fromLog.allTime.sessions === 2,
    );
    const aliased = focusSummaryComparison(log, {
      label: "PhD",
      tags: { Thesis: "PhD" },
      now,
    });
    check(
      "an aliased label finds its sessions in a raw log",
      aliased.window.sessions === 1 && aliased.allTime.sessions === 2,
    );

    // --- a rising label trends up ------------------------------------------
    const rising = focusSummary(
      [entry(now - 60 * DAY, 1, "Thesis"), entry(now - HOUR, 900, "Thesis")],
      { now, label: "Thesis" },
    );
    check(
      "a rising label trends up",
      focusSummaryComparison(rising, { label: "Thesis" }).trend === "up",
    );

    // --- malformed input never throws --------------------------------------
    const emptyLog = focusSummaryComparison([], { label: "Thesis" });
    check(
      "an empty log yields an empty comparison",
      emptyLog.window.sessions === 0 &&
        emptyLog.allTime.sessions === 0 &&
        emptyLog.trend === "steady",
    );

    const malformed = [null, undefined, {}, 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = focusSummaryComparison(value, { label: "Thesis" });
      } catch (error) {
        threw = true;
      }
      check(
        "focusSummaryComparison(" + String(value) + ") does not throw",
        !threw,
      );
      check(
        "focusSummaryComparison(" + String(value) + ") is zeroed and steady",
        !threw &&
          result.window.sessions === 0 &&
          result.window.minutes === 0 &&
          result.window.days === 0 &&
          result.window.perDayMinutes === 0 &&
          result.allTime.sessions === 0 &&
          result.allTime.minutes === 0 &&
          result.allTime.days === 0 &&
          result.allTime.perDayMinutes === 0 &&
          result.trend === "steady",
      );
    }

    // --- focusSummary without a label is unchanged -------------------------
    const untouched = focusSummary([entry(now - HOUR, 30, "Thesis")], { now });
    check(
      "focusSummary still returns exactly its three keys",
      JSON.stringify(Object.keys(untouched).sort()) ===
        JSON.stringify(["allTime", "trend", "window"]),
    );
    check(
      "focusSummary still carries the four scoped fields",
      JSON.stringify(Object.keys(untouched.window).sort()) ===
        JSON.stringify(["days", "minutes", "perDayMinutes", "sessions"]),
    );

    // --- the helper never mutates its input --------------------------------
    const frozen = focusSummary([entry(now - HOUR, 30, "Thesis")], {
      now,
      label: "Thesis",
    });
    const snapshot = JSON.stringify(frozen);
    focusSummaryComparison(frozen, { label: "Thesis" });
    check(
      "focusSummaryComparison never mutates its summary",
      JSON.stringify(frozen) === snapshot,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class FocusSummaryComparisonStaticTests(unittest.TestCase):
    def test_history_exports_the_helper(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+focusSummaryComparison\b",
            "history.js does not export focusSummaryComparison",
        )

    def test_index_html_has_the_scoped_line(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-summary-scoped"', html)
        self.assertIn("stats__summary-scoped", html)

    def test_main_js_renders_the_scoped_line(self):
        js = read(MAIN_PATH)
        for symbol in (
            "focusSummaryComparison",
            "stats-summary-scoped",
            "stats.summaryScopedUp",
            "stats.summaryScopedDown",
            "stats.summaryScopedSteady",
            "announce.summaryScoped",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_styles_define_the_scoped_line(self):
        css = read(STYLES_PATH)
        self.assertIn(".stats__summary-scoped", css)


class FocusSummaryComparisonI18nTests(unittest.TestCase):
    @staticmethod
    def _locale_block(source, name):
        match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
        if not match:
            raise AssertionError("could not find %s in i18n.js" % name)
        return match.group(1)

    def test_new_keys_present_in_every_locale(self):
        source = read(I18N_PATH)
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            block = self._locale_block(source, name)
            for key in NEW_I18N_KEYS:
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class FocusSummaryComparisonLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-summary-comparison-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        with open(
            os.path.join(cls.tmp_dir, "history.mjs"), "w", encoding="utf-8"
        ) as handle:
            handle.write(source)
        copy_history_dependencies(cls.tmp_dir)
        harness_path = os.path.join(cls.tmp_dir, "harness.mjs")
        with open(harness_path, "w", encoding="utf-8") as handle:
            handle.write(HARNESS)

        env = dict(os.environ, TZ="America/New_York")
        result = subprocess.run(
            [NODE_BIN, harness_path],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise AssertionError(
                "node harness failed (exit %s):\n%s\n%s"
                % (result.returncode, result.stdout, result.stderr)
            )
        cls.payload = json.loads(result.stdout)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_pure_logic(self):
        self.assertEqual(
            self.payload["failures"],
            [],
            "focusSummaryComparison logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
