"""Tests for the Focus Flow session-history module.

Two layers of coverage:

1. Static checks that ``app/history.js`` exists, exports the expected symbols,
   and stays free of DOM/network references.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   logic is verified for real. If ``node`` is missing the logic tests are
   skipped, mirroring the optional-runtime pattern used elsewhere.
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
    import {
      HISTORY_VERSION,
      GOAL_STORAGE_SHAPE_VERSION,
      MIN_GOAL_MINUTES,
      MAX_GOAL_MINUTES,
      MAX_LABEL_LENGTH,
      DEFAULT_WEEK_START,
      UNLABELLED,
      recordSession,
      pruneHistory,
      summarise,
      labelSummary,
      recentSessions,
      normalizeGoal,
      weekWindow,
      goalProgress,
    } from "./history.mjs";

    const DAY = 24 * 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    check(
      "HISTORY_VERSION is a positive integer",
      Number.isInteger(HISTORY_VERSION) && HISTORY_VERSION > 0,
    );

    const base = [];
    const recorded = recordSession(base, {
      endedAt: new Date(NOW).toISOString(),
      phase: "work",
      durationSeconds: 1500,
    });
    check("recordSession does not mutate its input", base.length === 0);
    check("recordSession appends one work entry", recorded.length === 1);
    check("recordSession stores the work phase", recorded[0].phase === "work");
    check("recordSession stores durationSeconds", recorded[0].durationSeconds === 1500);
    check(
      "recordSession stores an ISO endedAt",
      recorded[0].endedAt === new Date(NOW).toISOString(),
    );

    check(
      "recordSession ignores break phases",
      recordSession(base, {
        endedAt: new Date(NOW).toISOString(),
        phase: "shortBreak",
        durationSeconds: 300,
      }).length === 0,
    );
    check(
      "recordSession ignores malformed entries",
      recordSession(base, { phase: "work" }).length === 0,
    );
    check(
      "recordSession tolerates a missing log",
      recordSession(null, {
        endedAt: new Date(NOW).toISOString(),
        phase: "work",
        durationSeconds: 60,
      }).length === 1,
    );

    let capped = [];
    for (let i = 0; i < 600; i += 1) {
      capped = recordSession(capped, {
        endedAt: new Date(NOW + i).toISOString(),
        phase: "work",
        durationSeconds: 60,
      });
    }
    check("recordSession caps the log at MAX_ENTRIES", capped.length === 500);

    const mixed = [
      { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500 },
      { endedAt: new Date(NOW - 3 * DAY).toISOString(), phase: "work", durationSeconds: 1500 },
      { endedAt: new Date(NOW - 10 * DAY).toISOString(), phase: "work", durationSeconds: 1500 },
    ];
    const pruned = pruneHistory(mixed, { now: NOW, retentionDays: 7 });
    check("pruneHistory keeps recent entries", pruned.length === 2);
    check(
      "pruneHistory drops stale entries",
      !pruned.some(
        (entry) => entry.endedAt === new Date(NOW - 10 * DAY).toISOString(),
      ),
    );
    check("pruneHistory does not mutate its input", mixed.length === 3);

    const many = [];
    for (let i = 0; i < 600; i += 1) {
      many.push({
        endedAt: new Date(NOW).toISOString(),
        phase: "work",
        durationSeconds: 60,
      });
    }
    check(
      "pruneHistory enforces the entry cap",
      pruneHistory(many, { now: NOW, retentionDays: 90 }).length === 500,
    );

    const empty = summarise([], { now: NOW, days: 7 });
    check("summarise reports zero sessions on an empty log", empty.totalSessions === 0);
    check("summarise reports zero minutes on an empty log", empty.totalMinutes === 0);
    check("summarise flags an empty log", empty.empty === true);
    check("summarise returns every day in the window", empty.perDay.length === 7);

    const single = summarise(
      [{ endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500 }],
      { now: NOW, days: 7 },
    );
    check("summarise counts a single session", single.totalSessions === 1);
    check("summarise converts seconds to minutes", single.totalMinutes === 25);
    check("summarise keeps the full window", single.perDay.length === 7);
    check(
      "summarise buckets a single day",
      single.perDay.filter((day) => day.count === 1).length === 1,
    );

    const englishWeekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const dateKeyPattern = /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/;
    check(
      "summarise perDay exposes a YYYY-MM-DD date key",
      single.perDay.every((day) => dateKeyPattern.test(day.date)),
    );
    check(
      "summarise perDay no longer emits an English weekday name",
      single.perDay.every((day) => !englishWeekdays.includes(day.label)),
    );
    check(
      "summarise perDay label mirrors the calendar date key",
      single.perDay.every((day) => day.label === day.date),
    );
    check(
      "summarise perDay keeps the count shape",
      single.perDay.every(
        (day) => typeof day.count === "number" && typeof day.minutes === "number",
      ),
    );

    const multi = summarise(
      [
        { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500 },
        { endedAt: new Date(NOW - DAY).toISOString(), phase: "work", durationSeconds: 1500 },
        { endedAt: new Date(NOW - 2 * DAY).toISOString(), phase: "work", durationSeconds: 1200 },
      ],
      { now: NOW, days: 7 },
    );
    check("summarise counts multi-day sessions", multi.totalSessions === 3);
    check("summarise sums focused minutes", multi.totalMinutes === 70);
    check(
      "summarise spreads sessions across days",
      multi.perDay.filter((day) => day.count > 0).length === 3,
    );

    const outside = summarise(
      [
        { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500 },
        { endedAt: new Date(NOW - 10 * DAY).toISOString(), phase: "work", durationSeconds: 1500 },
      ],
      { now: NOW, days: 7 },
    );
    check("summarise ignores entries outside the window", outside.totalSessions === 1);

    check("HISTORY_VERSION is 2", HISTORY_VERSION === 2);
    check("MAX_LABEL_LENGTH is 40", MAX_LABEL_LENGTH === 40);
    check(
      "UNLABELLED names the fallback bucket",
      typeof UNLABELLED === "string" && UNLABELLED.length > 0,
    );

    const trimmed = recordSession([], {
      endedAt: new Date(NOW).toISOString(),
      phase: "work",
      durationSeconds: 1500,
      label: "  Thesis chapter 3  ",
    });
    check("recordSession trims a label", trimmed[0].label === "Thesis chapter 3");

    const truncated = recordSession([], {
      endedAt: new Date(NOW).toISOString(),
      phase: "work",
      durationSeconds: 1500,
      label: "x".repeat(120),
    });
    check(
      "recordSession truncates a label to MAX_LABEL_LENGTH",
      truncated[0].label.length === MAX_LABEL_LENGTH,
    );

    const blank = recordSession([], {
      endedAt: new Date(NOW).toISOString(),
      phase: "work",
      durationSeconds: 1500,
      label: "   ",
    });
    check("recordSession drops a whitespace-only label", !("label" in blank[0]));

    const v1Entry = {
      endedAt: new Date(NOW).toISOString(),
      phase: "work",
      durationSeconds: 1500,
    };
    const v1Summary = summarise([v1Entry], { now: NOW, days: 7 });
    check("v1 entries still summarise", v1Summary.totalSessions === 1);
    check("v1 entries keep their minutes", v1Summary.totalMinutes === 25);

    const tagged = [
      { endedAt: new Date(NOW - 2 * DAY).toISOString(), phase: "work", durationSeconds: 600, label: "Admin" },
      { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: new Date(NOW - 1 * DAY).toISOString(), phase: "work", durationSeconds: 900, label: "Thesis" },
      { endedAt: new Date(NOW - 3 * DAY).toISOString(), phase: "work", durationSeconds: 300 },
      { endedAt: new Date(NOW - 40 * DAY).toISOString(), phase: "work", durationSeconds: 300, label: "Old" },
    ];
    const tags = labelSummary(tagged, { now: NOW, days: 7 });
    check(
      "labelSummary lists each present label once, sorted",
      JSON.stringify(tags.labels) === JSON.stringify(["Admin", "Thesis"]),
    );
    check("labelSummary totals Thesis sessions", tags.totals.Thesis.sessions === 2);
    check("labelSummary totals Thesis minutes", tags.totals.Thesis.minutes === 40);
    check("labelSummary totals Admin minutes", tags.totals.Admin.minutes === 10);
    check(
      "labelSummary buckets unlabelled sessions",
      tags.totals[UNLABELLED].sessions === 1 &&
        tags.totals[UNLABELLED].minutes === 5,
    );
    check("labelSummary ignores labels outside the range", tags.totals.Old === undefined);

    const filtered = labelSummary(tagged, {
      now: NOW,
      days: 7,
      labels: ["Thesis"],
    });
    check(
      "labelSummary allow-list keeps the chosen label",
      filtered.totals.Thesis.sessions === 2,
    );
    check(
      "labelSummary allow-list drops other labels",
      filtered.totals.Admin === undefined,
    );

    const recent = recentSessions(tagged, { limit: 2 });
    check("recentSessions honours the limit", recent.length === 2);
    check(
      "recentSessions is newest first",
      recent[0].endedAt === new Date(NOW).toISOString(),
    );
    check("recentSessions reports the label", recent[0].label === "Thesis");
    check("recentSessions reports durationSeconds", recent[0].durationSeconds === 1500);

    const defaultRecent = recentSessions(tagged.concat(tagged), {});
    check("recentSessions defaults to five entries", defaultRecent.length === 5);

    const unlabelledRecent = recentSessions([v1Entry], { limit: 5 });
    check(
      "recentSessions omits an empty label",
      unlabelledRecent.length === 1 && unlabelledRecent[0].label === undefined,
    );

    check(
      "GOAL_STORAGE_SHAPE_VERSION is a positive integer",
      Number.isInteger(GOAL_STORAGE_SHAPE_VERSION) && GOAL_STORAGE_SHAPE_VERSION > 0,
    );
    check("MIN_GOAL_MINUTES is zero", MIN_GOAL_MINUTES === 0);
    check("MAX_GOAL_MINUTES is a full week", MAX_GOAL_MINUTES === 7 * 24 * 60);
    check("DEFAULT_WEEK_START is Monday", DEFAULT_WEEK_START === 1);

    check("normalizeGoal defaults null to zero minutes", normalizeGoal(null).minutes === 0);
    check("normalizeGoal tolerates undefined", normalizeGoal(undefined).minutes === 0);
    check(
      "normalizeGoal tolerates a malformed value",
      normalizeGoal("nonsense").minutes === 0,
    );
    check("normalizeGoal keeps a valid goal", normalizeGoal({ minutes: 300 }).minutes === 300);
    check("normalizeGoal accepts a bare number", normalizeGoal(120).minutes === 120);
    check(
      "normalizeGoal clamps above a week",
      normalizeGoal({ minutes: 99999 }).minutes === MAX_GOAL_MINUTES,
    );
    check(
      "normalizeGoal clamps below zero",
      normalizeGoal({ minutes: -50 }).minutes === 0,
    );
    check(
      "normalizeGoal trims and keeps a label",
      normalizeGoal({ minutes: 60, label: "  Thesis  " }).label === "Thesis",
    );
    check(
      "normalizeGoal drops an empty label",
      !("label" in normalizeGoal({ minutes: 60, label: "   " })),
    );
    check(
      "normalizeGoal truncates a long label",
      normalizeGoal({ minutes: 60, label: "x".repeat(120) }).label.length ===
        MAX_LABEL_LENGTH,
    );
    const goalInput = { minutes: 60, label: "Thesis" };
    normalizeGoal(goalInput);
    check(
      "normalizeGoal does not mutate its input",
      goalInput.minutes === 60 && goalInput.label === "Thesis",
    );

    const wk = weekWindow({ now: NOW, weekStartsOn: 1 });
    check("weekWindow spans seven days", wk.end - wk.start === 7 * DAY);
    check("weekWindow start is not after now", wk.start <= NOW);
    check("weekWindow end is after now", wk.end > NOW);
    check(
      "weekWindow starts at local midnight",
      new Date(wk.start).getHours() === 0 &&
        new Date(wk.start).getMinutes() === 0 &&
        new Date(wk.start).getSeconds() === 0 &&
        new Date(wk.start).getMilliseconds() === 0,
    );
    check("weekWindow defaults to Monday", weekWindow({ now: NOW }).start === wk.start);
    const wkSunday = weekWindow({ now: NOW, weekStartsOn: 0 });
    check(
      "weekWindow honours a Sunday start",
      wkSunday.end - wkSunday.start === 7 * DAY && wkSunday.start <= NOW,
    );

    const at = (offsetMs) => new Date(wk.start + offsetMs).toISOString();
    const weekHistory = [
      { endedAt: at(1 * 60 * 60 * 1000), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: at(2 * 60 * 60 * 1000), phase: "work", durationSeconds: 600, label: "Admin" },
      { endedAt: at(3 * 60 * 60 * 1000), phase: "work", durationSeconds: 900 },
      { endedAt: at(-1000), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: new Date(wk.end).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
    ];
    const frozenWeek = JSON.stringify(weekHistory);

    const goalWeek = goalProgress(weekHistory, { now: NOW, minutes: 60 });
    check("goalProgress reports the target", goalWeek.targetMinutes === 60);
    check("goalProgress sums focused minutes", goalWeek.focusedMinutes === 50);
    check("goalProgress reports remaining minutes", goalWeek.remainingMinutes === 10);
    check("goalProgress reports a clamped percentage", goalWeek.percent === 83);
    check("goalProgress is not reached under target", goalWeek.reached === false);
    check("goalProgress returns the week start", goalWeek.weekStart === wk.start);

    const over = goalProgress(weekHistory, { now: NOW, minutes: 30 });
    check("goalProgress flags an over-target week", over.reached === true);
    check("goalProgress clamps percent at 100", over.percent === 100);
    check("goalProgress reports no remaining when over", over.remainingMinutes === 0);

    const none = goalProgress(weekHistory, { now: NOW, minutes: 0 });
    check("goalProgress treats a zero target as not reached", none.reached === false);
    check("goalProgress defines percent as 100 with no target", none.percent === 100);
    check(
      "goalProgress handles a missing target",
      goalProgress(weekHistory, { now: NOW }).targetMinutes === 0,
    );

    const scoped = goalProgress(weekHistory, { now: NOW, minutes: 20, label: "Thesis" });
    check("goalProgress scopes to a label", scoped.focusedMinutes === 25);
    check("goalProgress reaches a label-scoped goal", scoped.reached === true);

    const unlabelled = goalProgress(weekHistory, { now: NOW, minutes: 10, label: UNLABELLED });
    check("goalProgress can scope to unlabelled entries", unlabelled.focusedMinutes === 15);

    const malformed = goalProgress(
      [
        null,
        42,
        { phase: "work" },
        { phase: "shortBreak", endedAt: new Date(NOW).toISOString(), durationSeconds: 300 },
      ],
      { now: NOW, minutes: 5 },
    );
    check("goalProgress ignores malformed entries", malformed.focusedMinutes === 0);
    check(
      "goalProgress tolerates a missing log",
      goalProgress(null, { now: NOW, minutes: 5 }).focusedMinutes === 0,
    );

    check(
      "goalProgress excludes entries before the week",
      goalProgress(
        [{ endedAt: new Date(wk.start - 1).toISOString(), phase: "work", durationSeconds: 600 }],
        { now: NOW, minutes: 5 },
      ).focusedMinutes === 0,
    );
    check(
      "goalProgress includes the inclusive week start",
      goalProgress(
        [{ endedAt: new Date(wk.start).toISOString(), phase: "work", durationSeconds: 600 }],
        { now: NOW, minutes: 5 },
      ).focusedMinutes === 10,
    );
    check(
      "goalProgress excludes the exclusive week end",
      goalProgress(
        [{ endedAt: new Date(wk.end).toISOString(), phase: "work", durationSeconds: 600 }],
        { now: NOW, minutes: 5 },
      ).focusedMinutes === 0,
    );

    check("goalProgress does not mutate its input", JSON.stringify(weekHistory) === frozenWeek);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


class HistoryStaticTests(unittest.TestCase):
    def test_history_module_exists(self):
        self.assertTrue(os.path.isfile(HISTORY_PATH), "missing app/history.js")

    def test_history_exports_expected_symbols(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(source, r"export\s+const\s+HISTORY_VERSION\b")
        self.assertRegex(source, r"export\s+const\s+MAX_LABEL_LENGTH\b")
        self.assertRegex(source, r"export\s+const\s+GOAL_STORAGE_SHAPE_VERSION\b")
        self.assertRegex(source, r"export\s+const\s+MAX_GOAL_MINUTES\b")
        self.assertRegex(source, r"export\s+const\s+MIN_GOAL_MINUTES\b")
        for function in (
            "recordSession",
            "pruneHistory",
            "summarise",
            "labelSummary",
            "recentSessions",
            "normalizeGoal",
            "weekWindow",
            "goalProgress",
        ):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "history.js does not export %s" % function,
            )

    def test_history_has_no_dom_references(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"document|window", source),
            "history.js must stay DOM-free",
        )

    def test_history_has_no_network_calls(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)


@unittest.skipUnless(NODE_BIN, "node is not installed")
class HistoryLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-history-")
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
            "history logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
