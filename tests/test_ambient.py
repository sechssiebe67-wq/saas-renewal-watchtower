"""Tests for the Focus Flow ambient-sound module.

Two layers of coverage:

1. Static checks that ``app/ambient.js`` exists, exports the documented
   symbols, and stays free of DOM/network references.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   noise generation and helpers are verified for real. If ``node`` is missing
   the logic tests are skipped, mirroring the optional-runtime pattern used in
   ``test_history.py``.
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
AMBIENT_PATH = os.path.join(APP_DIR, "ambient.js")
NODE_BIN = shutil.which("node")

HARNESS = textwrap.dedent(
    """
    import {
      AMBIENT_TYPES,
      AMBIENT_LABELS,
      DEFAULT_AMBIENT,
      normalizeAmbient,
      createNoiseBuffer,
      shouldPlay,
    } from "./ambient.mjs";

    const failures = [];
    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function same(a, b) {
      return JSON.stringify(a) === JSON.stringify(b);
    }

    const DEFAULT = { type: "off", volume: 0.3 };

    check("AMBIENT_TYPES is an array", Array.isArray(AMBIENT_TYPES));
    check("AMBIENT_TYPES is frozen", Object.isFrozen(AMBIENT_TYPES));
    check(
      "AMBIENT_TYPES has the four ids",
      same(AMBIENT_TYPES, ["off", "brown", "pink", "rain"]),
    );
    check("DEFAULT_AMBIENT matches", same(DEFAULT_AMBIENT, DEFAULT));
    check("DEFAULT_AMBIENT is frozen", Object.isFrozen(DEFAULT_AMBIENT));
    for (const id of AMBIENT_TYPES) {
      check("AMBIENT_LABELS has " + id, typeof AMBIENT_LABELS[id] === "string");
    }

    for (const value of [null, undefined, "garbage", {}, 42, [], true]) {
      let result;
      let threw = false;
      try {
        result = normalizeAmbient(value);
      } catch (error) {
        threw = true;
      }
      check(
        "normalizeAmbient(" + JSON.stringify(value) + ") does not throw",
        !threw,
      );
      check(
        "normalizeAmbient(" + JSON.stringify(value) + ") defaults to off",
        !threw && same(result, DEFAULT),
      );
    }

    check(
      "normalizeAmbient keeps a valid type",
      same(normalizeAmbient({ type: "brown" }), { type: "brown", volume: 0.3 }),
    );
    check(
      "normalizeAmbient accepts a bare type string",
      same(normalizeAmbient("rain"), { type: "rain", volume: 0.3 }),
    );
    check(
      "normalizeAmbient maps unknown types to off",
      normalizeAmbient({ type: "thunder", volume: 0.5 }).type === "off",
    );
    check(
      "normalizeAmbient clamps volume above 1",
      normalizeAmbient({ type: "pink", volume: 5 }).volume === 1,
    );
    check(
      "normalizeAmbient clamps volume below 0",
      normalizeAmbient({ type: "pink", volume: -3 }).volume === 0,
    );
    check(
      "normalizeAmbient parses a numeric string volume",
      normalizeAmbient({ type: "pink", volume: "0.5" }).volume === 0.5,
    );
    check(
      "normalizeAmbient defaults a garbage volume",
      normalizeAmbient({ type: "pink", volume: "loud" }).volume === 0.3,
    );

    check("createNoiseBuffer off returns null", createNoiseBuffer(null, "off") === null);
    check(
      "createNoiseBuffer unknown type returns null",
      createNoiseBuffer(null, "thunder") === null,
    );

    for (const type of ["brown", "pink", "rain"]) {
      const a = createNoiseBuffer(null, type, { seconds: 0.25, sampleRate: 8000 });
      const b = createNoiseBuffer(null, type, { seconds: 0.25, sampleRate: 8000 });
      check(type + " returns a Float32Array", a instanceof Float32Array);
      check(type + " has the expected length", a.length === 2000);
      check(type + " is deterministic", same(Array.from(a), Array.from(b)));
      let finite = true;
      for (let i = 0; i < a.length; i += 1) {
        if (!Number.isFinite(a[i])) {
          finite = false;
          break;
        }
      }
      check(type + " samples are finite", finite);
    }

    const fakeBuffer = { copied: null, copiedChannel: null };
    const fakeContext = {
      sampleRate: 8000,
      createBuffer(channels, length, rate) {
        fakeBuffer.channels = channels;
        fakeBuffer.length = length;
        fakeBuffer.rate = rate;
        return {
          copyToChannel(data, channel) {
            fakeBuffer.copied = Array.from(data);
            fakeBuffer.copiedChannel = channel;
          },
        };
      },
    };
    const viaContext = createNoiseBuffer(fakeContext, "pink", { seconds: 0.1 });
    check("createNoiseBuffer returns the context buffer", viaContext !== null);
    check("createNoiseBuffer uses one channel", fakeBuffer.channels === 1);
    check("createNoiseBuffer copies to channel 0", fakeBuffer.copiedChannel === 0);
    check(
      "createNoiseBuffer copies the generated samples",
      Array.isArray(fakeBuffer.copied) && fakeBuffer.copied.length === fakeBuffer.length,
    );

    check("shouldPlay off is silent", shouldPlay({ phase: "work", type: "off" }) === false);
    check(
      "shouldPlay plays during work",
      shouldPlay({ phase: "work", type: "brown" }) === true,
    );
    check(
      "shouldPlay is silent on a break by default",
      shouldPlay({ phase: "shortBreak", type: "brown" }) === false,
    );
    check(
      "shouldPlay continues through a break when breaks auto-start",
      shouldPlay({ phase: "shortBreak", type: "brown", autoStartBreaks: true }) === true,
    );
    check(
      "shouldPlay continues through a long break when auto-start is on",
      shouldPlay({ phase: "longBreak", type: "rain", autoStartBreaks: true }) === true,
    );
    check(
      "shouldPlay tolerates a missing argument",
      shouldPlay() === false,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


class AmbientStaticTests(unittest.TestCase):
    def test_ambient_module_exists(self):
        self.assertTrue(os.path.isfile(AMBIENT_PATH), "missing app/ambient.js")

    def test_ambient_exports_expected_symbols(self):
        with open(AMBIENT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertRegex(source, r"export\s+const\s+AMBIENT_TYPES\b")
        self.assertRegex(source, r"export\s+const\s+DEFAULT_AMBIENT\b")
        for function in ("normalizeAmbient", "createNoiseBuffer", "shouldPlay"):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "ambient.js does not export %s" % function,
            )

    def test_ambient_types_cover_documented_ids(self):
        with open(AMBIENT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for ambient_id in ("off", "brown", "pink", "rain"):
            self.assertIn('"%s"' % ambient_id, source)

    def test_ambient_has_no_dom_references(self):
        with open(AMBIENT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
            "ambient.js must stay DOM-free",
        )

    def test_ambient_has_no_network_calls(self):
        with open(AMBIENT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)


@unittest.skipUnless(NODE_BIN, "node is not installed")
class AmbientLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-ambient-")
        with open(AMBIENT_PATH, encoding="utf-8") as handle:
            source = handle.read()
        module_path = os.path.join(cls.tmp_dir, "ambient.mjs")
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
            "ambient logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
