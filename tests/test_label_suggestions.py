"""Tests for the Focus Flow session-label autocomplete.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports the pure ``recentLabels``
   helper, that ``app/main.js`` wires it to the session-label field, and that
   ``app/i18n.js`` carries the new user-facing strings in **every** locale.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   logic (de-duplication, ordering, cap, malformed input, empty history) is
   verified for real. If ``node`` is missing the logic tests are skipped,
   mirroring the optional-runtime pattern used elsewhere.
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
MAIN_PATH = os.path.join(APP_DIR, "main.js")
I18N_PATH = os.path.join(APP_DIR, "i18n.js")
INDEX_PATH = os.path.join(APP_DIR, "index.html")
NODE_BIN = shutil.which("node")

HARNESS = textwrap.dedent(
    """
    import { recentLabels } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T12:00:00Z");
    const failures = [];
    function check(name, condition) {
      if (!condition) failures.push(name);
    }
    const at = (offset) => new Date(NOW - offset).toISOString();

    check("recentLabels tolerates an empty log", recentLabels([]).length === 0);
    check("recentLabels tolerates a missing log", recentLabels(null).length === 0);
    check(
      "recentLabels tolerates a non-array log",
      recentLabels("nope").length === 0,
    );

    const single = recentLabels(
      [{ endedAt: at(0), phase: "work", durationSeconds: 1500, label: "Thesis" }],
      { now: NOW },
    );
    check("recentLabels returns one label", single.length === 1);
    check("recentLabels returns the label text", single[0] === "Thesis");

    const ordered = recentLabels(
      [
        { endedAt: at(3 * HOUR), phase: "work", label: "Older" },
        { endedAt: at(1 * HOUR), phase: "work", label: "Newest" },
        { endedAt: at(2 * HOUR), phase: "work", label: "Middle" },
      ],
      { now: NOW },
    );
    check(
      "recentLabels orders newest first",
      JSON.stringify(ordered) === JSON.stringify(["Newest", "Middle", "Older"]),
    );

    const deduped = recentLabels(
      [
        { endedAt: at(3 * HOUR), phase: "work", label: "thesis chapter 3" },
        { endedAt: at(1 * HOUR), phase: "work", label: "Thesis chapter 3" },
        { endedAt: at(2 * HOUR), phase: "work", label: "Admin" },
      ],
      { now: NOW },
    );
    check("recentLabels de-duplicates case-insensitively", deduped.length === 2);
    check(
      "recentLabels keeps the newest casing",
      deduped[0] === "Thesis chapter 3",
    );
    check(
      "recentLabels keeps the newest label first",
      deduped[1] === "Admin",
    );

    const trimmed = recentLabels(
      [{ endedAt: at(0), phase: "work", label: "  Padded  " }],
      { now: NOW },
    );
    check("recentLabels trims labels", trimmed[0] === "Padded");

    const blank = recentLabels(
      [
        { endedAt: at(0), phase: "work", label: "   " },
        { endedAt: at(0), phase: "work" },
      ],
      { now: NOW },
    );
    check("recentLabels drops empty labels", blank.length === 0);

    const many = [];
    for (let i = 0; i < 20; i += 1) {
      many.push({ endedAt: at(i * HOUR), phase: "work", label: "Label " + i });
    }
    check(
      "recentLabels caps at the default limit",
      recentLabels(many, { now: NOW }).length === 8,
    );
    check(
      "recentLabels caps at a requested limit",
      recentLabels(many, { now: NOW, limit: 3 }).length === 3,
    );
    check(
      "recentLabels caps at the newest labels",
      recentLabels(many, { now: NOW, limit: 2 })[0] === "Label 0",
    );
    check(
      "recentLabels coerces a string limit",
      recentLabels(many, { now: NOW, limit: "4" }).length === 4,
    );
    check(
      "recentLabels treats a zero limit as empty",
      recentLabels(many, { now: NOW, limit: 0 }).length === 0,
    );
    check(
      "recentLabels treats a negative limit as empty",
      recentLabels(many, { now: NOW, limit: -3 }).length === 0,
    );
    check(
      "recentLabels treats a malformed limit as empty",
      recentLabels(many, { now: NOW, limit: "nope" }).length === 0,
    );

    const malformed = recentLabels(
      [
        null,
        42,
        "string",
        {},
        { phase: "work" },
        { phase: "work", label: "No end" },
        { phase: "shortBreak", endedAt: at(0), label: "Break" },
        { endedAt: "not-a-date", phase: "work", label: "Bad date" },
      ],
      { now: NOW },
    );
    check("recentLabels ignores malformed entries", malformed.length === 0);

    const future = recentLabels(
      [
        { endedAt: at(-1 * HOUR), phase: "work", label: "Future" },
        { endedAt: at(1 * HOUR), phase: "work", label: "Past" },
      ],
      { now: NOW },
    );
    check(
      "recentLabels ignores future-dated entries",
      JSON.stringify(future) === JSON.stringify(["Past"]),
    );

    const frozen = [
      { endedAt: at(0), phase: "work", label: "Keep" },
      { endedAt: at(HOUR), phase: "work", label: "Other" },
    ];
    const snapshot = JSON.stringify(frozen);
    recentLabels(frozen, { now: NOW });
    check("recentLabels does not mutate its input", JSON.stringify(frozen) === snapshot);

    process.stdout.write(JSON.stringify({ failures }));
    """
)


class LabelSuggestionStaticTests(unittest.TestCase):
    def test_history_exports_recent_labels(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(
            source,
            r"export\s+function\s+recentLabels\b",
            "history.js does not export recentLabels",
        )

    def test_main_js_wires_up_autocomplete(self):
        with open(MAIN_PATH, encoding="utf-8") as handle:
            js = handle.read()
        for symbol in (
            "recentLabels",
            "session-label-suggestions",
            "renderLabelSuggestions",
            "acceptLabelSuggestion",
            "handleLabelSuggestionKeydown",
            "announce.labelSuggestion",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)
        for key in ('"ArrowDown"', '"ArrowUp"', '"Enter"', '"Tab"', '"Escape"'):
            self.assertIn(key, js, "main.js does not handle %s" % key)

    def test_index_html_has_suggestion_listbox(self):
        with open(INDEX_PATH, encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn('id="session-label-suggestions"', html)
        self.assertIn('role="listbox"', html)
        self.assertIn('data-i18n-attr="aria-label:label.suggestionsLabel"', html)
        self.assertRegex(
            html,
            r'<ul\s+id="session-label-suggestions"[\s\S]*?hidden',
            "the suggestion list must start hidden",
        )

    def test_new_i18n_keys_exist_in_every_locale(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
            self.assertIsNotNone(match, "could not find %s" % name)
            block = match.group(1)
            for key in ("label.suggestionsLabel", "announce.labelSuggestion"):
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class LabelSuggestionLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-labels-")
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
            "label suggestion logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
