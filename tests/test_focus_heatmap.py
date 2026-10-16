"""Tests for the Focus Flow ``focusHeatmap`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``focusHeatmap`` (and the
   ``HEATMAP_WEEKS`` constant), that ``app/index.html`` carries the heatmap
   markup, and that ``app/main.js`` renders the grid and reads the new catalog
   keys.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``focusHeatmap`` helper is
   exercised against real history logs so the empty / single-day / label-filter
   / alias / ``maxMinutes === 0`` shapes and the daylight-saving boundary are
   verified for real. The harness runs with a ``TZ`` that observes daylight
   saving so the local-calendar arithmetic is genuinely tested.
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
    "stats.heatmapHeading",
    "stats.heatmapLabel",
    "stats.heatmapRange",
    "stats.heatmapDay",
    "stats.heatmapLess",
    "stats.heatmapMore",
    "stats.heatmapEmpty",
    "announce.heatmap",
)

HARNESS = textwrap.dedent(
    """
    import { focusHeatmap, HEATMAP_WEEKS } from "./history.mjs";

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

    function dayKey(year, month, day) {
      return (
        String(year).padStart(4, "0") +
        "-" +
        String(month).padStart(2, "0") +
        "-" +
        String(day).padStart(2, "0")
      );
    }

    function findDay(result, key) {
      return result.days.find((day) => day.date === key);
    }

    // --- empty history ------------------------------------------------------
    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026
    const empty = focusHeatmap([], { now });
    check("HEATMAP_WEEKS is twelve", HEATMAP_WEEKS === 12);
    check("default weeks is twelve", empty.weeks === 12);
    check("empty covers weeks * 7 days", empty.days.length === 84);
    check("empty maxMinutes is zero", empty.maxMinutes === 0);
    check("empty flag is true", empty.empty === true);
    check("empty days are all zero", empty.days.every((day) => day.minutes === 0));
    check(
      "empty days are all level zero",
      empty.days.every((day) => day.level === 0),
    );
    check(
      "days are chronological",
      empty.days.every(
        (day, index) =>
          index === 0 || day.date > empty.days[index - 1].date,
      ),
    );
    check(
      "days are unique",
      new Set(empty.days.map((day) => day.date)).size === empty.days.length,
    );
    check(
      "days carry a YYYY-MM-DD date string",
      empty.days.every(
        (day) => typeof day.date === "string" && /^\\d{4}-\\d{2}-\\d{2}$/.test(day.date),
      ),
    );
    check("the last day is today", empty.days[83].date === "2026-06-17");
    check("the first day is today minus weeks*7-1", empty.days[0].date === "2026-03-26");
    check(
      "each day has minutes and sessions buckets",
      empty.days.every(
        (day) =>
          day.minutes === 0 &&
          day.sessions === 0 &&
          typeof day.date === "string" &&
          typeof day.level === "number",
      ),
    );

    // --- options ------------------------------------------------------------
    check(
      "weeks option is honoured",
      focusHeatmap([], { now, weeks: 3 }).days.length === 21,
    );
    check(
      "weeks option sets the returned count",
      focusHeatmap([], { now, weeks: 3 }).weeks === 3,
    );
    check(
      "an invalid weeks option falls back to the default",
      focusHeatmap([], { now, weeks: "nope" }).weeks === 12,
    );
    check(
      "the weeks option is clamped to the upper bound",
      focusHeatmap([], { now, weeks: 100 }).weeks === 26,
    );
    check(
      "weeks <= 0 is clamped to one",
      focusHeatmap([], { now, weeks: 0 }).weeks === 1 &&
        focusHeatmap([], { now, weeks: 0 }).days.length === 7,
    );
    check(
      "a negative weeks option is clamped to one",
      focusHeatmap([], { now, weeks: -5 }).weeks === 1,
    );
    check(
      "a fractional weeks option is floored",
      focusHeatmap([], { now, weeks: 6.9 }).weeks === 6,
    );
    check(
      "weekStartsOn is accepted but does not change the day buckets",
      JSON.stringify(
        focusHeatmap([], { now, weeks: 2, weekStartsOn: 0 }).days,
      ) ===
        JSON.stringify(
          focusHeatmap([], { now, weeks: 2, weekStartsOn: 1 }).days,
        ),
    );

    // --- single day ---------------------------------------------------------
    const single = focusHeatmap(
      [
        entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 25),
        entry(new Date(2026, 5, 17, 14, 0, 0).getTime(), 35),
      ],
      { now, weeks: 1 },
    );
    check("single day keeps seven buckets", single.days.length === 7);
    check("single day is not empty", single.empty === false);
    check("single day sums its minutes", single.maxMinutes === 60);
    check(
      "single day counts its sessions",
      findDay(single, "2026-06-17").sessions === 2,
    );
    check(
      "the best day gets the top level",
      findDay(single, "2026-06-17").level === 4,
    );
    check(
      "an empty day stays level zero",
      findDay(single, "2026-06-16").level === 0,
    );

    // --- level scaling ------------------------------------------------------
    const scaled = focusHeatmap(
      [
        entry(new Date(2026, 5, 15, 9, 0, 0).getTime(), 10),
        entry(new Date(2026, 5, 16, 9, 0, 0).getTime(), 20),
        entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 40),
      ],
      { now, weeks: 1 },
    );
    check("scaled max is the best day", scaled.maxMinutes === 40);
    check("scaled level 1", findDay(scaled, "2026-06-15").level === 1);
    check("scaled level 2", findDay(scaled, "2026-06-16").level === 2);
    check("scaled level 4", findDay(scaled, "2026-06-17").level === 4);
    check(
      "levels stay within 0..4",
      scaled.days.every((day) => day.level >= 0 && day.level <= 4),
    );

    // --- window excludes older days ----------------------------------------
    const windowed = focusHeatmap(
      [
        entry(now - 60 * DAY, 500),
        entry(now - HOUR, 20),
      ],
      { now, weeks: 4 },
    );
    check("out-of-window entries are ignored", windowed.maxMinutes === 20);
    check("in-window minutes are kept", findDay(windowed, "2026-06-17").minutes === 20);

    // --- label filter -------------------------------------------------------
    const filtered = focusHeatmap(
      [
        entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 40, "Thesis"),
        entry(new Date(2026, 5, 17, 10, 0, 0).getTime(), 10, "Admin"),
        entry(new Date(2026, 5, 16, 9, 0, 0).getTime(), 15, "Thesis"),
      ],
      { now, weeks: 1, label: "Thesis" },
    );
    check("label filter keeps only the matching label", filtered.maxMinutes === 40);
    check(
      "label filter sums only matching minutes",
      findDay(filtered, "2026-06-17").minutes === 40,
    );
    check(
      "label filter counts only matching sessions",
      findDay(filtered, "2026-06-17").sessions === 1,
    );

    const unlabelled = focusHeatmap(
      [entry(now - DAY, 5), entry(now - DAY, 7, "Thesis")],
      { now, weeks: 1, label: "(unlabelled)" },
    );
    check("the unlabelled filter matches unlabelled entries", unlabelled.maxMinutes === 5);

    // --- aliases ------------------------------------------------------------
    const aliased = focusHeatmap(
      [
        entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 50, "Thesis"),
        entry(new Date(2026, 5, 17, 10, 0, 0).getTime(), 20, "Admin"),
      ],
      {
        now,
        weeks: 1,
        label: "PhD",
        tags: { Thesis: "PhD" },
      },
    );
    check("an aliased label filter finds its sessions", aliased.maxMinutes === 50);
    check(
      "an alias merges matching sessions",
      findDay(aliased, "2026-06-17").sessions === 1,
    );

    // --- maxMinutes === 0 ---------------------------------------------------
    const zero = focusHeatmap(
      [
        entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 0),
        entry(new Date(2026, 5, 16, 9, 0, 0).getTime(), 0),
      ],
      { now, weeks: 1 },
    );
    check("zero-minute days keep maxMinutes at zero", zero.maxMinutes === 0);
    check("zero-minute days are empty", zero.empty === true);
    check(
      "zero-minute days are all level zero",
      zero.days.every((day) => day.level === 0),
    );

    // --- daylight-saving boundaries ----------------------------------------
    // 2026 spring-forward is Sunday 8 March and fall-back is Sunday 1 November.
    // Because 26 weeks cannot span both, each transition gets its own window;
    // the local-calendar arithmetic must keep every bucket and never shift,
    // drop, or duplicate a day. Each boundary day has an early and a late entry
    // so both sides of the transition are represented.
    const springNow = new Date(2026, 3, 1, 12, 0, 0).getTime(); // Wed 1 Apr 2026
    const spring = focusHeatmap(
      [
        entry(new Date(2026, 2, 8, 1, 30).getTime(), 15),
        entry(new Date(2026, 2, 8, 23, 30).getTime(), 25),
        entry(new Date(2026, 2, 9, 0, 30).getTime(), 99), // next day, its own bucket
      ],
      { now: springNow, weeks: 4 },
    );
    check("spring-forward window covers weeks * 7 days", spring.days.length === 28);
    check(
      "spring-forward window days are unique",
      new Set(spring.days.map((day) => day.date)).size === spring.days.length,
    );
    check(
      "spring-forward window days are chronological",
      spring.days.every(
        (day, index) => index === 0 || day.date > spring.days[index - 1].date,
      ),
    );
    check(
      "spring-forward keeps both boundary entries on one day",
      findDay(spring, "2026-03-08").sessions === 2 &&
        findDay(spring, "2026-03-08").minutes === 40,
    );
    check(
      "spring-forward day is present exactly once",
      spring.days.filter((day) => day.date === "2026-03-08").length === 1,
    );
    check(
      "the day after spring-forward is a separate bucket",
      findDay(spring, "2026-03-09").minutes === 99,
    );
    check(
      "spring-forward window starts exactly weeks * 7 - 1 days before today",
      spring.days[0].date === "2026-03-05",
    );

    const fallNow = new Date(2026, 10, 20, 12, 0, 0).getTime(); // Fri 20 Nov 2026
    const fall = focusHeatmap(
      [
        entry(new Date(2026, 10, 1, 0, 30).getTime(), 35),
        entry(new Date(2026, 10, 1, 23, 30).getTime(), 45),
      ],
      { now: fallNow, weeks: 4 },
    );
    check("fall-back window covers weeks * 7 days", fall.days.length === 28);
    check(
      "fall-back window days are unique",
      new Set(fall.days.map((day) => day.date)).size === fall.days.length,
    );
    check(
      "fall-back keeps both boundary entries on one day",
      findDay(fall, "2026-11-01").sessions === 2 &&
        findDay(fall, "2026-11-01").minutes === 80,
    );
    check(
      "fall-back day is present exactly once",
      fall.days.filter((day) => day.date === "2026-11-01").length === 1,
    );
    check(
      "fall-back window ends today",
      fall.days[27].date === "2026-11-20",
    );

    // --- robustness ---------------------------------------------------------
    const malformed = [null, undefined, {}, [], 42, "nope"];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = focusHeatmap(value, { now, weeks: 2 });
      } catch (error) {
        threw = true;
      }
      check("focusHeatmap(" + String(value) + ") does not throw", !threw);
      check(
        "focusHeatmap(" + String(value) + ") is the documented shape",
        !threw &&
          result.empty === true &&
          Array.isArray(result.days) &&
          result.days.length === 14 &&
          result.maxMinutes === 0,
      );
    }
    check(
      "malformed entries are ignored",
      focusHeatmap(
        [42, "x", { phase: "break", durationSeconds: 60 }],
        { now, weeks: 1 },
      ).empty === true,
    );
    check(
      "focusHeatmap survives a malformed now",
      focusHeatmap([], { now: "not-a-date", weeks: 1 }).days.length === 7,
    );

    const frozen = [entry(new Date(2026, 5, 17, 9, 0, 0).getTime(), 30, "Thesis")];
    const snapshot = JSON.stringify(frozen);
    const tags = { Thesis: "PhD" };
    const tagsSnapshot = JSON.stringify(tags);
    focusHeatmap(frozen, { now, weeks: 1, tags });
    check("focusHeatmap never mutates its log", JSON.stringify(frozen) === snapshot);
    check("focusHeatmap never mutates tags", JSON.stringify(tags) === tagsSnapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class FocusHeatmapStaticTests(unittest.TestCase):
    def test_history_exports_focus_heatmap(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+focusHeatmap\b",
            "history.js does not export focusHeatmap",
        )
        self.assertRegex(
            source,
            r"export\s+const\s+HEATMAP_WEEKS\b",
            "history.js does not export HEATMAP_WEEKS",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_heatmap(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-heatmap"', html)
        self.assertIn('id="stats-heatmap-grid"', html)
        self.assertIn('id="stats-heatmap-empty"', html)
        self.assertIn('id="stats-heatmap-range"', html)
        self.assertIn('role="img"', html)
        self.assertIn('data-i18n-attr="aria-label:stats.heatmapLabel"', html)
        self.assertIn('data-i18n="stats.heatmapEmpty"', html)
        self.assertIn('data-i18n="stats.heatmapHeading"', html)
        self.assertIn('data-i18n="stats.heatmapLess"', html)
        self.assertIn('data-i18n="stats.heatmapMore"', html)

    def test_main_js_renders_the_heatmap(self):
        js = read(MAIN_PATH)
        self.assertIn("focusHeatmap", js)
        self.assertIn("HEATMAP_WEEKS", js)
        self.assertIn("renderHeatmap", js)
        self.assertIn("renderHeatmapGrid", js)
        self.assertIn("stats-heatmap-grid", js)
        self.assertIn("announce.heatmap", js)
        self.assertIn("lastAnnouncedHeatmapRange", js)

    def test_styles_define_the_heatmap(self):
        css = read(STYLES_PATH)
        self.assertIn(".stats__heatmap-grid", css)
        self.assertIn(".stats__heatmap-cell", css)
        self.assertIn(".stats__heatmap-legend", css)
        self.assertIn(".stats__heatmap-empty", css)


class FocusHeatmapI18nTests(unittest.TestCase):
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
class FocusHeatmapLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-heatmap-")
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
            "focusHeatmap logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
