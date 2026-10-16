"""Tests for the Focus Flow ``labelShare`` helper.

Three layers of coverage, mirroring ``test_focus_heatmap.py``:

1. Static checks that ``app/history.js`` exports ``labelShare``, that
   ``app/index.html`` carries the focus-share donut markup, and that
   ``app/main.js`` renders the chart and reads the new catalog keys.
2. A check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``labelShare`` helper is
   exercised against both synthetic ``weeklyReview`` shapes and real history
   logs so the empty / ranking / tie-break / rounding / zero-total / malformed
   behaviour and the integration with ``weeklyReview`` (label filter, aliases,
   and the ``(unlabelled)`` bucket) are verified for real.
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
    "stats.shareHeading",
    "stats.shareChartLabel",
    "stats.shareSummary",
    "stats.shareLabelsOne",
    "stats.shareLabelsMany",
    "stats.shareSlice",
    "stats.shareEmpty",
    "announce.share",
)

HARNESS = textwrap.dedent(
    """
    import { labelShare, weeklyReview } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function entry(timestamp, minutes, label) {
      const row = {
        endedAt: new Date(timestamp).toISOString(),
        phase: "work",
        durationSeconds: minutes * 60,
      };
      if (label !== undefined) row.label = label;
      return row;
    }

    // --- empty / malformed input -------------------------------------------
    const empty = labelShare({ perLabel: [] });
    check("an empty perLabel yields no slices", empty.slices.length === 0);
    check("an empty perLabel sums to zero", empty.total === 0);
    check("an empty perLabel is empty", empty.empty === true);

    const malformed = [null, undefined, {}, 42, "nope", [], { perLabel: null }];
    for (const value of malformed) {
      let result;
      let threw = false;
      try {
        result = labelShare(value);
      } catch (error) {
        threw = true;
      }
      check("labelShare(" + String(value) + ") does not throw", !threw);
      check(
        "labelShare(" + String(value) + ") degrades to empty",
        !threw &&
          result.total === 0 &&
          result.slices.length === 0 &&
          result.empty === true,
      );
    }

    const nonObjectRows = labelShare({
      perLabel: [null, 3, "x", false, { label: "A", minutes: 10 }],
    });
    check("non-object rows are ignored", nonObjectRows.slices.length === 1);
    check("the surviving row is kept", nonObjectRows.slices[0].label === "A");
    check("the surviving minutes are kept", nonObjectRows.slices[0].minutes === 10);

    // --- ranking: minutes descending then label ascending -------------------
    const ranking = labelShare({
      perLabel: [
        { label: "Beta", minutes: 10 },
        { label: "Alpha", minutes: 30 },
        { label: "Gamma", minutes: 10 },
      ],
    });
    check("total sums every slice", ranking.total === 50);
    check(
      "the largest label is first",
      ranking.slices[0].label === "Alpha" && ranking.slices[0].minutes === 30,
    );
    check(
      "ties break by label ascending",
      ranking.slices[1].label === "Beta" && ranking.slices[2].label === "Gamma",
    );
    check("percent is the rounded share", ranking.slices[0].percent === 60);
    check(
      "percent adds up to 100 here",
      ranking.slices.reduce((sum, slice) => sum + slice.percent, 0) === 100,
    );
    check("a ranked review is not empty", ranking.empty === false);

    // --- rounding -----------------------------------------------------------
    const thirds = labelShare({
      perLabel: [
        { label: "A", minutes: 1 },
        { label: "B", minutes: 1 },
        { label: "C", minutes: 1 },
      ],
    });
    check(
      "each third rounds to 33",
      thirds.slices.every((slice) => slice.percent === 33),
    );

    // --- zero total ---------------------------------------------------------
    const zero = labelShare({
      perLabel: [
        { label: "A", minutes: 0 },
        { label: "B", minutes: 0 },
      ],
    });
    check(
      "zero total gives zero percent",
      zero.slices.every((slice) => slice.percent === 0),
    );
    check("rows with zero minutes are still slices", zero.empty === false);
    check("zero total stays zero", zero.total === 0);

    // --- negative / non-finite minutes -------------------------------------
    const badMinutes = labelShare({
      perLabel: [
        { label: "A", minutes: -5 },
        { label: "B", minutes: Infinity },
        { label: "C", minutes: 10 },
      ],
    });
    check(
      "negative minutes clamp to zero",
      badMinutes.slices.find((slice) => slice.label === "A").minutes === 0,
    );
    check(
      "non-finite minutes become zero",
      badMinutes.slices.find((slice) => slice.label === "B").minutes === 0,
    );
    check("total ignores malformed minutes", badMinutes.total === 10);

    // --- purity -------------------------------------------------------------
    const input = { perLabel: [{ label: "A", minutes: 10 }] };
    const snapshot = JSON.stringify(input);
    const out = labelShare(input);
    check("the input is not mutated", JSON.stringify(input) === snapshot);
    check(
      "slices expose exactly label/minutes/percent",
      out.slices.every(
        (slice) =>
          Object.keys(slice).sort().join(",") === "label,minutes,percent",
      ),
    );

    // --- integration with weeklyReview -------------------------------------
    const now = new Date(2026, 5, 17, 12, 0, 0).getTime(); // Wed 17 June 2026
    const review = weeklyReview(
      [
        entry(now - HOUR, 30, "Thesis"),
        entry(now - 2 * HOUR, 10, "Admin"),
        entry(now - 3 * HOUR, 20, "Thesis"),
      ],
      { now, weekStartsOn: 1 },
    );
    const share = labelShare(review);
    check("total matches the review's focusedMinutes", share.total === review.focusedMinutes);
    check("one slice per perLabel row", share.slices.length === review.perLabel.length);
    check(
      "ranking keeps the busiest label first",
      share.slices[0].label === "Thesis" && share.slices[0].minutes === 50,
    );
    check("percent matches the week", share.slices[0].percent === 83);
    check("a real week is not empty", share.empty === false);

    const filtered = weeklyReview(
      [entry(now - HOUR, 40, "Thesis"), entry(now - HOUR, 10, "Admin")],
      { now, weekStartsOn: 1, label: "Thesis" },
    );
    const filteredShare = labelShare(filtered);
    check("the label filter carries through", filteredShare.slices.length === 1);
    check(
      "the filtered label survives",
      filteredShare.slices[0].label === "Thesis",
    );

    const aliased = weeklyReview([entry(now - HOUR, 25, "Thesis")], {
      now,
      weekStartsOn: 1,
      tags: { Thesis: "PhD" },
    });
    const aliasedShare = labelShare(aliased);
    check("aliases carry through", aliasedShare.slices[0].label === "PhD");

    const unlabelled = weeklyReview([entry(now - HOUR, 15)], {
      now,
      weekStartsOn: 1,
    });
    const unlabelledShare = labelShare(unlabelled);
    check("unlabelled sessions form a slice", unlabelledShare.slices.length === 1);
    check(
      "the unlabelled slice uses the shared sentinel",
      unlabelledShare.slices[0].label === "(unlabelled)",
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class LabelShareStaticTests(unittest.TestCase):
    def test_history_exports_label_share(self):
        source = read(HISTORY_PATH)
        self.assertRegex(
            source,
            r"export\s+function\s+labelShare\b",
            "history.js does not export labelShare",
        )

    def test_history_stays_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_index_html_has_donut(self):
        html = read(INDEX_PATH)
        self.assertIn('id="stats-share"', html)
        self.assertIn('id="stats-share-chart"', html)
        self.assertIn('id="stats-share-summary"', html)
        self.assertIn('id="stats-share-empty"', html)
        self.assertIn('role="img"', html)
        self.assertIn('data-i18n-attr="aria-label:stats.shareChartLabel"', html)
        self.assertIn('data-i18n="stats.shareEmpty"', html)
        self.assertIn('data-i18n="stats.shareHeading"', html)

    def test_main_js_renders_the_share(self):
        js = read(MAIN_PATH)
        self.assertIn("labelShare", js)
        self.assertIn("renderShare", js)
        self.assertIn("renderShareChart", js)
        self.assertIn("stats-share-chart", js)
        self.assertIn("announce.share", js)
        self.assertIn("lastAnnouncedShareSignature", js)

    def test_styles_define_the_donut(self):
        css = read(STYLES_PATH)
        self.assertIn(".stats__share-chart", css)
        self.assertIn(".stats__share-slice", css)
        self.assertIn(".stats__share-empty", css)


class LabelShareI18nTests(unittest.TestCase):
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
class LabelShareLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-label-share-")
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
            "labelShare logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
