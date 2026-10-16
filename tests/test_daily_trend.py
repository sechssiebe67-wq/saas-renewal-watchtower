"""Tests for the Focus Flow ``dailyTrend`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``dailyTrend``, that
   ``app/index.html`` carries the sparkline markup, and that ``app/main.js``
   renders the chart and reads the new catalog keys.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``dailyTrend`` helper is
   exercised against real history logs so the empty / single-day / rising /
   falling / flat shapes, the label filter, the alias map, and the
   daylight-saving boundary (23h and 25h days) are verified for real. The
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
    "stats.dailyTrendHeading",
    "stats.dailyTrendChartLabel",
    "stats.dailyTrendUp",
    "stats.dailyTrendDown",
    "stats.dailyTrendFlat",
    "stats.dailyTrendRange",
    "stats.dailyTrendEmpty",
    "announce.dailyTrend",
)

HARNESS = textwrap.dedent(
    """
    import { dailyTrend, DAILY_TREND_DAYS, MAX_DAILY_TREND_DAYS } from "./history.mjs";

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
    const empty = dailyTrend([], { now: Date.now() });
    check("default days is fourteen", empty.points.length === 14);
    check("DAILY_TREND_DAYS is fourteen", DAILY_TREND_DAYS === 14);
    check("MAX_DAILY_TREND_DAYS is ninety", MAX_DAILY_TREND_DAYS === 90);
    check("empty points are all zero", empty.points.every((p) => p.minutes === 0));
    check("empty min is zero", empty.min === 0);
    check("empty max is zero", empty.max === 0);
    check("empty direction is flat", empty.direction === "flat");
    check("empty flag is true", empty.empty === true);
    check("points are an array", Array.isArray(empty.points));
    check(
      "points are chronological",
      empty.points.every(
        (point, index) =>
          index === 0 || point.date > empty.points[index - 1].date,
      ),
    );
    check(
      "points carry a YYYY-MM-DD date string",
      empty.points.every(
        (point) =>
          typeof point.date === "string" &&
          point.date.length === 10 &&
          point.date[4] === "-" &&
          point.date[7] === "-",
      ),
    );

    check(
      "the days option is honoured",
      dailyTrend([], { now: Date.now(), days: 3 }).points.length === 3,
    );
    check(
      "an invalid days option falls back to the default",
      dailyTrend([], { now: Date.now(), days: "nope" }).points.length === 14,
    );
    check(
      "the days option is clamped to the upper bound",
      dailyTrend([], { now: Date.now(), days: 999 }).points.length ===
        MAX_DAILY_TREND_DAYS,
    );
    check(
      "the days option is clamped to the lower bound",
      dailyTrend([], { now: Date.now(), days: 0 }).points.length === 1,
    );
    check(
      "a fractional days option is floored",
      dailyTrend([], { now: Date.now(), days: 6.9 }).points.length === 6,
    );

    // --- single day ---------------------------------------------------------
    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026
    const single = dailyTrend(
      [entry(now - 2 * HOUR, 25), entry(now - HOUR, 35)],
      { now, days: 1 },
    );
    check("single day keeps one point", single.points.length === 1);
    check("single day sums its minutes", single.points[0].minutes === 60);
    check("single day is not empty", single.empty === false);
    check("single day direction is flat", single.direction === "flat");
    check("single day min equals max", single.min === 60 && single.max === 60);

    // --- window excludes older days ----------------------------------------
    const windowed = dailyTrend(
      [entry(now - 60 * DAY, 500), entry(now - HOUR, 20)],
      { now, days: 4 },
    );
    check("out-of-window entries are ignored", windowed.max === 20);
    check("in-window minutes are kept", windowed.points[3].minutes === 20);

    // --- rising / falling / flat -------------------------------------------
    function daysAgo(daysBack, minutes, label) {
      return entry(new Date(2026, 5, 17 - daysBack, 12, 0, 0).getTime(), minutes, label);
    }
    const rising = dailyTrend(
      [daysAgo(2, 30), daysAgo(1, 60), daysAgo(0, 120)],
      { now, days: 3 },
    );
    check("rising direction is up", rising.direction === "up");
    check("rising min is the oldest day", rising.min === 30);
    check("rising max is the newest day", rising.max === 120);
    check("rising is not empty", rising.empty === false);

    const falling = dailyTrend(
      [daysAgo(2, 120), daysAgo(1, 90), daysAgo(0, 30)],
      { now, days: 3 },
    );
    check("falling direction is down", falling.direction === "down");

    const flat = dailyTrend(
      [daysAgo(2, 45), daysAgo(1, 45), daysAgo(0, 45)],
      { now, days: 3 },
    );
    check("flat direction is flat", flat.direction === "flat");
    check("flat is not empty", flat.empty === false);

    // Direction compares the newest day with the previous day, not a fitted
    // slope: [120, 30, 60] is "up" (60 > 30) even though the slope is negative,
    // and [30, 60, 60] is "flat" (60 === 60).
    const latestRise = dailyTrend(
      [daysAgo(2, 120), daysAgo(1, 30), daysAgo(0, 60)],
      { now, days: 3 },
    );
    check("direction compares the latest day", latestRise.direction === "up");
    const latestFlat = dailyTrend(
      [daysAgo(2, 30), daysAgo(1, 60), daysAgo(0, 60)],
      { now, days: 3 },
    );
    check("an unchanged latest day is flat", latestFlat.direction === "flat");
    const latestFall = dailyTrend(
      [daysAgo(2, 30), daysAgo(1, 90), daysAgo(0, 60)],
      { now, days: 3 },
    );
    check("a smaller latest day is down", latestFall.direction === "down");

    // --- label filter -------------------------------------------------------
    const filtered = dailyTrend(
      [
        daysAgo(1, 40, "Thesis"),
        daysAgo(1, 10, "Admin"),
        daysAgo(0, 15, "Thesis"),
      ],
      { now, days: 2, label: "Thesis" },
    );
    check("label filter keeps only the matching label", filtered.max === 40);
    check(
      "label filter sums the newer matching day",
      filtered.points[1].minutes === 15,
    );

    const unlabelled = dailyTrend(
      [entry(now - HOUR, 5), entry(now - HOUR, 7, "Thesis")],
      { now, days: 1, label: "(unlabelled)" },
    );
    check("the unlabelled filter matches unlabelled entries", unlabelled.max === 5);

    // --- aliases ------------------------------------------------------------
    const aliased = dailyTrend(
      [daysAgo(0, 50, "Thesis"), daysAgo(0, 20, "Admin")],
      { now, days: 1, label: "PhD", tags: { Thesis: "PhD" } },
    );
    check("an aliased label filter finds its sessions", aliased.max === 50);

    // --- daylight-saving: 23h spring-forward day ---------------------------
    const dstNow = new Date(2026, 2, 15, 12, 0, 0).getTime(); // Sun 15 Mar 2026
    const dst = dailyTrend(
      [
        entry(new Date(2026, 2, 2, 0, 30).getTime(), 10),
        entry(new Date(2026, 2, 8, 0, 30).getTime(), 20),
        entry(new Date(2026, 2, 8, 23, 30).getTime(), 30),
        entry(new Date(2026, 2, 15, 0, 30).getTime(), 40),
      ],
      { now: dstNow, days: 14 },
    );
    check("the spring-forward window keeps fourteen buckets", dst.points.length === 14);
    check(
      "the spring-forward window starts on the local calendar day",
      dst.points[0].date === "2026-03-02",
    );
    check(
      "the spring-forward window ends today",
      dst.points[13].date === "2026-03-15",
    );
    check("the 23h transition day is not shifted", dst.points[6].date === "2026-03-08");
    check("the 23h transition day merges both entries", dst.points[6].minutes === 50);
    check(
      "no day bucket is duplicated",
      new Set(dst.points.map((point) => point.date)).size === 14,
    );

    // --- daylight-saving: 25h fall-back day --------------------------------
    const fbNow = new Date(2026, 10, 8, 12, 0, 0).getTime(); // Sun 8 Nov 2026
    const fb = dailyTrend(
      [
        entry(new Date(2026, 9, 26, 0, 30).getTime(), 5),
        entry(new Date(2026, 10, 1, 0, 30).getTime(), 15),
        entry(new Date(2026, 10, 1, 23, 30).getTime(), 25),
        entry(new Date(2026, 10, 8, 12, 0, 0).getTime(), 35),
      ],
      { now: fbNow, days: 14 },
    );
    check("the fall-back window keeps fourteen buckets", fb.points.length === 14);
    check(
      "the fall-back window starts on the local calendar day",
      fb.points[0].date === "2026-10-26",
    );
    check("the fall-back window ends today", fb.points[13].date === "2026-11-08");
    check("the 25h transition day is not shifted", fb.points[6].date === "2026-11-01");
    check("the 25h transition day merges both entries", fb.points[6].minutes === 40);

    // --- daylight-saving: transition day is "today" and the just-completed
    // session sits in the final hour. A fixed DAY_MS upper bound lands at
    // ~23:00 local on the 25h day and would silently drop that entry.
    const fbToday = new Date(2026, 10, 1, 23, 30).getTime(); // Sun 1 Nov 2026
    const fbTodayResult = dailyTrend(
      [
        entry(new Date(2026, 10, 1, 0, 30).getTime(), 10),
        entry(new Date(2026, 10, 1, 23, 45).getTime(), 20),
      ],
      { now: fbToday, days: 1 },
    );
    check(
      "the fall-back day keeps its final-hour entry",
      fbTodayResult.points.length === 1 &&
        fbTodayResult.points[0].minutes === 30,
    );
    check("the fall-back day is not empty", fbTodayResult.empty === false);

    // --- robustness ---------------------------------------------------------
    const malformed = [null, undefined, {}, [], 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = dailyTrend(value, { now, days: 3 });
      } catch (error) {
        threw = true;
      }
      check("dailyTrend(" + String(value) + ") does not throw", !threw);
      check(
        "dailyTrend(" + String(value) + ") is empty",
        !threw && result.empty === true,
      );
    }
    check(
      "malformed entries are ignored",
      dailyTrend(
        [42, "x", { phase: "break", durationSeconds: 60 }],
        { now, days: 1 },
      ).empty === true,
    );
    check(
      "dailyTrend survives a malformed now",
      dailyTrend([], { now: "not-a-date", days: 1 }).points.length === 1,
    );

    const frozen = [entry(now - HOUR, 30, "Thesis")];
    const snapshot = JSON.stringify(frozen);
    const tags = { Thesis: "PhD" };
    const tagsSnapshot = JSON.stringify(tags);
    dailyTrend(frozen, { now, days: 1, tags });
    check("dailyTrend never mutates its log", JSON.stringify(frozen) === snapshot);
    check("dailyTrend never mutates tags", JSON.stringify(tags) === tagsSnapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class DailyTrendStaticTests(unittest.TestCase):
    def test_history_exports_daily_trend(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+dailyTrend\b",
            "history.js does not export dailyTrend",
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
        self.assertIn('id="stats-daily-trend"', html)
        self.assertIn('id="stats-daily-trend-chart"', html)
        self.assertIn('role="img"', html)
        self.assertIn(
            'data-i18n-attr="aria-label:stats.dailyTrendChartLabel"', html
        )
        self.assertIn('data-i18n="stats.dailyTrendEmpty"', html)

    def test_main_js_renders_the_trend(self):
        js = read(MAIN_PATH)
        self.assertIn("dailyTrend", js)
        self.assertIn("renderDailyTrend", js)
        self.assertIn("renderDailyTrendChart", js)
        self.assertIn("stats-daily-trend-chart", js)
        self.assertIn("announce.dailyTrend", js)
        self.assertIn("lastAnnouncedDailyTrendDirection", js)

    def test_styles_define_the_sparkline(self):
        css = read(STYLES_PATH)
        self.assertIn(".stats__daily-trend-chart", css)
        self.assertIn(".stats__daily-trend-line", css)
        self.assertIn(".stats__daily-trend-dot", css)


class DailyTrendI18nTests(unittest.TestCase):
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
class DailyTrendLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-daily-trend-")
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
            "dailyTrend logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
