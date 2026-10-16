"""Tests for the Focus Flow ``goalPace`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``goalPace`` and that
   ``app/main.js`` renders the projection and reads the new catalog keys.
2. A static check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``goalPace`` helper is
   exercised against real ``weeklyReview`` results so the remaining-day count,
   the per-day pace, the on-track signal, and the Sunday/Monday and
   daylight-saving boundaries are verified for real. The harness runs with a
   ``TZ`` that observes daylight saving so the calendar arithmetic is genuinely
   tested.
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
    "stats.goalPaceLabel",
    "stats.goalPaceLine",
    "stats.goalPaceDaysOne",
    "stats.goalPaceDaysMany",
    "stats.goalPaceOnTrack",
    "stats.goalPaceBehind",
    "announce.goalPace",
)

HARNESS = textwrap.dedent(
    """
    import { goalPace, weekWindow, weeklyReview } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    // --- no goal -> no projection ------------------------------------------
    for (const value of [null, undefined, {}, [], 42, "nope"]) {
      let result;
      let threw = false;
      try {
        result = goalPace(value, { now: Date.now() });
      } catch (error) {
        threw = true;
      }
      check("goalPace(" + String(value) + ") does not throw", !threw);
      check("goalPace(" + String(value) + ") is null", !threw && result === null);
    }
    check(
      "a zero target yields no projection",
      goalPace({ targetMinutes: 0, focusedMinutes: 10 }) === null,
    );
    check(
      "a negative target yields no projection",
      goalPace({ targetMinutes: -30, focusedMinutes: 0 }) === null,
    );
    check(
      "a non-numeric target yields no projection",
      goalPace({ targetMinutes: "abc", focusedMinutes: 0 }) === null,
    );

    // --- goal already met ---------------------------------------------------
    const met = goalPace(
      { targetMinutes: 100, focusedMinutes: 150 },
      { now: Date.now(), weekStart: 1 },
    );
    check("met goal returns a projection", met !== null);
    check("met goal reports no remaining minutes", met.remainingMinutes === 0);
    check("met goal reports a zero per-day pace", met.perDayMinutes === 0);
    check("met goal is on track", met.onTrack === true);
    check(
      "met goal reports a remaining-day count in 1..7",
      met.remainingDays >= 1 && met.remainingDays <= 7,
    );

    // --- partial progress mid-week (Monday week start) ----------------------
    // Wednesday 17 June 2026 is mid-week for a Monday-start week.
    const midNow = new Date(2026, 5, 17, 12, 0, 0).getTime();
    const midWindow = weekWindow({ now: midNow, weekStartsOn: 1 });
    const midLog = [
      {
        endedAt: new Date(midWindow.start + 1 * HOUR).toISOString(),
        phase: "work",
        durationSeconds: 90 * 60,
      },
    ];
    const midReview = weeklyReview(midLog, {
      now: midNow,
      minutes: 300,
      weekStartsOn: 1,
    });
    const mid = goalPace(midReview, { now: midNow, weekStart: 1 });
    check("mid-week projection exists", mid !== null);
    check("mid-week focused minutes flow through", midReview.focusedMinutes === 90);
    check("mid-week removes the focused minutes", mid.remainingMinutes === 210);
    check("mid-week counts five remaining days", mid.remainingDays === 5);
    check("mid-week rounds the per-day pace", mid.perDayMinutes === 42);
    check("mid-week is behind pace", mid.onTrack === false);

    const onTrack = goalPace(
      { targetMinutes: 300, focusedMinutes: 120 },
      { now: midNow, weekStart: 1 },
    );
    check("a fast pace is on track", onTrack.onTrack === true);
    check("a fast pace keeps the remaining minutes", onTrack.remainingMinutes === 180);
    check("a fast pace rounds the per-day pace", onTrack.perDayMinutes === 36);

    // --- Sunday vs Monday week start ---------------------------------------
    // Sunday 14 June 2026 starts the week for a Sunday-first user but ends the
    // previous week for a Monday-first user.
    const sundayNow = new Date(2026, 5, 14, 12, 0, 0).getTime();
    const sundayStart = goalPace(
      { targetMinutes: 300, focusedMinutes: 0 },
      { now: sundayNow, weekStart: 0 },
    );
    const mondayStart = goalPace(
      { targetMinutes: 300, focusedMinutes: 0 },
      { now: sundayNow, weekStart: 1 },
    );
    check("a Sunday start has seven days left", sundayStart.remainingDays === 7);
    check("a Monday start has one day left on Sunday", mondayStart.remainingDays === 1);
    check(
      "the week-start option name is also accepted",
      goalPace({ targetMinutes: 300, focusedMinutes: 0 }, {
        now: sundayNow,
        weekStartsOn: 1,
      }).remainingDays === 1,
    );
    check(
      "the week-start preference defaults to Monday",
      goalPace({ targetMinutes: 300, focusedMinutes: 0 }, { now: sundayNow })
        .remainingDays === 1,
    );

    // --- daylight-saving boundary week -------------------------------------
    // The US spring-forward is Sunday 8 March 2026; a Monday-start week that
    // contains it is 2..8 March. Calendar arithmetic must still count exactly
    // the days that remain (4..8 March = 5 days) even though the span is only
    // 167 wall-clock hours.
    const dstNow = new Date(2026, 2, 4, 12, 0, 0).getTime();
    const dst = goalPace(
      { targetMinutes: 300, focusedMinutes: 90 },
      { now: dstNow, weekStart: 1 },
    );
    check("DST week removes the focused minutes", dst.remainingMinutes === 210);
    check("DST week counts five remaining days", dst.remainingDays === 5);
    check("DST week rounds the per-day pace", dst.perDayMinutes === 42);
    check("DST week is behind pace", dst.onTrack === false);

    // --- robustness ---------------------------------------------------------
    const malformed = [
      { targetMinutes: 100 },
      { targetMinutes: 100, focusedMinutes: "abc" },
      { targetMinutes: 100, focusedMinutes: -50 },
    ];
    for (const review of malformed) {
      let threw = false;
      let result;
      try {
        result = goalPace(review, { now: midNow, weekStart: 1 });
      } catch (error) {
        threw = true;
      }
      check("malformed review does not throw", !threw);
      check("malformed review still projects", !threw && result !== null);
    }

    const frozenReview = { targetMinutes: 300, focusedMinutes: 90 };
    const frozen = JSON.stringify(frozenReview);
    goalPace(frozenReview, { now: midNow, weekStart: 1 });
    check(
      "goalPace never mutates its input",
      JSON.stringify(frozenReview) === frozen,
    );
    check(
      "goalPace survives a malformed now",
      goalPace({ targetMinutes: 300, focusedMinutes: 90 }, {
        now: "not-a-date",
        weekStart: 1,
      }) !== null,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class GoalPaceStaticTests(unittest.TestCase):
    def test_history_exports_goal_pace(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+goalPace\b",
            "history.js does not export goalPace",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_pace_line(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-goal-pace"', html)
        self.assertIn("data-i18n-attr=\"aria-label:stats.goalPaceLabel\"", html)

    def test_main_js_renders_goal_pace(self):
        js = read(MAIN_PATH)
        self.assertIn("goalPace", js)
        self.assertIn("renderGoalPace", js)
        self.assertIn("stats-goal-pace", js)
        self.assertIn("announce.goalPace", js)


class GoalPaceI18nTests(unittest.TestCase):
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
class GoalPaceLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-goal-pace-")
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
            "goalPace logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
