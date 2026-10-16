"""Tests for the Focus Flow ``focusTrend`` helper and the Stats sparkline.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``focusTrend`` and stays
   DOM-, storage-, and network-free, that ``app/index.html`` carries the
   sparkline markup, and that ``app/main.js`` renders it and reads the new
   catalog keys.
2. A static check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``focusTrend`` helper is
   exercised against real history so the trailing window, the label filter, the
   alias application, and the ``empty`` / ``max`` / ``min`` / ``totalMinutes``
   values are verified for real.
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
NODE_BIN = shutil.which("node")

NEW_I18N_KEYS = (
    "stats.trendHeading",
    "stats.trendLabel",
    "stats.trendSummary",
    "stats.trendHighest",
    "stats.trendLowest",
    "stats.trendEmpty",
    "announce.trend",
)

HARNESS = textwrap.dedent(
    """
    import { focusTrend, UNLABELLED } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const DAY = 24 * HOUR;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    // Monday 15 June 2026, midday.
    const now = new Date(2026, 5, 15, 12, 0, 0).getTime();

    function at(dayOffset, hour = 9) {
      return new Date(2026, 5, 15 + dayOffset, hour, 0, 0).getTime();
    }

    function entry(timestamp, durationMinutes, label) {
      const value = {
        endedAt: new Date(timestamp).toISOString(),
        phase: "work",
        durationSeconds: durationMinutes * 60,
      };
      if (label !== undefined) value.label = label;
      return value;
    }

    // --- empty window -------------------------------------------------------
    const empty = focusTrend([], { now });
    check("empty returns an object", empty && typeof empty === "object");
    check("empty is true", empty.empty === true);
    check("empty keeps the day count", empty.days === 7);
    check(
      "empty has seven zero-filled points",
      Array.isArray(empty.points) &&
        empty.points.length === 7 &&
        empty.points.every((point) => point.minutes === 0),
    );
    check("empty max is 0", empty.max === 0);
    check("empty min is 0", empty.min === 0);
    check("empty total is 0", empty.totalMinutes === 0);

    const dates = empty.points.map((point) => point.date);
    check(
      "points are chronological",
      JSON.stringify(dates) === JSON.stringify(dates.slice().sort()),
    );
    check(
      "points carry YYYY-MM-DD dates",
      dates.every((date) => /^\\d{4}-\\d{2}-\\d{2}$/.test(date)),
    );

    // --- single day ---------------------------------------------------------
    const single = focusTrend([entry(at(0), 25)], { now });
    check("single day is not empty", single.empty === false);
    check("single day total", single.totalMinutes === 25);
    check("single day max", single.max === 25);
    check("single day min", single.min === 0);
    check("single day lands on today", single.points[6].minutes === 25);
    check(
      "single day leaves the other days at zero",
      single.points.slice(0, 6).every((point) => point.minutes === 0),
    );

    // --- multiple days ------------------------------------------------------
    const multi = focusTrend(
      [entry(at(0), 30), entry(at(-1), 10), entry(at(-3), 50)],
      { now },
    );
    check("multi-day total", multi.totalMinutes === 90);
    check("multi-day max", multi.max === 50);
    check("multi-day min", multi.min === 0);
    check("multi-day today bucket", multi.points[6].minutes === 30);
    check("multi-day yesterday bucket", multi.points[5].minutes === 10);
    check("multi-day older bucket", multi.points[3].minutes === 50);

    // --- seconds are rounded to whole minutes -------------------------------
    const rounded = focusTrend([entry(at(0), 0.7)], { now });
    check("seconds round up to a whole minute", rounded.totalMinutes === 1);

    // --- entries outside the window are ignored -----------------------------
    const outside = focusTrend(
      [
        entry(at(0), 20),
        {
          endedAt: new Date(now - 8 * DAY).toISOString(),
          phase: "work",
          durationSeconds: 10 * 60,
        },
      ],
      { now },
    );
    check("an older entry is outside the window", outside.totalMinutes === 20);

    // --- breaks and malformed entries are ignored ---------------------------
    const breaks = focusTrend(
      [
        {
          endedAt: new Date(at(0)).toISOString(),
          phase: "shortBreak",
          durationSeconds: 300,
        },
      ],
      { now },
    );
    check("breaks do not count", breaks.empty === true);

    // --- label filter -------------------------------------------------------
    const labeled = [
      entry(at(0), 30, "Thesis"),
      entry(at(0), 20, "Admin"),
      entry(at(-1), 40),
    ];
    const onlyThesis = focusTrend(labeled, { now, label: "Thesis" });
    check("label filter total", onlyThesis.totalMinutes === 30);
    check("label filter is not empty", onlyThesis.empty === false);
    const unlabelled = focusTrend(labeled, { now, label: UNLABELLED });
    check("unlabelled filter total", unlabelled.totalMinutes === 40);
    const unknown = focusTrend(labeled, { now, label: "Nope" });
    check("an unknown label is empty", unknown.empty === true);

    // --- alias application --------------------------------------------------
    const tags = { Thesis: "PhD" };
    const aliased = focusTrend(labeled, { now, label: "PhD", tags });
    check("the alias filter matches the stored label", aliased.totalMinutes === 30);
    const aliasedUnfiltered = focusTrend(labeled, { now, tags });
    check(
      "aliases do not change an unfiltered total",
      aliasedUnfiltered.totalMinutes === 90,
    );

    // --- purity -------------------------------------------------------------
    const snapshot = JSON.stringify(labeled);
    focusTrend(labeled, { now, tags, label: "PhD" });
    check("input is never mutated", JSON.stringify(labeled) === snapshot);

    for (const value of [
      null,
      undefined,
      42,
      "nope",
      [null, 7, {}],
      [{ endedAt: "bad", phase: "work", durationSeconds: 600 }],
    ]) {
      let threw = false;
      let result;
      try {
        result = focusTrend(value, { now });
      } catch (error) {
        threw = true;
      }
      check("malformed history does not throw", !threw);
      check(
        "malformed history still returns points",
        !threw && result && Array.isArray(result.points),
      );
    }

    // --- custom window size -------------------------------------------------
    const five = focusTrend([entry(at(0), 10)], { now, days: 5 });
    check("custom window size", five.days === 5 && five.points.length === 5);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class FocusTrendStaticTests(unittest.TestCase):
    def test_history_exports_focus_trend(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+focusTrend\b",
            "history.js does not export focusTrend",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"document|window", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_trend_sparkline(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-trend"', html)
        self.assertIn('id="stats-trend-svg"', html)
        self.assertIn('id="stats-trend-line"', html)
        self.assertIn('id="stats-trend-summary"', html)
        self.assertIn('role="img"', html)
        self.assertIn('aria-labelledby="stats-trend-heading"', html)
        self.assertIn('data-i18n="stats.trendHeading"', html)
        self.assertIn('data-i18n-attr="aria-label:stats.trendLabel"', html)
        self.assertIn('class="stats__trend-summary visually-hidden"', html)
        self.assertRegex(
            html,
            r'<figure\s+id="stats-trend"[\s\S]*?hidden',
            "the trend section must start hidden",
        )

    def test_main_js_renders_trend(self):
        js = read(MAIN_PATH)
        for symbol in (
            "focusTrend",
            "renderFocusTrend",
            "trendPointsAttribute",
            "stats-trend-line",
            "stats-trend-summary",
            "stats.trendSummary",
            "announce.trend",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_main_js_resets_trend_announcements(self):
        js = read(MAIN_PATH)
        self.assertGreaterEqual(
            js.count("announcedTrend = false;"),
            4,
            "the trend must re-announce on filter, language, week-start, and aliases",
        )


class FocusTrendI18nTests(unittest.TestCase):
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

    def test_new_keys_have_real_translations(self):
        # Every key must resolve to a real string in each locale rather than
        # falling back to the key itself.
        source = read(I18N_PATH)
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            block = self._locale_block(source, name)
            for key in NEW_I18N_KEYS:
                match = re.search(
                    r'"%s":\s*"((?:[^"\\]|\\.)*)"' % re.escape(key),
                    block,
                )
                self.assertIsNotNone(
                    match,
                    "%s has no string value for %s" % (name, key),
                )
                value = match.group(1)
                self.assertTrue(
                    value.strip(),
                    "%s has an empty value for %s" % (name, key),
                )
                self.assertNotEqual(
                    value,
                    key,
                    "%s falls back to the key for %s" % (name, key),
                )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class FocusTrendLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-trend-")
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

        # A fixed time zone keeps the local calendar-day arithmetic
        # deterministic and free of daylight-saving noise.
        env = dict(os.environ, TZ="UTC")
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
            "focusTrend logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
