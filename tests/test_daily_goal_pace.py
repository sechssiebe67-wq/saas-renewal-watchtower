"""Tests for the Focus Flow ``dailyGoalPace`` helper.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``dailyGoalPace`` and stays free
   of DOM/storage/network references, that ``app/main.js`` renders the daily pace
   line and reads the new catalog keys, and that ``app/index.html`` carries the
   new markup.
2. A static check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``dailyGoalPace`` helper is
   exercised against real ``dailyReview`` results so the remaining-minute,
   remaining-hour (including the current hour), per-hour pace, on-track signal,
   label scoping, alias map, and daylight-saving boundaries are verified for
   real. The harness runs with a ``TZ`` that observes daylight saving so the
   local-hour arithmetic is genuinely tested.
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
    "stats.dailyGoalPaceLabel",
    "stats.dailyGoalPaceLine",
    "stats.dailyGoalPaceHoursOne",
    "stats.dailyGoalPaceHoursMany",
    "stats.dailyGoalPaceOnTrack",
    "stats.dailyGoalPaceBehind",
    "announce.dailyGoalPace",
)

HARNESS = textwrap.dedent(
    """
    import { dailyGoalPace, dailyReview } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    // A fixed local wall-clock instant so the hour-of-day is deterministic
    // whatever the time zone. 10:00 local leaves 14 whole local hours.
    const midNow = new Date(2026, 5, 15, 10, 0, 0).getTime();

    // --- no goal -> no projection ------------------------------------------
    for (const value of [null, undefined, {}, [], 42, "nope"]) {
      let result;
      let threw = false;
      try {
        result = dailyGoalPace(value, { now: Date.now() });
      } catch (error) {
        threw = true;
      }
      check("dailyGoalPace(" + String(value) + ") does not throw", !threw);
      check("dailyGoalPace(" + String(value) + ") is null", !threw && result === null);
    }
    check(
      "a zero target yields no projection",
      dailyGoalPace({ targetMinutes: 0, focusedMinutes: 10 }) === null,
    );
    check(
      "a negative target yields no projection",
      dailyGoalPace({ targetMinutes: -30, focusedMinutes: 0 }) === null,
    );
    check(
      "a non-numeric target yields no projection",
      dailyGoalPace({ targetMinutes: "abc", focusedMinutes: 0 }) === null,
    );

    // --- goal already met ---------------------------------------------------
    const met = dailyGoalPace(
      { targetMinutes: 100, focusedMinutes: 150 },
      { now: midNow },
    );
    check("met goal returns a projection", met !== null);
    check("met goal reports no remaining minutes", met.remainingMinutes === 0);
    check("met goal reports a zero per-hour pace", met.perHourMinutes === 0);
    check("met goal is reached", met.reached === true);
    check("met goal is on track", met.onTrack === true);
    check(
      "met goal reports a sane remaining-hour count",
      met.remainingHours >= 1 && met.remainingHours <= 24,
    );

    // --- partial progress mid-day ------------------------------------------
    const midLog = [
      {
        endedAt: new Date(2026, 5, 15, 9, 0, 0).toISOString(),
        phase: "work",
        durationSeconds: 30 * 60,
      },
    ];
    const midReview = dailyReview(midLog, {
      now: midNow,
      goal: { minutes: 120 },
    });
    const mid = dailyGoalPace(midReview, { now: midNow });
    check("mid-day projection exists", mid !== null);
    check("mid-day focused minutes flow through", midReview.focusedMinutes === 30);
    check("mid-day removes the focused minutes", mid.remainingMinutes === 90);
    check("mid-day counts the whole hours left including this one", mid.remainingHours === 14);
    check("mid-day rounds the per-hour pace", mid.perHourMinutes === 6);
    check("mid-day is not reached", mid.reached === false);
    check("mid-day is behind pace", mid.onTrack === false);

    const fast = dailyGoalPace(
      { targetMinutes: 120, focusedMinutes: 100 },
      { now: midNow },
    );
    check("a fast pace is on track", fast.onTrack === true);
    check("a fast pace keeps the remaining minutes", fast.remainingMinutes === 20);
    check("a fast pace rounds the per-hour pace", fast.perHourMinutes === 1);

    // The current hour counts even at the edges of the day.
    const lateNow = new Date(2026, 5, 15, 23, 30, 0).getTime();
    check(
      "the last hour of the day still counts",
      dailyGoalPace({ targetMinutes: 60, focusedMinutes: 0 }, { now: lateNow })
        .remainingHours === 1,
    );
    const earlyNow = new Date(2026, 5, 15, 0, 30, 0).getTime();
    check(
      "the first hour of the day counts all 24",
      dailyGoalPace({ targetMinutes: 60, focusedMinutes: 0 }, { now: earlyNow })
        .remainingHours === 24,
    );

    // --- label-scoped goal --------------------------------------------------
    const scopedLog = [
      {
        endedAt: new Date(2026, 5, 15, 8, 0, 0).toISOString(),
        phase: "work",
        durationSeconds: 20 * 60,
        label: "Thesis",
      },
      {
        endedAt: new Date(2026, 5, 15, 9, 0, 0).toISOString(),
        phase: "work",
        durationSeconds: 40 * 60,
        label: "Admin",
      },
    ];
    const scopedReview = dailyReview(scopedLog, {
      now: midNow,
      goal: { minutes: 60, label: "Thesis" },
    });
    const scopedPace = dailyGoalPace(scopedReview, { now: midNow });
    check("a scoped review counts only the matching label", scopedReview.focusedMinutes === 20);
    check("a scoped pace removes only the matching minutes", scopedPace.remainingMinutes === 40);

    // --- alias map applied consistently with dailyReview --------------------
    const aliasReview = dailyReview(scopedLog, {
      now: midNow,
      goal: { minutes: 60, label: "PhD" },
      tags: { Thesis: "PhD", Admin: "PhD" },
    });
    check(
      "an alias-scoped review merges the aliased labels",
      aliasReview.focusedMinutes === 60,
    );
    check(
      "over an aliased goal the pace is reached",
      dailyGoalPace(aliasReview, { now: midNow }).remainingMinutes === 0,
    );
    const aliasAll = dailyReview(scopedLog, {
      now: midNow,
      goal: { minutes: 100 },
      tags: { Thesis: "PhD", Admin: "PhD" },
    });
    check(
      "the alias map feeds the review total",
      dailyGoalPace(aliasAll, { now: midNow }).remainingMinutes === 40,
    );

    // --- daylight-saving day ------------------------------------------------
    // The US spring-forward is Sunday 8 March 2026; a day with a DST
    // transition must still yield a sane remaining-hour count.
    const dstNoon = new Date(2026, 2, 8, 12, 0, 0).getTime();
    const dst = dailyGoalPace(
      { targetMinutes: 120, focusedMinutes: 30 },
      { now: dstNoon },
    );
    check("DST noon counts the hours left", dst.remainingHours === 12);
    check(
      "DST remaining hours stay sane",
      dst.remainingHours >= 1 && dst.remainingHours <= 24,
    );
    const dstEarly = dailyGoalPace(
      { targetMinutes: 120, focusedMinutes: 30 },
      { now: new Date(2026, 2, 8, 1, 30, 0).getTime() },
    );
    check("DST early morning counts the hours left", dstEarly.remainingHours === 23);

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
        result = dailyGoalPace(review, { now: midNow });
      } catch (error) {
        threw = true;
      }
      check("malformed review does not throw", !threw);
      check("malformed review still projects", !threw && result !== null);
      check(
        "malformed focused minutes degrade to the full target",
        !threw && result.remainingMinutes === 100,
      );
    }

    const frozenReview = { targetMinutes: 120, focusedMinutes: 30 };
    const frozen = JSON.stringify(frozenReview);
    dailyGoalPace(frozenReview, { now: midNow });
    check(
      "dailyGoalPace never mutates its input",
      JSON.stringify(frozenReview) === frozen,
    );
    check(
      "dailyGoalPace survives a malformed now",
      dailyGoalPace({ targetMinutes: 120, focusedMinutes: 30 }, {
        now: "not-a-date",
      }) !== null,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class DailyGoalPaceStaticTests(unittest.TestCase):
    def test_history_exports_daily_goal_pace(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+dailyGoalPace\b",
            "history.js does not export dailyGoalPace",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("localStorage", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_daily_pace_line(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-daily-goal-pace"', html)
        self.assertIn(
            'data-i18n-attr="aria-label:stats.dailyGoalPaceLabel"', html
        )
        self.assertRegex(
            html,
            r'<p\s+id="stats-daily-goal-pace"[\s\S]*?hidden',
            "the daily goal pace line must start hidden",
        )

    def test_main_js_renders_daily_goal_pace(self):
        js = read(MAIN_PATH)
        for symbol in (
            "dailyGoalPace",
            "renderDailyGoalPace",
            "hideDailyGoalPace",
            "stats-daily-goal-pace",
            "announce.dailyGoalPace",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)


class DailyGoalPaceI18nTests(unittest.TestCase):
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
class DailyGoalPaceLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-daily-goal-pace-")
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

        # Run in a time zone that observes daylight saving so the local-hour
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
            "dailyGoalPace logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
