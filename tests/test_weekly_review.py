"""Tests for the Focus Flow ``weeklyReview`` helper.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports ``weeklyReview`` and stays
   free of DOM/network references.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   logic is verified for real. If ``node`` is missing the logic tests are
   skipped, mirroring the pattern used by ``test_history.py``.
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
NODE_BIN = shutil.which("node")

HARNESS = textwrap.dedent(
    """
    import {
      UNLABELLED,
      weekWindow,
      weeklyReview,
    } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    const wk = weekWindow({ now: NOW, weekStartsOn: 1 });
    const at = (offsetMs) => new Date(wk.start + offsetMs).toISOString();

    const history = [
      { endedAt: at(1 * HOUR), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: at(2 * HOUR), phase: "work", durationSeconds: 600, label: "Admin" },
      { endedAt: at(3 * HOUR), phase: "work", durationSeconds: 900 },
      { endedAt: at(4 * HOUR), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: new Date(wk.start - 1000).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: new Date(wk.end).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
    ];
    const frozen = JSON.stringify(history);

    const empty = weeklyReview([], { now: NOW, minutes: 60 });
    check("empty log has no per-label rows", empty.perLabel.length === 0);
    check("empty log has no labels", empty.labels.length === 0);
    check("empty log reports zero focused minutes", empty.focusedMinutes === 0);
    check("empty log keeps the target", empty.targetMinutes === 60);
    check("empty log reports zero percent", empty.percent === 0);
    check("empty log is not reached", empty.reached === false);
    check("empty log reports the remaining minutes", empty.remainingMinutes === 60);
    check("empty log returns the week start", empty.weekStart === wk.start);
    check("empty week review is not scoped", empty.scoped === false);

    const none = weeklyReview(history, { now: NOW, minutes: 0 });
    check("no goal defines percent as 100", none.percent === 100);
    check("no goal is not reached", none.reached === false);
    check("no goal keeps the target at zero", none.targetMinutes === 0);
    check(
      "no goal reports zero share of target",
      none.perLabel.every((row) => row.percentOfTarget === 0),
    );
    check("unscoped review is not scoped", none.scoped === false);

    const under = weeklyReview(history, { now: NOW, minutes: 100 });
    check("under-target sums focused minutes", under.focusedMinutes === 75);
    check("under-target reports the percentage", under.percent === 75);
    check("under-target reports remaining minutes", under.remainingMinutes === 25);
    check("under-target is not reached", under.reached === false);

    const reached = weeklyReview(history, { now: NOW, minutes: 50 });
    check("goal reached is flagged", reached.reached === true);
    check("goal reached clamps percent at 100", reached.percent === 100);
    check("goal reached reports no remaining minutes", reached.remainingMinutes === 0);

    check(
      "per-label rows are sorted by minutes then label",
      JSON.stringify(under.labels) ===
        JSON.stringify(["Thesis", UNLABELLED, "Admin"]),
    );
    const thesis = under.perLabel[0];
    check("per-label row keeps the label", thesis.label === "Thesis");
    check("per-label row counts sessions", thesis.sessions === 2);
    check("per-label row sums minutes", thesis.minutes === 50);
    check("per-label row reports share of target", thesis.percentOfTarget === 50);

    const unlabelledRow = under.perLabel[1];
    check("unlabelled row uses the fallback label", unlabelledRow.label === UNLABELLED);
    check("unlabelled row counts sessions", unlabelledRow.sessions === 1);
    check("unlabelled row sums minutes", unlabelledRow.minutes === 15);

    const ties = weeklyReview(
      [
        { endedAt: at(1), phase: "work", durationSeconds: 600, label: "Zeta" },
        { endedAt: at(2), phase: "work", durationSeconds: 600, label: "Alpha" },
      ],
      { now: NOW, minutes: 0 },
    );
    check(
      "ties are broken by label ascending",
      JSON.stringify(ties.labels) === JSON.stringify(["Alpha", "Zeta"]),
    );

    const scoped = weeklyReview(history, { now: NOW, minutes: 20, label: "Thesis" });
    check("label scoping sums only that label", scoped.focusedMinutes === 50);
    check("label scoping reaches the scoped goal", scoped.reached === true);
    check(
      "label scoping keeps only the matching row",
      scoped.perLabel.length === 1 && scoped.perLabel[0].label === "Thesis",
    );
    check(
      "label scoping lists only the matching label",
      JSON.stringify(scoped.labels) === JSON.stringify(["Thesis"]),
    );
    check("label scoping marks the review as scoped", scoped.scoped === true);

    const unlabelled = weeklyReview(history, {
      now: NOW,
      minutes: 10,
      label: UNLABELLED,
    });
    check("label scoping can target unlabelled entries", unlabelled.focusedMinutes === 15);
    check(
      "label scoping to unlabelled keeps that row",
      JSON.stringify(unlabelled.labels) === JSON.stringify([UNLABELLED]),
    );

    const malformed = weeklyReview(
      [
        null,
        42,
        { phase: "work" },
        { phase: "shortBreak", endedAt: at(1), durationSeconds: 300 },
      ],
      { now: NOW, minutes: 5 },
    );
    check("malformed entries are ignored", malformed.focusedMinutes === 0);
    check("malformed entries produce no rows", malformed.perLabel.length === 0);
    check("malformed entries still compute percent", malformed.percent === 0);

    check(
      "weeklyReview tolerates a missing log",
      weeklyReview(null, { now: NOW, minutes: 5 }).focusedMinutes === 0,
    );
    check(
      "weeklyReview never mutates its input",
      JSON.stringify(history) === frozen,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


class WeeklyReviewStaticTests(unittest.TestCase):
    def test_history_exports_weekly_review(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(
            source,
            r"export\s+function\s+weeklyReview\b",
            "history.js does not export weeklyReview",
        )

    def test_weekly_review_stays_pure(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)


@unittest.skipUnless(NODE_BIN, "node is not installed")
class WeeklyReviewLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-weekly-review-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        module_path = os.path.join(cls.tmp_dir, "history.mjs")
        with open(module_path, "w", encoding="utf-8") as handle:
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
            "weeklyReview logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
