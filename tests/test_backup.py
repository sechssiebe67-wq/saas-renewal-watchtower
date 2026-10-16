"""Tests for the Focus Flow local backup / restore helpers.

Two layers of coverage:

1. Static checks that ``app/history.js`` exports the pure backup helpers and
   stays free of DOM, storage, and network access, that ``app/index.html``
   carries the Settings **Backup & restore** controls, that ``app/main.js``
   wires them to ``localStorage`` through the pure helpers and a ``FileReader``,
   and that every new message key exists in all three locales.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file (with its sibling pure modules) and exercised through
   a harness so the envelope shape, the round-trip, the forward-compatibility
   guard, pruning, clamping, determinism, and non-mutation are verified for
   real.
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
    "settings.backup",
    "settings.backupHint",
    "settings.exportBackup",
    "settings.exportBackupHint",
    "settings.restoreBackup",
    "settings.restoreBackupHint",
    "settings.restoreBackupFile",
    "settings.backupInvalid",
    "announce.backupExported",
    "announce.backupRestored",
    "announce.backupFailed",
)

HARNESS = textwrap.dedent(
    """
    import {
      BACKUP_FORMAT_VERSION,
      BACKUP_KEYS,
      MAX_GOAL_MINUTES,
      exportBackup,
      backupToJson,
      parseBackup,
      backupFileName,
    } from "./history.mjs";

    const HOUR = 60 * 60 * 1000;
    const DAY = 24 * HOUR;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    check(
      "BACKUP_FORMAT_VERSION is a positive integer",
      Number.isInteger(BACKUP_FORMAT_VERSION) && BACKUP_FORMAT_VERSION > 0,
    );
    check("BACKUP_FORMAT_VERSION starts at 1", BACKUP_FORMAT_VERSION === 1);
    check(
      "BACKUP_KEYS is a frozen array",
      Array.isArray(BACKUP_KEYS) && Object.isFrozen(BACKUP_KEYS),
    );
    for (const key of [
      "settings",
      "history",
      "goal",
      "dailyGoal",
      "ambient",
      "locale",
      "weekStart",
    ]) {
      check("BACKUP_KEYS includes " + key, BACKUP_KEYS.includes(key));
    }

    const state = {
      settings: {
        work: 30,
        shortBreak: 7,
        longBreak: 20,
        longBreakInterval: 3,
        sound: true,
        autoStartBreaks: false,
      },
      history: [
        {
          endedAt: new Date(NOW - 1 * HOUR).toISOString(),
          phase: "work",
          durationSeconds: 1800,
          label: "Thesis",
        },
        {
          endedAt: new Date(NOW - 2 * HOUR).toISOString(),
          phase: "work",
          durationSeconds: 600,
        },
        {
          endedAt: new Date(NOW - 3 * HOUR).toISOString(),
          phase: "work",
          durationSeconds: 900,
          label: "Admin",
        },
      ],
      goal: { minutes: 300, label: "Thesis" },
      dailyGoal: { minutes: 50 },
      ambient: { type: "rain", volume: 0.4 },
      locale: "de",
      weekStart: 0,
    };
    const frozen = JSON.stringify(state);

    const envelope = exportBackup(state, { now: NOW });
    check("envelope has the format version", envelope.version === BACKUP_FORMAT_VERSION);
    check(
      "envelope has an ISO exportedAt",
      envelope.exportedAt === new Date(NOW).toISOString(),
    );
    check(
      "envelope data carries every key",
      BACKUP_KEYS.every((key) => Object.prototype.hasOwnProperty.call(envelope.data, key)),
    );
    check("exportBackup does not mutate its input", JSON.stringify(state) === frozen);

    const json = backupToJson(state, { now: NOW });
    check("backupToJson is indented", json.includes('  "data"'));

    const parsed = parseBackup(json, { now: NOW });
    check("round-trip parses", parsed !== null);
    check(
      "round-trip settings",
      JSON.stringify(parsed.settings) === JSON.stringify(state.settings),
    );
    check("round-trip history count", parsed.history.length === 3);
    check(
      "round-trip keeps labels",
      parsed.history.some((entry) => entry.label === "Thesis"),
    );
    check(
      "round-trip weekly goal",
      parsed.goal.minutes === 300 && parsed.goal.label === "Thesis",
    );
    check("round-trip daily goal", parsed.dailyGoal.minutes === 50);
    check(
      "round-trip ambient",
      parsed.ambient.type === "rain" && parsed.ambient.volume === 0.4,
    );
    check("round-trip locale", parsed.locale === "de");
    check("round-trip week start", parsed.weekStart === 0);

    check("invalid JSON returns null", parseBackup("{not json") === null);
    check("null literal returns null", parseBackup("null") === null);
    check("non-object JSON returns null", parseBackup("[1,2,3]") === null);
    check("empty string returns null", parseBackup("") === null);
    check("non-string input returns null", parseBackup(42) === null);
    check(
      "future version returns null",
      parseBackup(JSON.stringify({ version: 2, data: state })) === null,
    );
    check(
      "non-integer version returns null",
      parseBackup(JSON.stringify({ version: 1.5, data: state })) === null,
    );
    check(
      "string version returns null",
      parseBackup(JSON.stringify({ version: "1", data: state })) === null,
    );
    check(
      "zero version returns null",
      parseBackup(JSON.stringify({ version: 0, data: state })) === null,
    );
    check(
      "negative version returns null",
      parseBackup(JSON.stringify({ version: -1, data: state })) === null,
    );
    check(
      "envelope without data returns null",
      parseBackup(JSON.stringify({ version: 1, exportedAt: "x" })) === null,
    );

    const bare = parseBackup(
      JSON.stringify({ goal: { minutes: 120 }, history: [], locale: "es" }),
      { now: NOW },
    );
    check("bare data object is accepted", bare !== null);
    check("bare data normalises the goal", bare.goal.minutes === 120);
    check("bare data defaults the ambient", bare.ambient.type === "off");
    check("bare data keeps the locale", bare.locale === "es");
    check("bare data defaults the week start", bare.weekStart === 1);
    check("bare data leaves settings null", bare.settings === null);

    const oldEntry = {
      endedAt: new Date(NOW - 200 * DAY).toISOString(),
      phase: "work",
      durationSeconds: 1500,
    };
    const freshEntry = {
      endedAt: new Date(NOW - 1 * DAY).toISOString(),
      phase: "work",
      durationSeconds: 1500,
    };
    const pruned = parseBackup(
      JSON.stringify({
        version: 1,
        data: { history: [oldEntry, freshEntry], goal: { minutes: 999999 } },
      }),
      { now: NOW },
    );
    check(
      "history older than the retention window is pruned",
      pruned.history.length === 1 && pruned.history[0].endedAt === freshEntry.endedAt,
    );
    check(
      "a goal above the weekly maximum is clamped",
      pruned.goal.minutes === MAX_GOAL_MINUTES,
    );

    check(
      "backupToJson is deterministic",
      backupToJson(state, { now: NOW }) === backupToJson(state, { now: NOW }),
    );
    check("backupToJson does not mutate its input", JSON.stringify(state) === frozen);

    const name = backupFileName(NOW);
    const localDate = new Date(NOW);
    const expectedName =
      "focus-flow-backup-" +
      localDate.getFullYear() +
      "-" +
      String(localDate.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(localDate.getDate()).padStart(2, "0") +
      ".json";
    check("backupFileName uses the local date", name === expectedName);
    check(
      "backupFileName has the right shape",
      /^focus-flow-backup-\\d{4}-\\d{2}-\\d{2}\\.json$/.test(name),
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class BackupStaticTests(unittest.TestCase):
    def test_history_exports_backup_helpers(self):
        source = read(HISTORY_PATH)
        for constant in ("BACKUP_FORMAT_VERSION", "BACKUP_KEYS"):
            self.assertRegex(
                source,
                r"export\s+const\s+%s\b" % constant,
                "history.js does not export %s" % constant,
            )
        for function in (
            "exportBackup",
            "backupToJson",
            "parseBackup",
            "backupFileName",
        ):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "history.js does not export %s" % function,
            )

    def test_history_backup_helpers_stay_pure(self):
        source = read(HISTORY_PATH)
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("createObjectURL", source)
        self.assertNotIn("localStorage", source)

    def test_index_html_has_backup_controls(self):
        html = read(INDEX_PATH)
        expectations = {
            "backup sub-heading": 'data-i18n="settings.backup"',
            "export button": 'id="backup-export"',
            "restore button": 'id="backup-restore"',
            "restore file input": 'id="backup-restore-file"',
            "inline status": 'id="backup-status"',
        }
        for label, fragment in expectations.items():
            self.assertIn(fragment, html, "index.html missing %s" % label)
        self.assertIn('type="file"', html)
        self.assertIn('accept="application/json,.json"', html)

    def test_main_js_wires_the_backup(self):
        js = read(MAIN_PATH)
        for symbol in (
            "backupToJson",
            "parseBackup",
            "backupFileName",
            "exportBackupFile",
            "restoreBackupText",
            "applyRestoredBackup",
            "FileReader",
            "createObjectURL",
            "revokeObjectURL",
            '"application/json',
            "announce.backupRestored",
            "announce.backupFailed",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

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
class BackupLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-backup-")
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
            "backup logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
