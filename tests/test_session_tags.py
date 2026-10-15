"""Tests for the Focus Flow device-only session tag aliases.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports ``normalizeSessionTags``,
   ``applyAliases``, ``SESSION_TAGS_STORAGE_SHAPE_VERSION``,
   ``SESSION_TAGS_MAX_ENTRIES`` and ``SESSION_TAGS_MAX_ALIAS_LENGTH``, that
   ``app/index.html`` wires up the Settings alias group, and that ``app/main.js``
   reads, normalises, persists, and renders the key.
2. A static check that every new message key is present in all three locales.
3. When a ``node`` binary is available, the pure ``history.js`` helpers are
   exercised so ``normalizeSessionTags``, ``applyAliases``, and the ``tags``
   threading through the derived views are verified for real.
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
    "settings.sessionTags",
    "settings.sessionTagsHint",
    "settings.sessionTagsFrom",
    "settings.sessionTagsTo",
    "settings.sessionTagsAdd",
    "settings.sessionTagsEntry",
    "settings.sessionTagsListLabel",
    "settings.sessionTagsRemove",
    "settings.sessionTagsRemoveLabel",
    "announce.sessionTagsAdded",
    "announce.sessionTagsRemoved",
    "announce.sessionTagsInvalid",
)

HARNESS = textwrap.dedent(
    """
    import {
      SESSION_TAGS_STORAGE_SHAPE_VERSION,
      SESSION_TAGS_MAX_ENTRIES,
      SESSION_TAGS_MAX_ALIAS_LENGTH,
      normalizeSessionTags,
      applyAliases,
      summarise,
      labelSummary,
      recentSessions,
      recentLabels,
      goalProgress,
      dailyGoalProgress,
      weeklyReview,
      streaks,
      parseBackup,
    } from "./history.mjs";

    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    check(
      "SESSION_TAGS_STORAGE_SHAPE_VERSION is a positive integer",
      Number.isInteger(SESSION_TAGS_STORAGE_SHAPE_VERSION) &&
        SESSION_TAGS_STORAGE_SHAPE_VERSION > 0,
    );
    check(
      "SESSION_TAGS_MAX_ENTRIES is a positive integer",
      Number.isInteger(SESSION_TAGS_MAX_ENTRIES) && SESSION_TAGS_MAX_ENTRIES > 0,
    );
    check(
      "SESSION_TAGS_MAX_ALIAS_LENGTH is a positive integer",
      Number.isInteger(SESSION_TAGS_MAX_ALIAS_LENGTH) &&
        SESSION_TAGS_MAX_ALIAS_LENGTH > 0,
    );

    // --- normalizeSessionTags -------------------------------------------------

    const fromObject = normalizeSessionTags({ Thesis: "PhD", Admin: "Ops" });
    check("normalizeSessionTags maps an object", fromObject.Thesis === "PhD" && fromObject.Admin === "Ops");
    check(
      "normalizeSessionTags returns a plain map",
      JSON.stringify(Object.keys(fromObject).sort()) === JSON.stringify(["Admin", "Thesis"]),
    );

    const fromArray = normalizeSessionTags([
      { from: "Thesis", to: "PhD" },
      { from: "Admin", to: "Ops" },
    ]);
    check(
      "normalizeSessionTags accepts { from, to } pairs",
      fromArray.Thesis === "PhD" && fromArray.Admin === "Ops",
    );

    for (const value of [null, undefined, 42, "nonsense", true, [], [1, 2]]) {
      const result = normalizeSessionTags(value);
      check(
        "normalizeSessionTags(" + JSON.stringify(value) + ") returns an empty map",
        result && typeof result === "object" && Object.keys(result).length === 0,
      );
    }

    const trimmed = normalizeSessionTags([{ from: "  Thesis  ", to: "  PhD  " }]);
    check("normalizeSessionTags trims the label", trimmed.Thesis === "PhD");

    const blank = normalizeSessionTags([
      { from: "   ", to: "PhD" },
      { from: "Thesis", to: "   " },
      { from: "Thesis", to: "Thesis" },
    ]);
    check("normalizeSessionTags drops blank and no-op aliases", Object.keys(blank).length === 0);

    const longAlias = normalizeSessionTags([
      { from: "Thesis", to: "y".repeat(200) },
    ]);
    check(
      "normalizeSessionTags caps the alias length",
      longAlias.Thesis.length === SESSION_TAGS_MAX_ALIAS_LENGTH,
    );

    const deduped = normalizeSessionTags({ Thesis: "A", thesis: "B" });
    check("normalizeSessionTags de-duplicates keys case-insensitively", Object.keys(deduped).length === 1);
    check("normalizeSessionTags keeps the newest alias", Object.values(deduped)[0] === "B");

    const cappedInput = {};
    for (let i = 0; i < SESSION_TAGS_MAX_ENTRIES + 20; i += 1) {
      cappedInput["Label " + i] = "Alias " + i;
    }
    check(
      "normalizeSessionTags caps the entry count",
      Object.keys(normalizeSessionTags(cappedInput)).length === SESSION_TAGS_MAX_ENTRIES,
    );

    const frozenInput = { Thesis: "PhD" };
    normalizeSessionTags(frozenInput);
    check("normalizeSessionTags does not mutate its input", frozenInput.Thesis === "PhD");

    // --- applyAliases ---------------------------------------------------------

    const tags = normalizeSessionTags({ Thesis: "PhD", Admin: "Ops" });
    check("applyAliases returns the alias", applyAliases("Thesis", tags) === "PhD");
    check("applyAliases is case-insensitive", applyAliases("thesis", tags) === "PhD");
    check("applyAliases returns the label when unmapped", applyAliases("Other", tags) === "Other");
    check("applyAliases returns the label without tags", applyAliases("Thesis", undefined) === "Thesis");
    check("applyAliases tolerates an empty map", applyAliases("Thesis", {}) === "Thesis");
    check("applyAliases tolerates a non-string label", applyAliases(42, tags) === 42);
    check("applyAliases tolerates a missing label", applyAliases(undefined, tags) === undefined);
    check("applyAliases accepts a swapped call order", applyAliases(tags, "Thesis") === "PhD");

    // --- tags threading -------------------------------------------------------

    const log = [
      { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
      { endedAt: new Date(NOW).toISOString(), phase: "work", durationSeconds: 600, label: "Admin" },
    ];
    const frozenLog = JSON.stringify(log);

    const aliased = labelSummary(log, { now: NOW, days: 7, tags });
    check("labelSummary groups by alias", aliased.totals.PhD.sessions === 1 && aliased.totals.Ops.sessions === 1);
    check("labelSummary drops the canonical keys", aliased.totals.Thesis === undefined);
    check(
      "labelSummary lists the aliased labels",
      JSON.stringify(aliased.labels) === JSON.stringify(["Ops", "PhD"]),
    );

    const plain = labelSummary(log, { now: NOW, days: 7 });
    check("labelSummary without tags keeps the stored labels", plain.totals.Thesis.sessions === 1);

    const merged = labelSummary(log, {
      now: NOW,
      days: 7,
      tags: normalizeSessionTags({ Thesis: "Same", Admin: "Same" }),
    });
    check("labelSummary merges labels that share an alias", merged.totals.Same.sessions === 2);

    const recent = recentSessions(log, { tags });
    check(
      "recentSessions aliases the label",
      recent.some((entry) => entry.label === "PhD") &&
        recent.every((entry) => entry.label !== "Thesis"),
    );

    const suggestions = recentLabels(log, { now: NOW, tags });
    check(
      "recentLabels aliases the suggestions",
      suggestions.includes("PhD") && suggestions.includes("Ops") && !suggestions.includes("Thesis"),
    );

    const scopedSummary = summarise(log, { now: NOW, days: 7, label: "PhD", tags });
    check("summarise matches an aliased filter", scopedSummary.totalSessions === 1);
    const plainSummary = summarise(log, { now: NOW, days: 7, label: "Thesis" });
    check("summarise without tags matches the stored label", plainSummary.totalSessions === 1);

    const review = weeklyReview(log, { now: NOW, tags });
    check(
      "weeklyReview groups by alias",
      review.labels.includes("PhD") && review.labels.includes("Ops") && !review.labels.includes("Thesis"),
    );

    const goal = goalProgress(log, { now: NOW, minutes: 10, label: "PhD", tags });
    check("goalProgress matches an aliased filter", goal.focusedMinutes === 25);

    const daily = dailyGoalProgress(log, { now: NOW, minutes: 10, label: "Ops", tags });
    check("dailyGoalProgress matches an aliased filter", daily.focusedMinutes === 10);

    const streak = streaks(log, { now: NOW, tags });
    check("streaks accepts tags and stays day-based", streak.current === 1);

    check("tags threading does not mutate the log", JSON.stringify(log) === frozenLog);

    const parsed = parseBackup(
      JSON.stringify({ version: 1, data: { sessionTags: { Thesis: "PhD" } } }),
      { now: NOW },
    );
    check("parseBackup normalises sessionTags", parsed !== null && parsed.sessionTags.Thesis === "PhD");
    const parsedMissing = parseBackup(
      JSON.stringify({ version: 1, data: {} }),
      { now: NOW },
    );
    check(
      "parseBackup defaults sessionTags to an empty map",
      parsedMissing !== null && Object.keys(parsedMissing.sessionTags).length === 0,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class SessionTagsStaticTests(unittest.TestCase):
    def test_history_exports_session_tag_helpers(self):
        source = read(HISTORY_PATH)
        for constant in (
            "SESSION_TAGS_STORAGE_SHAPE_VERSION",
            "SESSION_TAGS_MAX_ENTRIES",
            "SESSION_TAGS_MAX_ALIAS_LENGTH",
        ):
            self.assertRegex(
                source,
                r"export\s+const\s+%s\b" % constant,
                "history.js does not export %s" % constant,
            )
        for function in ("normalizeSessionTags", "applyAliases"):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "history.js does not export %s" % function,
            )

    def test_history_stays_dom_and_storage_free(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"document|window", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("localStorage", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_derived_views_accept_tags(self):
        source = read(HISTORY_PATH)
        for function in (
            "summarise",
            "labelSummary",
            "recentSessions",
            "recentLabels",
            "goalProgress",
            "dailyGoalProgress",
            "weeklyReview",
            "streaks",
        ):
            match = re.search(
                r"export\s+function\s+%s\b([\s\S]*?)\)\s*\{" % function,
                source,
            )
            self.assertIsNotNone(match, "history.js does not export %s" % function)
            self.assertIn(
                "tags",
                match.group(1),
                "%s does not accept a tags option" % function,
            )

    def test_index_html_has_session_tag_controls(self):
        html = read(INDEX_PATH)
        for fragment in (
            'id="session-tag-from"',
            'id="session-tag-to"',
            'id="session-tag-add"',
            'id="session-tags-list"',
            'data-i18n="settings.sessionTags"',
            'data-i18n="settings.sessionTagsFrom"',
            'data-i18n="settings.sessionTagsTo"',
            'data-i18n="settings.sessionTagsAdd"',
            'data-i18n-attr="aria-label:settings.sessionTagsListLabel"',
        ):
            self.assertIn(fragment, html, "index.html missing %s" % fragment)
        self.assertRegex(
            html,
            r'<ul\s+id="session-tags-list"[\s\S]*?hidden',
            "the alias list must start hidden",
        )

    def test_main_js_wires_up_session_tags(self):
        js = read(MAIN_PATH)
        self.assertIn('"focus-flow:session-tags"', js)
        for symbol in (
            "normalizeSessionTags",
            "applyAliases",
            "renderSessionTags",
            "addSessionTag",
            "removeSessionTag",
            "persistSessionTags",
            "announce.sessionTagsAdded",
            "announce.sessionTagsRemoved",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)


class SessionTagsI18nTests(unittest.TestCase):
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
class SessionTagsLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-session-tags-")
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
            "session-tags logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
