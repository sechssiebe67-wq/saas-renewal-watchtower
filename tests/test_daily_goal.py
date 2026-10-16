"""Tests for the Focus Flow daily focus goal.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports the daily-goal helpers and
   stays free of DOM/network references, that every new ``app/i18n.js`` message
   key is present in all three locales, and that ``index.html`` carries the new
   settings controls and Stats row.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   daily-goal maths is verified for real. If ``node`` is missing the logic tests
   are skipped, mirroring the pattern used by ``test_history.py`` and
   ``test_weekly_review.py``.
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

HARNESS = textwrap.dedent(
    """
    import {
      DAILY_GOAL_STORAGE_SHAPE_VERSION,
      MAX_DAILY_GOAL_MINUTES,
      MAX_LABEL_LENGTH,
      UNLABELLED,
      normalizeDailyGoal,
      dailyGoalProgress,
    } from "./history.mjs";

    const DAY = 24 * 60 * 60 * 1000;
    const HOUR = 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function localStart(ts) {
      const d = new Date(ts);
      return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    }

    const today = localStart(NOW);
    // `work(dayOffset, seconds, label)` builds a completed-work entry whose
    // local calendar day is `dayOffset` days from today, at 09:00 local time.
    function work(dayOffset, seconds = 1500, label) {
      const entry = {
        endedAt: new Date(today + dayOffset * DAY + 9 * HOUR).toISOString(),
        phase: "work",
        durationSeconds: seconds,
      };
      if (label !== undefined) entry.label = label;
      return entry;
    }

    check(
      "DAILY_GOAL_STORAGE_SHAPE_VERSION is a positive integer",
      Number.isInteger(DAILY_GOAL_STORAGE_SHAPE_VERSION) &&
        DAILY_GOAL_STORAGE_SHAPE_VERSION > 0,
    );
    check("MAX_DAILY_GOAL_MINUTES is a full day", MAX_DAILY_GOAL_MINUTES === 1440);

    // Normalisation: every tricky input coerces without throwing.
    check("normalizeDailyGoal defaults null to zero", normalizeDailyGoal(null).minutes === 0);
    check("normalizeDailyGoal tolerates undefined", normalizeDailyGoal(undefined).minutes === 0);
    check("normalizeDailyGoal tolerates garbage", normalizeDailyGoal("nonsense").minutes === 0);
    check("normalizeDailyGoal tolerates an empty object", normalizeDailyGoal({}).minutes === 0);
    check("normalizeDailyGoal keeps a valid goal", normalizeDailyGoal({ minutes: 50 }).minutes === 50);
    check("normalizeDailyGoal accepts a bare number", normalizeDailyGoal(120).minutes === 120);
    check(
      "normalizeDailyGoal accepts a numeric string",
      normalizeDailyGoal({ minutes: "45" }).minutes === 45,
    );
    check(
      "normalizeDailyGoal rounds to whole minutes",
      normalizeDailyGoal({ minutes: 49.6 }).minutes === 50,
    );
    check(
      "normalizeDailyGoal clamps above a day",
      normalizeDailyGoal({ minutes: 99999 }).minutes === MAX_DAILY_GOAL_MINUTES,
    );
    check("normalizeDailyGoal clamps below zero", normalizeDailyGoal({ minutes: -50 }).minutes === 0);
    check("normalizeDailyGoal clamps a negative number", normalizeDailyGoal(-5).minutes === 0);
    check(
      "normalizeDailyGoal trims and keeps a label",
      normalizeDailyGoal({ minutes: 60, label: "  Thesis  " }).label === "Thesis",
    );
    check(
      "normalizeDailyGoal drops an empty label",
      !("label" in normalizeDailyGoal({ minutes: 60, label: "   " })),
    );
    check(
      "normalizeDailyGoal truncates a long label",
      normalizeDailyGoal({ minutes: 60, label: "x".repeat(120) }).label.length ===
        MAX_LABEL_LENGTH,
    );
    const goalInput = { minutes: 60, label: "Thesis" };
    normalizeDailyGoal(goalInput);
    check(
      "normalizeDailyGoal does not mutate its input",
      goalInput.minutes === 60 && goalInput.label === "Thesis",
    );

    // Progress: the exact acceptance examples.
    const empty = dailyGoalProgress([], { now: NOW, minutes: 50 });
    check("empty log reports the target", empty.targetMinutes === 50);
    check("empty log reports zero focused minutes", empty.focusedMinutes === 0);
    check("empty log reports the remaining minutes", empty.remainingMinutes === 50);
    check("empty log reports zero percent", empty.percent === 0);
    check("empty log is not reached", empty.reached === false);
    check("empty log returns the local day start", empty.dayStart === today);

    const exact = dailyGoalProgress([work(0, 3000)], { now: NOW, minutes: 50 });
    check("exact target sums focused minutes", exact.focusedMinutes === 50);
    check("exact target is reached", exact.reached === true);
    check("exact target reports full percent", exact.percent === 100);
    check("exact target reports no remaining", exact.remainingMinutes === 0);

    const half = dailyGoalProgress([work(0, 1500)], { now: NOW, minutes: 50 });
    check("half target sums focused minutes", half.focusedMinutes === 25);
    check("half target is not reached", half.reached === false);
    check("half target reports 50 percent", half.percent === 50);
    check("half target reports the remainder", half.remainingMinutes === 25);

    const noon = dailyGoalProgress(
      [{ endedAt: new Date(today + 12 * HOUR).toISOString(), phase: "work", durationSeconds: 1500 }],
      { now: NOW, minutes: 10 },
    );
    check("entries later today still count", noon.focusedMinutes === 25);

    const yesterday = dailyGoalProgress([work(-1, 1500)], { now: NOW, minutes: 10 });
    check("entries from yesterday do not count", yesterday.focusedMinutes === 0);
    check("yesterday is not reached", yesterday.reached === false);

    const tomorrow = dailyGoalProgress([work(1, 1500)], { now: NOW, minutes: 10 });
    check("entries from tomorrow do not count", tomorrow.focusedMinutes === 0);

    const mixed = [
      work(0, 1500, "Thesis"),
      work(0, 1500, "Admin"),
      work(0, 600),
      work(-1, 3000, "Thesis"),
    ];
    const frozen = JSON.stringify(mixed);
    const scoped = dailyGoalProgress(mixed, { now: NOW, minutes: 20, label: "Thesis" });
    check("label scoping sums only the matching label", scoped.focusedMinutes === 25);
    check("label scoping reaches the scoped goal", scoped.reached === true);

    const admin = dailyGoalProgress(mixed, { now: NOW, minutes: 20, label: "Admin" });
    check("label scoping keeps other labels separate", admin.focusedMinutes === 25);

    const unlabelled = dailyGoalProgress(mixed, { now: NOW, minutes: 5, label: UNLABELLED });
    check("UNLABELLED counts entries without a label", unlabelled.focusedMinutes === 10);

    const allToday = dailyGoalProgress(mixed, { now: NOW, minutes: 100 });
    check("unscoped progress sums today only", allToday.focusedMinutes === 60);
    check("dailyGoalProgress does not mutate its input", JSON.stringify(mixed) === frozen);

    const malformed = dailyGoalProgress(
      [
        null,
        42,
        { phase: "work" },
        { phase: "shortBreak", endedAt: new Date(today + HOUR).toISOString(), durationSeconds: 300 },
        { phase: "longBreak", endedAt: new Date(today + 2 * HOUR).toISOString(), durationSeconds: 900 },
        { endedAt: "not-a-date", phase: "work", durationSeconds: 60 },
        { endedAt: new Date(today + 3 * HOUR).toISOString(), phase: "work", durationSeconds: -5 },
      ],
      { now: NOW, minutes: 5 },
    );
    check("malformed entries and non-work phases are ignored", malformed.focusedMinutes === 0);
    check(
      "dailyGoalProgress tolerates a missing log",
      dailyGoalProgress(null, { now: NOW, minutes: 5 }).focusedMinutes === 0,
    );

    const none = dailyGoalProgress([work(0, 1500)], { now: NOW, minutes: 0 });
    check("no goal defines percent as 100", none.percent === 100);
    check("no goal is not reached", none.reached === false);
    check(
      "dailyGoalProgress handles a missing target",
      dailyGoalProgress([work(0, 1500)], { now: NOW }).targetMinutes === 0,
    );

    const clampedTarget = dailyGoalProgress([work(0, 3000)], {
      now: NOW,
      minutes: 99999,
    });
    check(
      "dailyGoalProgress clamps the target",
      clampedTarget.targetMinutes === MAX_DAILY_GOAL_MINUTES,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def extract_submit_handler(source):
    """Return the body of ``el.form``'s submit listener, or ``None``.

    A simple brace-matching scan is enough for this single listener and avoids
    pulling in a JavaScript parser just to guard an ordering regression.
    """
    marker = 'el.form.addEventListener("submit"'
    start = source.find(marker)
    if start == -1:
        return None
    brace = source.find("{", start)
    if brace == -1:
        return None
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    return None


DAILY_I18N_KEYS = (
    "settings.dailyGoal",
    "settings.dailyGoalPlaceholder",
    "settings.dailyGoalHint",
    "settings.clearDailyGoal",
    "stats.dailyGoal",
    "stats.dailyGoalBarLabel",
    "stats.dailyGoalReached",
    "announce.dailyGoalReached",
    "announce.dailyGoalSaved",
    "announce.dailyGoalCleared",
)


class DailyGoalStaticTests(unittest.TestCase):
    def test_history_exports_daily_goal_helpers(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(
            source,
            r"export\s+const\s+DAILY_GOAL_STORAGE_SHAPE_VERSION\b",
            "history.js does not export DAILY_GOAL_STORAGE_SHAPE_VERSION",
        )
        for function in ("normalizeDailyGoal", "dailyGoalProgress"):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "history.js does not export %s" % function,
            )

    def test_daily_goal_helpers_stay_pure(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_daily_goal_keys_present_in_every_locale(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
            self.assertIsNotNone(match, "could not find %s" % name)
            block = match.group(1)
            for key in DAILY_I18N_KEYS:
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )

    def test_index_html_has_daily_goal_controls_and_row(self):
        with open(INDEX_PATH, encoding="utf-8") as handle:
            html = handle.read()
        for fragment in (
            'id="daily-goal"',
            'id="clear-daily-goal"',
            'id="stats-daily-goal"',
            'id="stats-daily-goal-bar"',
            'id="stats-daily-goal-reached"',
        ):
            self.assertIn(fragment, html, "index.html missing %s" % fragment)
        self.assertIn('name="dailyGoal"', html)
        self.assertIn('data-i18n="settings.dailyGoal"', html)
        self.assertIn('data-i18n="stats.dailyGoal"', html)
        self.assertRegex(
            html,
            r'<div\s+id="stats-daily-goal"[\s\S]*?hidden',
            "the stats daily goal row must start hidden",
        )

    def test_main_js_wires_daily_goal(self):
        with open(MAIN_PATH, encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn('"focus-flow:daily-goal"', js)
        for symbol in (
            "normalizeDailyGoal",
            "dailyGoalProgress",
            "renderDailyGoal",
            "applyDailyGoal",
            "persistDailyGoal",
            "announce.dailyGoalReached",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_submit_saves_typed_goals_not_clobbered_inputs(self):
        """Regression: ``applyGoal`` calls ``syncForm``, which rewrites the
        daily-goal input from the old stored value. The submit handler must read
        both inputs *before* applying either, otherwise the daily goal typed by
        the user is discarded and the old value (or a clear) is saved."""
        with open(MAIN_PATH, encoding="utf-8") as handle:
            js = handle.read()
        handler = extract_submit_handler(js)
        self.assertIsNotNone(
            handler, "could not find the form submit handler in main.js"
        )
        self.assertIsNone(
            re.search(r"apply(?:Daily)?Goal\s*\(\s*el\.inputs", handler),
            "submit handler calls an apply*Goal function with a live "
            "el.inputs read; capture both field values first",
        )
        self.assertRegex(
            handler,
            r"const\s+\w*[Dd]ailyGoal\w*\s*=\s*el\.inputs\.dailyGoal",
            "submit handler must capture the daily-goal input into a local "
            "before calling applyDailyGoal",
        )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class DailyGoalLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-daily-goal-")
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
            "daily goal logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
