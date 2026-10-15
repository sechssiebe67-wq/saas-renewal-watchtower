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
      recordSession,
      pruneHistory,
      summarise,
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
        for function in ("recordSession", "pruneHistory", "summarise"):
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
