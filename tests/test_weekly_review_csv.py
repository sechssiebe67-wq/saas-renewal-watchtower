"""Tests for the Focus Flow ``weeklyReviewCsv`` helper.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports the pure ``weeklyReviewCsv``
   helper and keeps it free of DOM, storage, and network access, that
   ``app/index.html`` wires up a disabled-by-default **Export CSV** button, that
   ``app/main.js`` turns the helper's output into a download, and that the three
   new message keys exist in every locale.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a harness so the header, the
   per-label rows, the totals row, RFC 4180 escaping, the ``UNLABELLED`` label,
   and graceful handling of empty/malformed input are verified for real.
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
INDEX_PATH = os.path.join(APP_DIR, "index.html")
MAIN_PATH = os.path.join(APP_DIR, "main.js")
I18N_PATH = os.path.join(APP_DIR, "i18n.js")
NODE_BIN = shutil.which("node")

HEADER = "Label,Sessions,Minutes,Share of target (%)"
NEW_I18N_KEYS = ("review.export", "review.exportHint", "review.exported")

HARNESS = textwrap.dedent(
    """
    import {
      UNLABELLED,
      weekWindow,
      weeklyReview,
      weeklyReviewCsv,
    } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const HEADER = "Label,Sessions,Minutes,Share of target (%)";
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    const wk = weekWindow({ now: NOW, weekStartsOn: 1 });
    const at = (offsetMs) => new Date(wk.start + offsetMs).toISOString();

    const history = [
      { endedAt: at(1 * HOUR), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: at(2 * HOUR), phase: "work", durationSeconds: 600 },
      { endedAt: at(3 * HOUR), phase: "work", durationSeconds: 900, label: "Admin" },
    ];
    const frozen = JSON.stringify(history);
    const review = weeklyReview(history, { now: NOW, minutes: 100 });
    const csv = weeklyReviewCsv(review);
    const lines = csv.split("\\n");

    check("starts with the header row", lines[0] === HEADER);
    check("ends with a trailing newline", csv.endsWith("\\n"));
    check(
      "has a header, one row per label, a totals row, and a trailing blank",
      lines.length === review.perLabel.length + 3,
    );

    const rowFor = (label) =>
      lines
        .slice(1, -2)
        .find((line) => line.startsWith(label === UNLABELLED ? "(" : label));

    const thesisRow = rowFor("Thesis");
    check("Thesis row exists", typeof thesisRow === "string");
    check("Thesis row has the label", thesisRow === "Thesis,1,25,25");
    check(
      "unlabelled row uses the shared UNLABELLED label",
      lines.includes(UNLABELLED + ",1,10,10"),
    );
    check("totals row sums the sessions", lines[lines.length - 2] === "Total,3,50,50");

    const noGoal = weeklyReview(history, { now: NOW, minutes: 0 });
    const noGoalLines = weeklyReviewCsv(noGoal).split("\\n");
    check(
      "with no goal every label row has a zero share of target",
      noGoalLines
        .slice(1, -2)
        .every((line) => line.endsWith(",0")),
    );
    check(
      "with no goal the totals row keeps the defined 100 percent",
      noGoalLines[noGoalLines.length - 2] === "Total,3,50,100",
    );

    const tricky = {
      focusedMinutes: 15,
      percent: 15,
      perLabel: [
        { label: "A, B", sessions: 1, minutes: 5, percentOfTarget: 5 },
        { label: 'He said "hi"', sessions: 1, minutes: 5, percentOfTarget: 5 },
        { label: "Line\\nbreak", sessions: 1, minutes: 5, percentOfTarget: 5 },
      ],
    };
    const escaped = weeklyReviewCsv(tricky);
    check("quotes a field containing a comma", escaped.includes('"A, B",1,5,5'));
    const doubleQuoted = '"' + 'He said ""hi""' + '"';
    check(
      "doubles internal quotes",
      escaped.includes(doubleQuoted + ",1,5,5"),
    );
    check(
      "quotes a field containing a newline",
      escaped.includes('"Line\\nbreak",1,5,5'),
    );

    const override = weeklyReviewCsv(
      {
        focusedMinutes: 10,
        percent: 10,
        perLabel: [
          { label: UNLABELLED, sessions: 1, minutes: 10, percentOfTarget: 10 },
        ],
      },
      { unlabelled: "(ohne Bezeichnung)", locale: "de" },
    );
    check(
      "localised unlabelled label replaces the default",
      override.includes("(ohne Bezeichnung),1,10,10"),
    );

    const empty = weeklyReviewCsv(null);
    check(
      "null input yields a header and a zero totals row",
      empty === HEADER + "\\nTotal,0,0,0\\n",
    );
    check("undefined input does not throw", weeklyReviewCsv(undefined) === empty);
    check("an empty object does not throw", weeklyReviewCsv({}) === empty);
    check(
      "a non-array perLabel does not throw",
      weeklyReviewCsv({ perLabel: "nope" }) === empty,
    );

    const malformed = weeklyReviewCsv({
      focusedMinutes: "bad",
      percent: -5,
      perLabel: [
        null,
        42,
        { label: "Only label" },
        { label: "Bad counts", sessions: -3, minutes: NaN, percentOfTarget: "x" },
      ],
    });
    check(
      "malformed rows are coerced, not fatal",
      malformed.split("\\n")[1] === "Only label,0,0,0" &&
        malformed.split("\\n")[2] === "Bad counts,0,0,0" &&
        malformed.split("\\n")[3] === "Total,0,0,0",
    );

    check(
      "the input history is never mutated",
      JSON.stringify(history) === frozen,
    );
    check(
      "the review object is never mutated",
      review.perLabel[0].label === "Thesis" && review.focusedMinutes === 50,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class WeeklyReviewCsvStaticTests(unittest.TestCase):
    def test_history_exports_weekly_review_csv(self):
        source = read(HISTORY_PATH)
        self.assertRegex(source, r"export\s+function\s+weeklyReviewCsv\b")

    def test_history_stays_dom_and_network_free(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"document|window", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("createObjectURL", source)
        self.assertNotIn("localStorage", source)

    def test_index_html_has_disabled_export_button(self):
        html = read(INDEX_PATH)
        self.assertIn('id="review-export"', html)
        self.assertRegex(html, r"<button[^>]*id=\"review-export\"[^>]*disabled")
        self.assertIn('data-i18n="review.export"', html)
        self.assertIn('data-i18n="review.exportHint"', html)

    def test_main_js_wires_up_the_export(self):
        js = read(MAIN_PATH)
        self.assertIn("weeklyReviewCsv", js)
        self.assertIn("exportWeeklyReview", js)
        self.assertIn("createObjectURL", js)
        self.assertIn("revokeObjectURL", js)
        self.assertIn("focus-flow-week-", js)
        self.assertIn('"text/csv', js)

    def test_new_keys_present_in_every_locale(self):
        source = read(I18N_PATH)
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
            self.assertIsNotNone(match, "could not find %s" % name)
            block = match.group(1)
            for key in NEW_I18N_KEYS:
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class WeeklyReviewCsvLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-review-csv-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        with open(
            os.path.join(cls.tmp_dir, "history.mjs"), "w", encoding="utf-8"
        ) as handle:
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
            "weeklyReviewCsv logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
