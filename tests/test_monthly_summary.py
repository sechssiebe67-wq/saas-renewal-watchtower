"""Tests for the Focus Flow ``monthlySummary`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``monthlySummary``, that
   ``app/index.html`` carries the monthly focus comparison markup, that
   ``app/main.js`` renders the block and reads the new catalog keys, and that
   ``app/styles.css`` styles it.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``monthlySummary`` helper is
   exercised against real history logs so the empty / single-entry / out-of-
   window shapes, the label filter, the alias map, the up / steady / down trend
   classification, and the daylight-saving day count are verified for real. The
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
    "stats.monthHeading",
    "stats.monthLabel",
    "stats.monthWindow",
    "stats.monthAllTime",
    "stats.monthUp",
    "stats.monthDown",
    "stats.monthSteady",
    "stats.monthEmpty",
    "announce.month",
)

HARNESS = textwrap.dedent(
    """
    import { monthlySummary } from "./history.mjs";

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

    // --- empty history ------------------------------------------------------
    const empty = monthlySummary([], { now });
    check("empty window has no sessions", empty.window.sessions === 0);
    check("empty window has no minutes", empty.window.minutes === 0);
    check("empty window days run from the 1st to today", empty.window.days === 17);
    check("empty all-time has no sessions", empty.allTime.sessions === 0);
    check("empty all-time has no minutes", empty.allTime.minutes === 0);
    check("empty all-time months are floored at one", empty.allTime.months === 1);
    check("empty all-time per-month is zero", empty.allTime.perMonthMinutes === 0);
    check("empty trend is steady", empty.trend === "steady");

    // --- single entry inside the month -------------------------------------
    const one = monthlySummary([entry(new Date(2026, 5, 1, 9, 0).getTime(), 30)], {
      now,
    });
    check("a month entry counts one session", one.window.sessions === 1);
    check("a month entry sums minutes", one.window.minutes === 30);
    check("a constant monthly pace is steady", one.trend === "steady");
    check("a single active month is one", one.allTime.months === 1);
    check("per-month average is the total for one month", one.allTime.perMonthMinutes === 30);

    // --- entries outside the current month ---------------------------------
    const old = monthlySummary([entry(new Date(2026, 4, 20, 9, 0).getTime(), 600)], {
      now,
    });
    check("last month is excluded from the window", old.window.sessions === 0);
    check("last month is counted all-time", old.allTime.sessions === 1);
    check("last month minutes are counted all-time", old.allTime.minutes === 600);
    check("last month still gives one active month", old.allTime.months === 1);

    // The current month window is day 1 through today, inclusive.
    const two = monthlySummary(
      [
        entry(new Date(2026, 5, 1, 9, 0).getTime(), 25),
        entry(new Date(2026, 5, 17, 9, 0).getTime(), 15),
      ],
      { now },
    );
    check("the month window sums both entries", two.window.sessions === 2);
    check("the month window sums both minutes", two.window.minutes === 40);

    // --- label filter -------------------------------------------------------
    const filtered = monthlySummary(
      [
        entry(new Date(2026, 5, 10, 9, 0).getTime(), 40, "Thesis"),
        entry(new Date(2026, 5, 10, 9, 0).getTime(), 10, "Admin"),
        entry(new Date(2026, 5, 10, 9, 0).getTime(), 15),
      ],
      { now, label: "Thesis" },
    );
    check("label filter keeps only the matching label", filtered.window.sessions === 1);
    check("label filter sums only the matching minutes", filtered.window.minutes === 40);
    check("label filter narrows all-time too", filtered.allTime.sessions === 1);

    const unlabelled = monthlySummary(
      [entry(new Date(2026, 5, 10, 9, 0).getTime(), 5)],
      { now, label: "(unlabelled)" },
    );
    check("the unlabelled filter matches unlabelled entries", unlabelled.window.minutes === 5);

    // --- aliases ------------------------------------------------------------
    const aliased = monthlySummary([entry(new Date(2026, 5, 10, 9, 0).getTime(), 50, "Thesis")], {
      now,
      label: "PhD",
      tags: { Thesis: "PhD" },
    });
    check("an aliased label filter finds its sessions", aliased.window.minutes === 50);

    // --- trend classification ----------------------------------------------
    // A busy current month against a low, long all-time baseline trends up.
    const upEntries = [];
    for (let index = 0; index < 100; index += 1) {
      upEntries.push(entry(now - (200 - index) * DAY, 1));
    }
    for (let day = 1; day <= 17; day += 1) {
      upEntries.push(entry(new Date(2026, 5, day, 9, 0).getTime(), 60));
    }
    const up = monthlySummary(upEntries, { now });
    check("recent month above the baseline trends up", up.trend === "up");

    // A quiet current month against a high, long all-time baseline trends down.
    const downEntries = [];
    for (let index = 0; index < 50; index += 1) {
      downEntries.push(entry(now - (100 - index) * DAY, 60));
    }
    for (let day = 1; day <= 17; day += 1) {
      downEntries.push(entry(new Date(2026, 5, day, 9, 0).getTime(), 1));
    }
    const down = monthlySummary(downEntries, { now });
    check("a quiet month below the baseline trends down", down.trend === "down");

    // A constant daily pace over the whole retained log is steady.
    const steadyEntries = [];
    for (let index = 0; index < 60; index += 1) {
      steadyEntries.push(entry(now - index * DAY, 30));
    }
    const steady = monthlySummary(steadyEntries, { now });
    check("a constant daily pace is steady", steady.trend === "steady");

    // A tiny fluctuation under the tolerance must not flip the label.
    const tolerantEntries = [];
    for (let day = 1; day <= 17; day += 1) {
      tolerantEntries.push(entry(new Date(2026, 5, day, 9, 0).getTime(), 30));
    }
    for (let index = 1; index <= 40; index += 1) {
      tolerantEntries.push(entry(now - (17 + index) * DAY, 30));
    }
    tolerantEntries.push(entry(new Date(2026, 5, 17, 10, 0).getTime(), 3));
    const tolerant = monthlySummary(tolerantEntries, { now });
    check("a small fluctuation stays steady", tolerant.trend === "steady");

    // --- active-month averaging --------------------------------------------
    const multi = monthlySummary(
      [
        entry(new Date(2026, 3, 10, 9, 0).getTime(), 300),
        entry(new Date(2026, 4, 10, 9, 0).getTime(), 300),
        entry(new Date(2026, 5, 10, 9, 0).getTime(), 300),
      ],
      { now },
    );
    check("three active months are counted", multi.allTime.months === 3);
    check("per-month average spans the active months", multi.allTime.perMonthMinutes === 300);

    // --- daylight-saving day counting --------------------------------------
    // The US fall-back is Sunday 1 November 2026. The November window from the
    // 1st through the 5th must be exactly five local days and keep the entry
    // logged at 00:30 on the 25-hour fall-back day.
    const dstNow = new Date(2026, 10, 5, 12, 0, 0).getTime();
    const dst = monthlySummary(
      [
        entry(new Date(2026, 10, 1, 0, 30).getTime(), 15),
        entry(new Date(2026, 10, 5, 8, 0).getTime(), 25),
      ],
      { now: dstNow },
    );
    check("the DST window keeps the fall-back day entry", dst.window.sessions === 2);
    check("the DST window counts five days", dst.window.days === 5);
    check("the DST window sums both entries", dst.window.minutes === 40);

    // --- robustness ---------------------------------------------------------
    const malformed = [null, undefined, {}, [], 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = monthlySummary(value, { now });
      } catch (error) {
        threw = true;
      }
      check("monthlySummary(" + String(value) + ") does not throw", !threw);
      check(
        "monthlySummary(" + String(value) + ") is empty and steady",
        !threw &&
          result.window.sessions === 0 &&
          result.allTime.sessions === 0 &&
          result.trend === "steady",
      );
    }
    check(
      "malformed entries are ignored",
      monthlySummary(
        [42, "x", { phase: "break", durationSeconds: 60 }],
        { now },
      ).allTime.sessions === 0,
    );
    check(
      "monthlySummary survives a malformed now",
      monthlySummary([], { now: "not-a-date" }).window.days >= 1,
    );

    const frozen = [entry(new Date(2026, 5, 10, 9, 0).getTime(), 30, "Thesis")];
    const snapshot = JSON.stringify(frozen);
    const tags = { Thesis: "PhD" };
    const tagsSnapshot = JSON.stringify(tags);
    monthlySummary(frozen, { now, label: "PhD", tags });
    check("monthlySummary never mutates its log", JSON.stringify(frozen) === snapshot);
    check("monthlySummary never mutates tags", JSON.stringify(tags) === tagsSnapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class MonthlySummaryStaticTests(unittest.TestCase):
    def test_history_exports_monthly_summary(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+monthlySummary\b",
            "history.js does not export monthlySummary",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_month_block(self):
        html = read(INDEX_PATH)
        for fragment in (
            'id="stats-month"',
            'id="stats-month-window"',
            'id="stats-month-alltime"',
            'id="stats-month-compare"',
            'id="stats-month-empty"',
            'role="group"',
        ):
            self.assertIn(fragment, html, "missing %s" % fragment)
        self.assertIn('data-i18n="stats.monthHeading"', html)
        self.assertIn('data-i18n="stats.monthEmpty"', html)
        self.assertIn('data-i18n-attr="aria-label:stats.monthLabel"', html)

    def test_main_js_renders_the_month_block(self):
        js = read(MAIN_PATH)
        for symbol in (
            "monthlySummary",
            "renderMonthSummary",
            "stats-month-window",
            "stats.monthWindow",
            "stats.monthAllTime",
            "announce.month",
            "lastAnnouncedMonthTrend",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_styles_define_the_month_block(self):
        css = read(STYLES_PATH)
        for fragment in (
            ".stats__month-panel",
            ".stats__month-line",
            ".stats__month-compare",
            ".stats__month-empty",
        ):
            self.assertIn(fragment, css, "missing CSS %s" % fragment)


class MonthlySummaryI18nTests(unittest.TestCase):
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
class MonthlySummaryLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-month-")
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
            "monthlySummary logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
