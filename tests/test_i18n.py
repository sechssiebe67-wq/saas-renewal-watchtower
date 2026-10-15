"""Tests for the Focus Flow i18n message catalog.

Two layers of coverage:

1. Static checks that ``app/i18n.js`` exists, exports the documented symbols,
   stays free of DOM/network references, and that the shell wires up the
   ``data-i18n`` hooks and the locale switcher. These also assert that the new
   module is precached under a bumped service-worker cache.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the locale
   normalisation, catalog parity, and translation fallbacks are verified for
   real. If ``node`` is missing the logic tests are skipped, mirroring the
   optional-runtime pattern used in ``test_ambient.py``.
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
I18N_PATH = os.path.join(APP_DIR, "i18n.js")
INDEX_PATH = os.path.join(APP_DIR, "index.html")
MAIN_PATH = os.path.join(APP_DIR, "main.js")
SERVICE_WORKER_PATH = os.path.join(APP_DIR, "service-worker.js")
NODE_BIN = shutil.which("node")

HARNESS = textwrap.dedent(
    """
    import {
      SUPPORTED_LOCALES,
      LOCALE_LABELS,
      DEFAULT_LOCALE,
      MESSAGES,
      normalizeLocale,
      translate,
      createTranslator,
      LOCALE_STORAGE_SHAPE_VERSION,
    } from "./i18n.mjs";

    const failures = [];
    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    check("SUPPORTED_LOCALES is an array", Array.isArray(SUPPORTED_LOCALES));
    check("SUPPORTED_LOCALES is frozen", Object.isFrozen(SUPPORTED_LOCALES));
    check("SUPPORTED_LOCALES includes en", SUPPORTED_LOCALES.includes("en"));
    check("SUPPORTED_LOCALES ships at least two locales", SUPPORTED_LOCALES.length >= 2);
    for (const id of SUPPORTED_LOCALES) {
      check("LOCALE_LABELS has " + id, typeof LOCALE_LABELS[id] === "string");
    }
    check("DEFAULT_LOCALE is en", DEFAULT_LOCALE === "en");
    check(
      "LOCALE_STORAGE_SHAPE_VERSION is a number",
      typeof LOCALE_STORAGE_SHAPE_VERSION === "number",
    );

    for (const id of SUPPORTED_LOCALES) {
      check("MESSAGES has " + id, MESSAGES[id] && typeof MESSAGES[id] === "object");
    }

    const defaultKeys = Object.keys(MESSAGES[DEFAULT_LOCALE]);
    check("default catalog is non-empty", defaultKeys.length > 0);
    for (const id of SUPPORTED_LOCALES) {
      for (const key of defaultKeys) {
        check(
          "catalog parity " + id + " has " + key,
          typeof (MESSAGES[id] || {})[key] === "string",
        );
      }
    }

    for (const value of [null, undefined, 42, {}, [], true, "garbage", "xx-YY"]) {
      let result;
      let threw = false;
      try {
        result = normalizeLocale(value);
      } catch (error) {
        threw = true;
      }
      check(
        "normalizeLocale(" + JSON.stringify(value) + ") does not throw",
        !threw,
      );
      check(
        "normalizeLocale(" + JSON.stringify(value) + ") falls back to default",
        !threw && result === DEFAULT_LOCALE,
      );
    }
    check("normalizeLocale keeps a supported id", normalizeLocale("de") === "de");
    check("normalizeLocale is case-insensitive", normalizeLocale("DE") === "de");
    check(
      "normalizeLocale resolves a regional tag",
      normalizeLocale("es-MX") === "es",
    );
    check(
      "normalizeLocale unwraps { locale }",
      normalizeLocale({ locale: "es" }) === "es",
    );
    check(
      "normalizeLocale rejects an unknown object locale",
      normalizeLocale({ locale: "xx" }) === DEFAULT_LOCALE,
    );

    check(
      "translate returns the requested locale",
      translate("de", "controls.reset") === MESSAGES.de["controls.reset"],
    );
    check(
      "translate falls back to the key for unknown keys",
      translate("en", "totally.missing.key") === "totally.missing.key",
    );
    check(
      "translate falls back to the default for an unsupported locale",
      translate("fr", "controls.start") === MESSAGES.en["controls.start"],
    );
    check(
      "translate substitutes placeholders",
      translate("en", "recent.minutes", { count: 5 }) === "5 min",
    );
    check(
      "translate leaves missing placeholders in place",
      translate("en", "announce.ambientOn", {}) === "Ambient sound: {type}.",
    );
    check(
      "translate tolerates null params",
      translate("en", "controls.start", null) === MESSAGES.en["controls.start"],
    );
    check(
      "translate ignores unknown params",
      translate("en", "controls.skip", { nope: 1 }) === MESSAGES.en["controls.skip"],
    );
    check(
      "translate never returns undefined",
      typeof translate("de", "missing.everywhere") === "string",
    );

    const t = createTranslator("es");
    check("createTranslator returns a function", typeof t === "function");
    check(
      "createTranslator binds the locale",
      t("controls.start") === MESSAGES.es["controls.start"],
    );
    check(
      "createTranslator normalises an unknown locale",
      createTranslator("zz")("controls.start") === MESSAGES.en["controls.start"],
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


class I18nStaticTests(unittest.TestCase):
    def test_i18n_module_exists(self):
        self.assertTrue(os.path.isfile(I18N_PATH), "missing app/i18n.js")

    def test_i18n_exports_expected_symbols(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for constant in (
            "SUPPORTED_LOCALES",
            "LOCALE_LABELS",
            "DEFAULT_LOCALE",
            "MESSAGES",
            "LOCALE_STORAGE_SHAPE_VERSION",
        ):
            self.assertRegex(
                source,
                r"export\s+const\s+%s\b" % constant,
                "i18n.js does not export %s" % constant,
            )
        for function in ("normalizeLocale", "translate", "createTranslator"):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "i18n.js does not export %s" % function,
            )

    def test_i18n_documents_fallback_to_default(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("MESSAGES[DEFAULT_LOCALE]", source)

    def test_i18n_has_no_dom_references(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"document|window", source),
            "i18n.js must stay DOM-free",
        )

    def test_i18n_has_no_network_calls(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)
        self.assertNotIn("://", source)

    def test_i18n_has_no_imports(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"^\s*import\s", source, re.M),
            "i18n.js must not import third-party modules",
        )
        self.assertNotIn("require(", source)

    def test_index_html_has_i18n_hooks(self):
        with open(INDEX_PATH, encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn("data-i18n=", html)
        self.assertIn("data-i18n-attr=", html)
        self.assertIn('id="locale"', html)
        self.assertIn('for="locale"', html)

    def test_index_html_i18n_keys_exist_in_catalog(self):
        with open(INDEX_PATH, encoding="utf-8") as handle:
            html = handle.read()
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        catalog_keys = set(re.findall(r'"([A-Za-z][\w.]*)":', source))

        html_keys = set(re.findall(r'data-i18n="([^"]+)"', html))
        for spec in re.findall(r'data-i18n-attr="([^"]+)"', html):
            for pair in spec.split(";"):
                if ":" in pair:
                    html_keys.add(pair.split(":", 1)[1].strip())

        self.assertTrue(html_keys, "index.html has no i18n hooks")
        missing = sorted(key for key in html_keys if key not in catalog_keys)
        self.assertEqual(missing, [], "hooks without catalog entries: %s" % missing)

    def test_main_js_wires_up_i18n_and_locale_storage(self):
        with open(MAIN_PATH, encoding="utf-8") as handle:
            js = handle.read()
        self.assertIn("./i18n.js", js)
        self.assertIn('"focus-flow:locale"', js)
        for symbol in (
            "SUPPORTED_LOCALES",
            "LOCALE_LABELS",
            "DEFAULT_LOCALE",
            "normalizeLocale",
            "createTranslator",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)

    def test_service_worker_precaches_i18n_with_bumped_cache(self):
        with open(SERVICE_WORKER_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn('"./i18n.js"', source)
        match = re.search(r'CACHE_NAME\s*=\s*"focus-flow-v(\d+)"', source)
        self.assertIsNotNone(match, "service worker has no CACHE_NAME")
        self.assertGreater(
            int(match.group(1)),
            7,
            "bump CACHE_NAME when the precache list changes",
        )


@unittest.skipUnless(NODE_BIN, "node is not installed")
class I18nLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-i18n-")
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        module_path = os.path.join(cls.tmp_dir, "i18n.mjs")
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
            "i18n logic failures: %s" % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
