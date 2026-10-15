"""Tests for the Focus Flow user-selectable first day of the week.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``WEEK_START_OPTIONS``,
   ``WEEK_START_STORAGE_SHAPE_VERSION`` and ``normalizeWeekStart``, that
   ``app/index.html`` wires up the ``week-start`` select with localised label
   and options, and that ``app/main.js`` reads and writes the key.
2. A static check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``history.js`` helpers are
   exercised so ``normalizeWeekStart`` and the ``weekStartsOn`` behaviour of
   ``weekWindow``/``goalProgress``/``weeklyReview`` are verified for real,
   including the Sunday/Monday boundary.
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
    "settings.weekStart",
    "settings.weekStartMonday",
    "settings.weekStartSunday",
    "announce.weekStart",
)

HARNESS = textwrap.dedent(
    """
    import {
      DEFAULT_WEEK_START,
      WEEK_START_OPTIONS,
      WEEK_START_STORAGE_SHAPE_VERSION,
      normalizeWeekStart,
      weekWindow,
      goalProgress,
      weeklyReview,
    } from "./history.mjs";

    const DAY = 24 * 60 * 60 * 1000;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    check("DEFAULT_WEEK_START is Monday", DEFAULT_WEEK_START === 1);

    check(
      "WEEK_START_STORAGE_SHAPE_VERSION is a positive integer",
      Number.isInteger(WEEK_START_STORAGE_SHAPE_VERSION) &&
        WEEK_START_STORAGE_SHAPE_VERSION > 0,
    );

    check("WEEK_START_OPTIONS is an array", Array.isArray(WEEK_START_OPTIONS));
    check("WEEK_START_OPTIONS is frozen", Object.isFrozen(WEEK_START_OPTIONS));
    check("WEEK_START_OPTIONS has two entries", WEEK_START_OPTIONS.length === 2);
    check(
      "WEEK_START_OPTIONS leads with the default",
      WEEK_START_OPTIONS[0].value === DEFAULT_WEEK_START,
    );
    const optionValues = WEEK_START_OPTIONS.map((option) => option.value);
    check(
      "WEEK_START_OPTIONS offers Monday and Sunday",
      optionValues.includes(1) && optionValues.includes(0),
    );
    for (const option of WEEK_START_OPTIONS) {
      check(
        "WEEK_START_OPTIONS entry " + option.value + " is frozen",
        Object.isFrozen(option),
      );
      check(
        "WEEK_START_OPTIONS entry " + option.value + " has a label key",
        typeof option.labelKey === "string" && option.labelKey.length > 0,
      );
    }

    check("normalizeWeekStart(0) returns 0", normalizeWeekStart(0) === 0);
    check("normalizeWeekStart(1) returns 1", normalizeWeekStart(1) === 1);
    check("normalizeWeekStart('0') returns 0", normalizeWeekStart("0") === 0);
    check("normalizeWeekStart('1') returns 1", normalizeWeekStart("1") === 1);
    check(
      "normalizeWeekStart trims a numeric string",
      normalizeWeekStart("  1  ") === 1,
    );
    check(
      "normalizeWeekStart unwraps { weekStartsOn: 0 }",
      normalizeWeekStart({ weekStartsOn: 0 }) === 0,
    );
    check(
      "normalizeWeekStart unwraps a numeric-string object",
      normalizeWeekStart({ weekStartsOn: "0" }) === 0,
    );

    const fallbackInputs = [
      null,
      undefined,
      2,
      -1,
      6,
      7,
      1.5,
      NaN,
      Infinity,
      -Infinity,
      "2",
      "-1",
      "",
      "   ",
      "monday",
      "sunday",
      true,
      false,
      {},
      [],
      [0],
      { weekStartsOn: 5 },
      { weekStartsOn: null },
      { weekStartsOn: {} },
    ];
    for (const value of fallbackInputs) {
      let result;
      let threw = false;
      try {
        result = normalizeWeekStart(value);
      } catch (error) {
        threw = true;
      }
      const label = "normalizeWeekStart(" + String(value) + ")";
      check(label + " does not throw", !threw);
      check(label + " falls back to the default", !threw && result === DEFAULT_WEEK_START);
    }

    const objectInput = { weekStartsOn: 0 };
    normalizeWeekStart(objectInput);
    check(
      "normalizeWeekStart does not mutate its input",
      objectInput.weekStartsOn === 0,
    );

    // 14 June 2026 is a Sunday; 15 June 2026 is a Monday (local construction).
    const sunday = new Date(2026, 5, 14, 9, 0, 0);
    const monday = new Date(2026, 5, 15, 9, 0, 0);
    check("fixture Sunday is a Sunday", sunday.getDay() === 0);
    check("fixture Monday is a Monday", monday.getDay() === 1);

    const now = new Date(2026, 5, 15, 12, 0, 0).getTime();
    const log = [
      { endedAt: sunday.toISOString(), phase: "work", durationSeconds: 600 },
      { endedAt: monday.toISOString(), phase: "work", durationSeconds: 1500 },
    ];
    const frozenLog = JSON.stringify(log);

    const sunWindow = weekWindow({ now, weekStartsOn: 0 });
    const monWindow = weekWindow({ now, weekStartsOn: 1 });
    check(
      "Sunday window starts on Sunday the 14th",
      new Date(sunWindow.start).getDay() === 0 &&
        new Date(sunWindow.start).getDate() === 14,
    );
    check(
      "Monday window starts on Monday the 15th",
      new Date(monWindow.start).getDay() === 1 &&
        new Date(monWindow.start).getDate() === 15,
    );
    check("Sunday window spans seven days", sunWindow.end - sunWindow.start === 7 * DAY);
    check("Monday window spans seven days", monWindow.end - monWindow.start === 7 * DAY);
    check(
      "weekWindow defaults to Monday",
      weekWindow({ now }).start === monWindow.start,
    );

    const sunGoal = goalProgress(log, { now, minutes: 100, weekStartsOn: 0 });
    const monGoal = goalProgress(log, { now, minutes: 100, weekStartsOn: 1 });
    check("Sunday start counts the Sunday entry", sunGoal.focusedMinutes === 35);
    check("Monday start excludes the Sunday entry", monGoal.focusedMinutes === 25);
    check("Sunday start reports the Sunday week start", sunGoal.weekStart === sunWindow.start);
    check("Monday start reports the Monday week start", monGoal.weekStart === monWindow.start);

    const sunReview = weeklyReview(log, { now, minutes: 100, weekStartsOn: 0 });
    const monReview = weeklyReview(log, { now, minutes: 100, weekStartsOn: 1 });
    check("weeklyReview Sunday start totals", sunReview.focusedMinutes === 35);
    check("weeklyReview Monday start totals", monReview.focusedMinutes === 25);
    check(
      "weeklyReview Sunday start counts two sessions",
      sunReview.perLabel[0].sessions === 2,
    );
    check(
      "weeklyReview Monday start counts one session",
      monReview.perLabel[0].sessions === 1,
    );

    const sundayMidnight = [
      { endedAt: new Date(2026, 5, 14, 0, 0, 0).toISOString(), phase: "work", durationSeconds: 600 },
    ];
    check(
      "Sunday midnight is inside a Sunday-start week",
      goalProgress(sundayMidnight, { now, minutes: 5, weekStartsOn: 0 }).focusedMinutes === 10,
    );
    check(
      "Sunday midnight is outside a Monday-start week",
      goalProgress(sundayMidnight, { now, minutes: 5, weekStartsOn: 1 }).focusedMinutes === 0,
    );

    check(
      "goalProgress does not mutate its input",
      JSON.stringify(log) === frozenLog,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class WeekStartStaticTests(unittest.TestCase):
    def test_history_exports_week_start_helpers(self):
        source = read(HISTORY_PATH)
        self.assertRegex(source, r"export\s+const\s+WEEK_START_OPTIONS\b")
        self.assertRegex(source, r"export\s+const\s+WEEK_START_STORAGE_SHAPE_VERSION\b")
        self.assertRegex(source, r"export\s+function\s+normalizeWeekStart\b")

    def test_index_html_has_week_start_select(self):
        html = read(INDEX_PATH)
        self.assertIn('id="week-start"', html)
        self.assertIn('name="weekStart"', html)
        self.assertIn('for="week-start"', html)
        self.assertRegex(html, r'value="1"')
        self.assertRegex(html, r'value="0"')
        for key in (
            "settings.weekStart",
            "settings.weekStartMonday",
            "settings.weekStartSunday",
        ):
            self.assertIn('data-i18n="%s"' % key, html, "index.html missing %s" % key)

    def test_index_html_defaults_to_monday(self):
        html = read(INDEX_PATH)
        match = re.search(r'<option value="1"([^>]*)>', html)
        self.assertIsNotNone(match, "index.html has no Monday option")
        self.assertIn("selected", match.group(1))

    def test_main_js_wires_up_week_start(self):
        js = read(MAIN_PATH)
        self.assertIn('"focus-flow:week-start"', js)
        self.assertIn("normalizeWeekStart", js)
        self.assertIn("weekStartsOn", js)
        self.assertIn("applyWeekStart", js)
        self.assertIn("announce.weekStart", js)
        self.assertIn('"week-start"', js)


class WeekStartI18nTests(unittest.TestCase):
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
class WeekStartLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-week-start-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        with open(os.path.join(cls.tmp_dir, "history.mjs"), "w", encoding="utf-8") as handle:
            handle.write(source)
        copy_history_dependencies(cls.tmp_dir)
        harness_path = os.path.join(cls.tmp_dir, "harness.mjs")
        with open(harness_path, "w", encoding="utf-8") as handle:
            handle.write(HARNESS)

        result = subprocess.run(
            [NODE_BIN, harness_path],
            capture_output=True,
            text=True,
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
            "week-start logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
