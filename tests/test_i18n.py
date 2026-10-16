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
      LOCALE_DATA,
      normalizeLocale,
      translate,
      createTranslator,
      formatNumber,
      formatWeekday,
      formatMonth,
      formatDuration,
      pluralise,
      pluralCategory,
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

    check("LOCALE_DATA is an object", LOCALE_DATA && typeof LOCALE_DATA === "object");
    check("LOCALE_DATA is frozen", Object.isFrozen(LOCALE_DATA));
    for (const id of SUPPORTED_LOCALES) {
      const data = LOCALE_DATA[id];
      check("LOCALE_DATA has " + id, data && typeof data === "object");
      check("LOCALE_DATA." + id + " is frozen", Object.isFrozen(data));
      check(
        "LOCALE_DATA." + id + " has 7 short weekdays",
        Array.isArray(data.weekdaysShort) && data.weekdaysShort.length === 7,
      );
      check(
        "LOCALE_DATA." + id + " has 7 long weekdays",
        Array.isArray(data.weekdaysLong) && data.weekdaysLong.length === 7,
      );
      check(
        "LOCALE_DATA." + id + " has 12 short months",
        Array.isArray(data.monthsShort) && data.monthsShort.length === 12,
      );
      check(
        "LOCALE_DATA." + id + " has 12 long months",
        Array.isArray(data.monthsLong) && data.monthsLong.length === 12,
      );
      check(
        "LOCALE_DATA." + id + " has separators",
        typeof data.decimalSeparator === "string" &&
          data.decimalSeparator.length > 0 &&
          typeof data.groupSeparator === "string" &&
          data.groupSeparator.length > 0,
      );
      check(
        "LOCALE_DATA." + id + " has a plural selector",
        typeof data.plural === "function",
      );
    }

    check("formatNumber groups en thousands", formatNumber(1234567, "en") === "1,234,567");
    check("formatNumber groups de thousands", formatNumber(1234567, "de") === "1.234.567");
    check("formatNumber uses the es decimal comma", formatNumber(1234.5, "es") === "1.234,5");
    check("formatNumber keeps the sign", formatNumber(-1234, "de") === "-1.234");
    check("formatNumber falls back to en", formatNumber(1234, "fr") === "1,234");
    check("formatNumber tolerates malformed input", formatNumber("abc", "en") === "0");
    check("formatNumber tolerates NaN", formatNumber(NaN, "en") === "0");

    check("formatWeekday localises en", formatWeekday("2026-06-15", "en") === "Mon");
    check("formatWeekday localises de", formatWeekday("2026-06-15", "de") === "Mo");
    check(
      "formatWeekday localises a long de name",
      formatWeekday("2026-06-15", "de", { long: true }) === "Montag",
    );
    check("formatWeekday localises es", formatWeekday("2026-06-15", "es") === "lun");
    check(
      "formatWeekday indexes by getDay (Sunday)",
      formatWeekday("2026-06-14", "en") === "Sun",
    );
    check(
      "formatWeekday falls back to en for unknown locales",
      formatWeekday("2026-06-15", "fr") === "Mon",
    );
    check(
      "formatWeekday tolerates a Date",
      formatWeekday(new Date(2026, 5, 15), "en") === "Mon",
    );
    check("formatWeekday returns empty for malformed input", formatWeekday("nope", "en") === "");

    check("formatMonth localises en", formatMonth("2026-01-15", "en") === "Jan");
    check("formatMonth localises de", formatMonth("2026-12-15", "de") === "Dez");
    check(
      "formatMonth localises a long es name",
      formatMonth("2026-03-15", "es", { long: true }) === "marzo",
    );
    check(
      "formatMonth falls back to en for unknown locales",
      formatMonth("2026-01-15", "fr") === "Jan",
    );
    check("formatMonth returns empty for malformed input", formatMonth(null, "en") === "");

    check("formatDuration formats en", formatDuration(25, "en") === "25 min");
    check("formatDuration formats de", formatDuration(25, "de") === "25 Min.");
    check("formatDuration groups es thousands", formatDuration(1234, "es") === "1.234 min");
    check("formatDuration localises the singular", formatDuration(1, "de") === "1 Min.");
    check("formatDuration falls back for unknown locales", formatDuration(5, "fr") === "5 min");
    check("formatDuration tolerates malformed input", formatDuration(null, "en") === "0 min");

    check("pluralCategory selects one for 1", pluralCategory(1, "en") === "one");
    check("pluralCategory selects other for 0", pluralCategory(0, "en") === "other");
    check("pluralCategory selects other for 2", pluralCategory(2, "de") === "other");
    check(
      "pluralCategory falls back to en for unknown locales",
      pluralCategory(1, "fr") === "one",
    );
    check(
      "pluralise selects the one form",
      pluralise(1, { one: "a", other: "b" }, "en") === "a",
    );
    check(
      "pluralise selects the other form",
      pluralise(3, { one: "a", other: "b" }, "en") === "b",
    );
    check(
      "pluralise falls back to other for a missing category",
      pluralise(1, { other: "b" }, "en") === "b",
    );
    check("pluralise tolerates malformed forms", pluralise(2, null, "en") === "");

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
            "LOCALE_DATA",
            "LOCALE_STORAGE_SHAPE_VERSION",
        ):
            self.assertRegex(
                source,
                r"export\s+const\s+%s\b" % constant,
                "i18n.js does not export %s" % constant,
            )
        for function in (
            "normalizeLocale",
            "translate",
            "createTranslator",
            "formatNumber",
            "formatWeekday",
            "formatMonth",
            "formatDuration",
            "pluralise",
        ):
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
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bglobalThis\b", source),
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

    def test_goal_breakdown_keys_present_in_every_locale(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        keys = (
            "stats.goalBreakdown",
            "stats.goalBreakdownLabel",
            "stats.goalBreakdownOne",
            "stats.goalBreakdownMany",
            "stats.goalLabelStats",
            "announce.goalBreakdown",
            "announce.goalBreakdownScoped",
        )
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
            self.assertIsNotNone(match, "could not find %s" % name)
            block = match.group(1)
            for key in keys:
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )

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
