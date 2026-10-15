"""Tests for the Focus Flow ``streaks`` helper.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports ``streaks`` and stays free of
   DOM/network references.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   streak maths is verified for real. If ``node`` is missing the logic tests are
   skipped, mirroring the pattern used by ``test_history.py`` and
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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "app")
HISTORY_PATH = os.path.join(APP_DIR, "history.js")
NODE_BIN = shutil.which("node")

HARNESS = textwrap.dedent(
    """
    import { streaks } from "./history.mjs";

    const DAY = 24 * 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function localStart(ts) {
      const d = new Date(ts);
      return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    }

    function key(ts) {
      const d = new Date(ts);
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${d.getFullYear()}-${m}-${day}`;
    }

    const today = localStart(NOW);
    // `work(dayOffset, label, seconds)` builds a completed-work entry whose
    // calendar day is `dayOffset` days from today, at 09:00 local time.
    const work = (dayOffset, seconds = 1500) => ({
      endedAt: new Date(today + dayOffset * DAY + 9 * 60 * 60 * 1000).toISOString(),
      phase: "work",
      durationSeconds: seconds,
    });

    const empty = streaks([], { now: NOW });
    check("empty history has no current streak", empty.current === 0);
    check("empty history has no longest streak", empty.longest === 0);
    check("empty history logs nothing today", empty.todayCount === 0);
    check("empty history has no minutes today", empty.todayMinutes === 0);
    check("empty history has no last active day", empty.lastActiveDay === null);

    const single = streaks([work(0)], { now: NOW });
    check("single day reports current one", single.current === 1);
    check("single day reports longest one", single.longest === 1);
    check("single day counts today", single.todayCount === 1);
    check("single day sums today minutes", single.todayMinutes === 25);
    check("single day reports last active day", single.lastActiveDay === key(today));

    const consecutive = streaks([work(0), work(-1), work(-2)], { now: NOW });
    check("consecutive days report the run", consecutive.current === 3);
    check("consecutive days report the longest", consecutive.longest === 3);

    const gap = streaks([work(0), work(-1), work(-3)], { now: NOW });
    check("a gap ends the current streak", gap.current === 2);
    check("a gap keeps the longest run", gap.longest === 2);

    const endsYesterday = streaks([work(-1), work(-2), work(-3)], { now: NOW });
    check("a streak ending yesterday stays active", endsYesterday.current === 3);
    check("a streak ending yesterday logs nothing today", endsYesterday.todayCount === 0);
    check("a streak ending yesterday has no minutes today", endsYesterday.todayMinutes === 0);
    check(
      "a streak ending yesterday reports the last active day",
      endsYesterday.lastActiveDay === key(today - DAY),
    );

    const longestWins = streaks(
      [work(0), work(-1), work(-10), work(-11), work(-12), work(-13), work(-14)],
      { now: NOW },
    );
    check("longest can exceed current", longestWins.longest === 5);
    check("current counts the recent run only", longestWins.current === 2);

    const pastOnly = streaks([work(-3), work(-4), work(-5)], { now: NOW });
    check("a stale run leaves current at zero", pastOnly.current === 0);
    check("a stale run still sets longest", pastOnly.longest === 3);

    const sameDay = streaks([work(0, 600), work(0, 900), work(0, 300)], { now: NOW });
    check("multiple sessions on one day are one streak day", sameDay.current === 1);
    check("multiple sessions count today", sameDay.todayCount === 3);
    check("multiple sessions sum today minutes", sameDay.todayMinutes === 30);

    const malformed = streaks(
      [
        null,
        42,
        { phase: "work" },
        { endedAt: "not-a-date", phase: "work", durationSeconds: 60 },
        { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: -5 },
      ],
      { now: NOW },
    );
    check("malformed entries are ignored", malformed.current === 0);
    check("malformed entries produce no longest", malformed.longest === 0);
    check("malformed entries log nothing today", malformed.todayCount === 0);
    check("malformed entries have no last active day", malformed.lastActiveDay === null);

    const nonWork = streaks(
      [
        { endedAt: new Date(today + 9 * 60 * 60 * 1000).toISOString(), phase: "shortBreak", durationSeconds: 300 },
        { endedAt: new Date(today + 10 * 60 * 60 * 1000).toISOString(), phase: "longBreak", durationSeconds: 900 },
      ],
      { now: NOW },
    );
    check("non-work phases are ignored", nonWork.current === 0);
    check("non-work phases produce no longest", nonWork.longest === 0);

    const mixed = [
      work(0),
      { endedAt: new Date(today + 9 * 60 * 60 * 1000).toISOString(), phase: "shortBreak", durationSeconds: 300 },
      work(-1),
    ];
    const frozen = JSON.stringify(mixed);
    const mixedResult = streaks(mixed, { now: NOW });
    check("mixed log counts only work days", mixedResult.current === 2);
    check("streaks does not mutate its input", JSON.stringify(mixed) === frozen);

    check("streaks tolerates a missing log", streaks(null, { now: NOW }).current === 0);
    check(
      "streaks accepts an explicit week start",
      streaks([work(0)], { now: NOW, weekStartsOn: 0 }).current === 1,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


DST_HARNESS = textwrap.dedent(
    """
    import { streaks } from "./history.mjs";

    const spec = JSON.parse(process.argv[2]);
    const failures = [];

    for (const testCase of spec.cases) {
      const [ny, nm, nd, nh] = testCase.now;
      const now = new Date(ny, nm - 1, nd, nh).getTime();
      const log = testCase.days.map(([y, m, d, h]) => ({
        endedAt: new Date(y, m - 1, d, h).toISOString(),
        phase: "work",
        durationSeconds: 1500,
      }));
      const result = streaks(log, { now });
      if (result.current !== testCase.expected) {
        failures.push(`${testCase.name}: current ${result.current} !== ${testCase.expected}`);
      }
      if (result.longest !== testCase.expected) {
        failures.push(`${testCase.name}: longest ${result.longest} !== ${testCase.expected}`);
      }
    }

    process.stdout.write(JSON.stringify({ failures }));
    """
)

# Each case is a run of consecutive local calendar days that straddles a DST
# transition in the given timezone. `expected` is 3: the calendar run must be
# counted as three consecutive days even though one of the nights is 23h/25h.
DST_TZ_CASES = {
    "America/New_York": [
        {
            "name": "spring forward",
            "now": [2026, 3, 9, 12],
            "days": [[2026, 3, 7, 9], [2026, 3, 8, 9], [2026, 3, 9, 9]],
            "expected": 3,
        },
        {
            "name": "fall back",
            "now": [2026, 11, 2, 12],
            "days": [[2026, 10, 31, 9], [2026, 11, 1, 9], [2026, 11, 2, 9]],
            "expected": 3,
        },
    ],
    "Europe/London": [
        {
            "name": "spring forward",
            "now": [2026, 3, 30, 12],
            "days": [[2026, 3, 28, 9], [2026, 3, 29, 9], [2026, 3, 30, 9]],
            "expected": 3,
        },
        {
            "name": "fall back",
            "now": [2026, 10, 26, 12],
            "days": [[2026, 10, 24, 9], [2026, 10, 25, 9], [2026, 10, 26, 9]],
            "expected": 3,
        },
    ],
}


class StreaksStaticTests(unittest.TestCase):
    def test_history_exports_streaks(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(
            source,
            r"export\s+function\s+streaks\b",
            "history.js does not export streaks",
        )

    def test_streaks_stays_pure(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"document|window", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_streaks_uses_calendar_day_arithmetic(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn(
            "DAY_MS",
            source[source.index("export function streaks"):],
            "streaks must not step days with the fixed DAY_MS constant (DST bug)",
        )


class StreaksStaticAssetTests(unittest.TestCase):
    def test_stats_streak_and_reminder_markup(self):
        with open(os.path.join(APP_DIR, "index.html"), encoding="utf-8") as handle:
            html = handle.read()
        for fragment in (
            'id="stats-streak"',
            'id="stats-streak-current"',
            'id="stats-streak-longest"',
            'id="stats-streak-today"',
            'id="stats-reminder"',
        ):
            self.assertIn(fragment, html, "index.html missing %s" % fragment)
        self.assertIn("Current streak", html)
        self.assertIn("Longest streak", html)
        self.assertIn("No focus session logged today yet.", html)

    def test_main_js_references_streak_elements(self):
        with open(os.path.join(APP_DIR, "main.js"), encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn("streaks", js)
        self.assertIn('"stats-streak"', js)
        self.assertIn('"stats-streak-current"', js)
        self.assertIn('"stats-streak-longest"', js)
        self.assertIn('"stats-streak-today"', js)
        self.assertIn('"stats-reminder"', js)
        self.assertIn("renderStreak", js)


@unittest.skipUnless(NODE_BIN, "node is not installed")
class StreaksLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-streaks-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        module_path = os.path.join(cls.tmp_dir, "history.mjs")
        with open(module_path, "w", encoding="utf-8") as handle:
            handle.write(source)
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
            "streaks logic failures: %s" % ", ".join(self.payload["failures"]),
        )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class StreaksDstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-streaks-dst-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        with open(os.path.join(cls.tmp_dir, "history.mjs"), "w", encoding="utf-8") as handle:
            handle.write(source)
        with open(os.path.join(cls.tmp_dir, "harness.mjs"), "w", encoding="utf-8") as handle:
            handle.write(DST_HARNESS)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def _run(self, timezone, cases):
        env = dict(os.environ, TZ=timezone)
        result = subprocess.run(
            [NODE_BIN, os.path.join(self.tmp_dir, "harness.mjs"), json.dumps({"cases": cases})],
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise AssertionError(
                "node DST harness failed for %s (exit %s):\n%s\n%s"
                % (timezone, result.returncode, result.stdout, result.stderr)
            )
        return json.loads(result.stdout)

    def test_streaks_survive_dst_transitions(self):
        for timezone, cases in DST_TZ_CASES.items():
            with self.subTest(timezone=timezone):
                payload = self._run(timezone, cases)
                self.assertEqual(
                    payload["failures"],
                    [],
                    "DST streak failures in %s: %s"
                    % (timezone, ", ".join(payload["failures"])),
                )


if __name__ == "__main__":
    unittest.main()
