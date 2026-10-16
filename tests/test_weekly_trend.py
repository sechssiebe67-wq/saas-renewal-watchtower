"""Tests for the Focus Flow ``weeklyTrend`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``weeklyTrend``, that
   ``app/index.html`` carries the sparkline markup, and that ``app/main.js``
   renders the chart and reads the new catalog keys.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``weeklyTrend`` helper is
   exercised against real history logs so the empty / single-week / rising /
   falling / flat shapes, the label filter, the alias map, the Sunday/Monday
   week start, and the daylight-saving boundary are verified for real. The
   harness runs with a ``TZ`` that observes daylight saving so the calendar
   arithmetic is genuinely tested.
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
    "stats.trendHeading",
    "stats.trendChartLabel",
    "stats.trendUp",
    "stats.trendDown",
    "stats.trendFlat",
    "stats.trendRange",
    "stats.trendEmpty",
    "announce.trend",
)

HARNESS = textwrap.dedent(
    """
    import { weeklyTrend, weekWindow, TREND_WEEKS } from "./history.mjs";

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

    // --- empty history ------------------------------------------------------
    const empty = weeklyTrend([], { now: Date.now(), weekStartsOn: 1 });
    check("default weeks is eight", empty.weeks === 8);
    check("empty has eight points", empty.points.length === 8);
    check("empty points are all zero", empty.points.every((p) => p.minutes === 0));
    check("empty min is zero", empty.min === 0);
    check("empty max is zero", empty.max === 0);
    check("empty direction is flat", empty.direction === "flat");
    check("empty flag is true", empty.empty === true);
    check(
      "points are chronological",
      empty.points.every(
        (point, index) =>
          index === 0 || point.weekStart > empty.points[index - 1].weekStart,
      ),
    );
    check(
      "points carry a YYYY-MM-DD weekStart string",
      empty.points.every(
        (point) =>
          typeof point.weekStart === "string" &&
          /^\\d{4}-\\d{2}-\\d{2}$/.test(point.weekStart),
      ),
    );

    // The default week count is exported as TREND_WEEKS.
    check("TREND_WEEKS is eight", TREND_WEEKS === 8);
    check(
      "weeks option is honoured",
      weeklyTrend([], { now: Date.now(), weeks: 3 }).weeks === 3,
    );
    check(
      "an invalid weeks option falls back to the default",
      weeklyTrend([], { now: Date.now(), weeks: "nope" }).weeks === 8,
    );
    check(
      "the weeks option is clamped to the upper bound",
      weeklyTrend([], { now: Date.now(), weeks: 100 }).weeks === 26,
    );
    check(
      "the weeks option is clamped to the lower bound",
      weeklyTrend([], { now: Date.now(), weeks: 0 }).weeks === 1,
    );
    check(
      "a fractional weeks option is floored",
      weeklyTrend([], { now: Date.now(), weeks: 6.9 }).weeks === 6,
    );

    // --- single week --------------------------------------------------------
    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026
    const single = weeklyTrend(
      [entry(now - 2 * HOUR, 25), entry(now - HOUR, 35)],
      { now, weeks: 1, weekStartsOn: 1 },
    );
    check("single week keeps one point", single.points.length === 1);
    check("single week sums its minutes", single.points[0].minutes === 60);
    check("single week is not empty", single.empty === false);
    check("single week direction is flat", single.direction === "flat");
    check("single week min equals max", single.min === 60 && single.max === 60);

    // --- window excludes older weeks ---------------------------------------
    const windowed = weeklyTrend(
      [entry(now - 60 * DAY, 500), entry(now - HOUR, 20)],
      { now, weeks: 4, weekStartsOn: 1 },
    );
    check("out-of-window entries are ignored", windowed.max === 20);
    check("in-window minutes are kept", windowed.points[3].minutes === 20);

    // --- rising / falling / flat -------------------------------------------
    function weeksAgo(weeksBack, minutes, label) {
      return entry(now - weeksBack * 7 * DAY, minutes, label);
    }
    const rising = weeklyTrend(
      [
        weeksAgo(3, 30),
        weeksAgo(2, 60),
        weeksAgo(1, 90),
        weeksAgo(0, 120),
      ],
      { now, weeks: 4, weekStartsOn: 1 },
    );
    check("rising direction is up", rising.direction === "up");
    check("rising min is the oldest week", rising.min === 30);
    check("rising max is the newest week", rising.max === 120);
    check("rising is not empty", rising.empty === false);

    const falling = weeklyTrend(
      [
        weeksAgo(3, 120),
        weeksAgo(2, 90),
        weeksAgo(1, 60),
        weeksAgo(0, 30),
      ],
      { now, weeks: 4, weekStartsOn: 1 },
    );
    check("falling direction is down", falling.direction === "down");

    const flat = weeklyTrend(
      [weeksAgo(2, 45), weeksAgo(1, 45), weeksAgo(0, 45)],
      { now, weeks: 3, weekStartsOn: 1 },
    );
    check("flat direction is flat", flat.direction === "flat");
    check("flat is not empty", flat.empty === false);

    // Direction compares the newest week with the week before it, not a fitted
    // slope: [120, 30, 60] is "up" (60 > 30) even though the slope is negative,
    // and [30, 60, 60] is "flat" (60 === 60).
    const latestRise = weeklyTrend(
      [weeksAgo(2, 120), weeksAgo(1, 30), weeksAgo(0, 60)],
      { now, weeks: 3, weekStartsOn: 1 },
    );
    check("direction compares the latest week", latestRise.direction === "up");
    const latestFlat = weeklyTrend(
      [weeksAgo(2, 30), weeksAgo(1, 60), weeksAgo(0, 60)],
      { now, weeks: 3, weekStartsOn: 1 },
    );
    check("an unchanged latest week is flat", latestFlat.direction === "flat");
    const latestFall = weeklyTrend(
      [weeksAgo(2, 30), weeksAgo(1, 90), weeksAgo(0, 60)],
      { now, weeks: 3, weekStartsOn: 1 },
    );
    check("a smaller latest week is down", latestFall.direction === "down");

    // --- label filter -------------------------------------------------------
    const filtered = weeklyTrend(
      [
        weeksAgo(1, 40, "Thesis"),
        weeksAgo(1, 10, "Admin"),
        weeksAgo(0, 15, "Thesis"),
      ],
      { now, weeks: 2, weekStartsOn: 1, label: "Thesis" },
    );
    check("label filter keeps only the matching label", filtered.max === 40);
    check("label filter sums the newer matching week", filtered.points[1].minutes === 15);

    const unlabelled = weeklyTrend(
      [entry(now - DAY, 5), entry(now - DAY, 7, "Thesis")],
      { now, weeks: 1, weekStartsOn: 1, label: "(unlabelled)" },
    );
    check("the unlabelled filter matches unlabelled entries", unlabelled.max === 5);

    // --- aliases ------------------------------------------------------------
    const aliased = weeklyTrend(
      [weeksAgo(0, 50, "Thesis"), weeksAgo(0, 20, "Admin")],
      {
        now,
        weeks: 1,
        weekStartsOn: 1,
        label: "PhD",
        tags: { Thesis: "PhD" },
      },
    );
    check("an aliased label filter finds its sessions", aliased.max === 50);

    // --- Sunday vs Monday week start ---------------------------------------
    // "Now" is Monday 15 June 2026 and the session is the previous day, Sunday
    // 14 June. A Sunday-first week puts it in the current (newest) bucket; a
    // Monday-first week puts it in the previous bucket.
    const mondayNow = new Date(2026, 5, 15, 12, 0, 0).getTime();
    const sundayEntry = entry(new Date(2026, 5, 14, 6, 0, 0).getTime(), 30);
    const sundayStart = weeklyTrend([sundayEntry], {
      now: mondayNow,
      weeks: 2,
      weekStartsOn: 0,
    });
    const mondayStart = weeklyTrend([sundayEntry], {
      now: mondayNow,
      weeks: 2,
      weekStartsOn: 1,
    });
    check(
      "a Sunday start puts Sunday in the newest bucket",
      sundayStart.points[1].minutes === 30 && sundayStart.points[0].minutes === 0,
    );
    check(
      "a Monday start puts Sunday in the previous bucket",
      mondayStart.points[0].minutes === 30 && mondayStart.points[1].minutes === 0,
    );
    check(
      "the weekStart option name is also accepted",
      weeklyTrend([sundayEntry], { now: mondayNow, weeks: 2, weekStart: 1 })
        .points[0].minutes === 30,
    );

    // --- daylight-saving boundary ------------------------------------------
    // The US spring-forward is Sunday 8 March 2026; for a Monday-start week the
    // bucket 2..8 March is only 167 wall-clock hours. Calendar arithmetic must
    // still keep both boundary entries in that bucket.
    const dst = weeklyTrend(
      [
        entry(new Date(2026, 2, 2, 0, 30).getTime(), 15),
        entry(new Date(2026, 2, 8, 23, 30).getTime(), 25),
        entry(new Date(2026, 2, 9, 0, 30).getTime(), 99), // next week, excluded
      ],
      {
        now: new Date(2026, 2, 4, 12, 0, 0).getTime(),
        weeks: 2,
        weekStartsOn: 1,
      },
    );
    check("DST bucket keeps both boundary entries", dst.points[1].minutes === 40);
    check("DST does not leak the next week", dst.max === 40);
    check(
      "DST bucket starts on the local Monday",
      dst.points[1].weekStart === "2026-03-02",
    );

    // --- robustness ---------------------------------------------------------
    const malformed = [null, undefined, {}, [], 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = weeklyTrend(value, { now, weekStartsOn: 1 });
      } catch (error) {
        threw = true;
      }
      check("weeklyTrend(" + String(value) + ") does not throw", !threw);
      check(
        "weeklyTrend(" + String(value) + ") is empty",
        !threw && result.empty === true,
      );
    }
    check(
      "malformed entries are ignored",
      weeklyTrend(
        [42, "x", { phase: "break", durationSeconds: 60 }],
        { now, weeks: 1 },
      ).empty === true,
    );
    check(
      "weeklyTrend survives a malformed now",
      weeklyTrend([], { now: "not-a-date", weeks: 1 }).weeks === 1,
    );

    const frozen = [entry(now - HOUR, 30, "Thesis")];
    const snapshot = JSON.stringify(frozen);
    const tags = { Thesis: "PhD" };
    const tagsSnapshot = JSON.stringify(tags);
    weeklyTrend(frozen, { now, weekStartsOn: 1, tags });
    check("weeklyTrend never mutates its log", JSON.stringify(frozen) === snapshot);
    check("weeklyTrend never mutates tags", JSON.stringify(tags) === tagsSnapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class WeeklyTrendStaticTests(unittest.TestCase):
    def test_history_exports_weekly_trend(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+weeklyTrend\b",
            "history.js does not export weeklyTrend",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_sparkline(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-trend"', html)
        self.assertIn('id="stats-trend-chart"', html)
        self.assertIn('role="img"', html)
        self.assertIn("data-i18n-attr=\"aria-label:stats.trendChartLabel\"", html)
        self.assertIn('data-i18n="stats.trendEmpty"', html)

    def test_main_js_renders_the_trend(self):
        js = read(MAIN_PATH)
        self.assertIn("weeklyTrend", js)
        self.assertIn("renderTrend", js)
        self.assertIn("renderTrendChart", js)
        self.assertIn("stats-trend-chart", js)
        self.assertIn("announce.trend", js)
        self.assertIn("lastAnnouncedTrendDirection", js)

    def test_styles_define_the_sparkline(self):
        css = read(STYLES_PATH)
        self.assertIn(".stats__trend-chart", css)
        self.assertIn(".stats__trend-line", css)
        self.assertIn(".stats__trend-dot", css)


class WeeklyTrendI18nTests(unittest.TestCase):
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
class WeeklyTrendLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-weekly-trend-")
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

        # Run in a time zone that observes daylight saving so the calendar
        # arithmetic is genuinely exercised at the DST boundary.
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
            "weeklyTrend logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
