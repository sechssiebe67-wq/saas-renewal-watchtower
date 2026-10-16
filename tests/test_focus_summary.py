"""Tests for the Focus Flow ``focusSummary`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``focusSummary`` and its
   constants, that ``app/index.html`` carries the 30-day summary markup, that
   ``app/main.js`` renders the block and reads the new catalog keys, and that
   ``app/styles.css`` styles it.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``focusSummary`` helper is
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
    "stats.summaryHeading",
    "stats.summaryLabel",
    "stats.summaryWindow",
    "stats.summaryAllTime",
    "stats.summaryUp",
    "stats.summaryDown",
    "stats.summarySteady",
    "stats.summaryEmpty",
    "announce.summary",
)

HARNESS = textwrap.dedent(
    """
    import { focusSummary, SUMMARY_DAYS } from "./history.mjs";

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
    const empty = focusSummary([], { now: Date.now() });
    check("SUMMARY_DAYS is 30", SUMMARY_DAYS === 30);
    check("empty window has no sessions", empty.window.sessions === 0);
    check("empty window has no minutes", empty.window.minutes === 0);
    check("empty window uses the requested days", empty.window.days === 30);
    check("empty window per-day is zero", empty.window.perDayMinutes === 0);
    check("empty all-time has no sessions", empty.allTime.sessions === 0);
    check("empty all-time has no minutes", empty.allTime.minutes === 0);
    check("empty all-time days are floored at one", empty.allTime.days === 1);
    check("empty all-time per-day is zero", empty.allTime.perDayMinutes === 0);
    check("empty trend is steady", empty.trend === "steady");

    const single = focusSummary([entry(Date.now() - HOUR, 30)], {
      now: Date.now(),
    });
    check("single entry counts one session", single.window.sessions === 1);
    check("single entry sums minutes", single.window.minutes === 30);
    check("single entry all-time days is one", single.allTime.days === 1);
    check("single entry all-time per-day is the total", single.allTime.perDayMinutes === 30);

    // --- days option --------------------------------------------------------
    check(
      "the days option is honoured",
      focusSummary([], { now: Date.now(), days: 7 }).window.days === 7,
    );
    check(
      "an invalid days option falls back to the default",
      focusSummary([], { now: Date.now(), days: "nope" }).window.days === 30,
    );
    check(
      "the days option is floored at one",
      focusSummary([], { now: Date.now(), days: 0 }).window.days === 1,
    );
    check(
      "a fractional days option is floored",
      focusSummary([], { now: Date.now(), days: 5.9 }).window.days === 5,
    );

    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026

    // --- single entry (fixed now) ------------------------------------------
    const one = focusSummary([entry(now - 2 * HOUR, 25), entry(now - HOUR, 35)], {
      now,
    });
    check("single window sums sessions", one.window.sessions === 2);
    check("single window sums minutes", one.window.minutes === 60);
    check("single window per-day uses the requested days", one.window.perDayMinutes === 2);
    check("single all-time has one day", one.allTime.days === 1);
    check("single all-time per-day equals the total", one.allTime.perDayMinutes === 60);

    // --- entries outside the 30-day window ---------------------------------
    const old = focusSummary([entry(now - 60 * DAY, 600)], { now });
    check("out-of-window entry is excluded from the window", old.window.sessions === 0);
    check("out-of-window entry is counted all-time", old.allTime.sessions === 1);
    check("out-of-window minutes are counted all-time", old.allTime.minutes === 600);
    check("all-time day count reaches back to the oldest entry", old.allTime.days === 61);

    // --- label filter -------------------------------------------------------
    const filtered = focusSummary(
      [
        entry(now - HOUR, 40, "Thesis"),
        entry(now - HOUR, 10, "Admin"),
        entry(now - HOUR, 15),
      ],
      { now, label: "Thesis" },
    );
    check("label filter keeps only the matching label", filtered.window.sessions === 1);
    check("label filter sums only the matching minutes", filtered.window.minutes === 40);
    check("label filter narrows all-time too", filtered.allTime.sessions === 1);

    const unlabelled = focusSummary(
      [entry(now - HOUR, 5), entry(now - HOUR, 7, "Thesis")],
      { now, label: "(unlabelled)" },
    );
    check("the unlabelled filter matches unlabelled entries", unlabelled.window.minutes === 5);

    // --- aliases ------------------------------------------------------------
    const aliased = focusSummary([entry(now - HOUR, 50, "Thesis")], {
      now,
      label: "PhD",
      tags: { Thesis: "PhD" },
    });
    check("an aliased label filter finds its sessions", aliased.window.minutes === 50);

    // --- trend classification ----------------------------------------------
    // A high recent window against a low all-time baseline trends up.
    const up = focusSummary([entry(now - 80 * DAY, 1), entry(now - HOUR, 900)], { now });
    check("recent pace above the baseline trends up", up.trend === "up");
    check("up window per-day is the recent average", up.window.perDayMinutes === 30);

    // The mirror image trends down.
    const down = focusSummary([entry(now - 80 * DAY, 900), entry(now - HOUR, 1)], { now });
    check("recent pace below the baseline trends down", down.trend === "down");

    // A constant daily pace over the whole retained log is steady.
    const steadyEntries = [];
    for (let index = 0; index < 60; index += 1) {
      steadyEntries.push(entry(now - index * DAY, 30));
    }
    const steady = focusSummary(steadyEntries, { now });
    check("a constant daily pace is steady", steady.trend === "steady");

    // A tiny fluctuation under the tolerance must not flip the label.
    const tolerant = focusSummary(
      [entry(now - 60 * DAY, 100), entry(now - HOUR, 103)],
      { now },
    );
    check("a small fluctuation stays steady", tolerant.trend === "steady");

    // --- daylight-saving day counting --------------------------------------
    // The US fall-back is Sunday 1 November 2026. A trailing five-day window
    // ending Thursday 5 November must include 1 November (a 25-hour local day)
    // and the all-time count from 1 to 5 November must be exactly five days.
    const dstNow = new Date(2026, 10, 5, 12, 0, 0).getTime();
    const dst = focusSummary(
      [
        entry(new Date(2026, 10, 1, 0, 30).getTime(), 15),
        entry(new Date(2026, 10, 5, 8, 0).getTime(), 25),
      ],
      { now: dstNow, days: 5 },
    );
    check("the DST window keeps the fall-back day entry", dst.window.sessions === 2);
    check("the DST window sums both entries", dst.window.minutes === 40);
    check("the DST all-time day count is five", dst.allTime.days === 5);

    // --- robustness ---------------------------------------------------------
    const malformed = [null, undefined, {}, [], 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = focusSummary(value, { now });
      } catch (error) {
        threw = true;
      }
      check("focusSummary(" + String(value) + ") does not throw", !threw);
      check(
        "focusSummary(" + String(value) + ") is empty and steady",
        !threw &&
          result.window.sessions === 0 &&
          result.allTime.sessions === 0 &&
          result.trend === "steady",
      );
    }
    check(
      "malformed entries are ignored",
      focusSummary(
        [42, "x", { phase: "break", durationSeconds: 60 }],
        { now },
      ).allTime.sessions === 0,
    );
    check(
      "focusSummary survives a malformed now",
      focusSummary([], { now: "not-a-date" }).window.days === 30,
    );

    const frozen = [entry(now - HOUR, 30, "Thesis")];
    const snapshot = JSON.stringify(frozen);
    const tags = { Thesis: "PhD" };
    const tagsSnapshot = JSON.stringify(tags);
    focusSummary(frozen, { now, label: "PhD", tags });
    check("focusSummary never mutates its log", JSON.stringify(frozen) === snapshot);
    check("focusSummary never mutates tags", JSON.stringify(tags) === tagsSnapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class FocusSummaryStaticTests(unittest.TestCase):
    def test_history_exports_focus_summary(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+focusSummary\b",
            "history.js does not export focusSummary",
        )
        self.assertRegex(
            source,
            r"export\s+const\s+SUMMARY_DAYS\b",
            "history.js does not export SUMMARY_DAYS",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_summary_block(self):
        html = read(INDEX_PATH)
        for fragment in (
            'id="stats-summary"',
            'id="stats-summary-window"',
            'id="stats-summary-alltime"',
            'id="stats-summary-compare"',
            'id="stats-summary-empty"',
            'role="group"',
        ):
            self.assertIn(fragment, html, "missing %s" % fragment)
        self.assertIn('data-i18n="stats.summaryHeading"', html)
        self.assertIn('data-i18n="stats.summaryEmpty"', html)
        self.assertIn('data-i18n-attr="aria-label:stats.summaryLabel"', html)

    def test_main_js_renders_the_summary(self):
        js = read(MAIN_PATH)
        for symbol in (
            "focusSummary",
            "SUMMARY_DAYS",
            "renderSummary",
            "stats-summary-window",
            "stats.summaryWindow",
            "stats.summaryAllTime",
            "announce.summary",
            "lastAnnouncedSummaryTrend",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_styles_define_the_summary_block(self):
        css = read(STYLES_PATH)
        for fragment in (
            ".stats__summary-panel",
            ".stats__summary-line",
            ".stats__summary-compare",
            ".stats__summary-empty",
        ):
            self.assertIn(fragment, css, "missing CSS %s" % fragment)


class FocusSummaryI18nTests(unittest.TestCase):
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
class FocusSummaryLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-summary-")
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
            "focusSummary logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
