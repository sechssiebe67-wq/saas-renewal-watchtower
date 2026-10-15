"""Progressive Web App tests for the Focus Flow web app.

Parses ``manifest.webmanifest`` as JSON, inspects ``service-worker.js``, and
confirms the referenced icon files exist and are valid PNGs. No browser or
JavaScript runtime is required.
"""

import json
import os
import re
import struct
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(REPO_ROOT, "app")
ICONS_DIR = os.path.join(APP_DIR, "icons")

MANIFEST_PATH = os.path.join(APP_DIR, "manifest.webmanifest")
SERVICE_WORKER_PATH = os.path.join(APP_DIR, "service-worker.js")


def read_text(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def png_dimensions(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("%s is not a PNG file" % path)
    width, height = struct.unpack(">II", header[16:24])
    return width, height


class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(MANIFEST_PATH, encoding="utf-8") as handle:
            cls.manifest = json.load(handle)

    def test_required_fields_present(self):
        for field in (
            "name",
            "short_name",
            "description",
            "start_url",
            "scope",
            "display",
            "background_color",
            "theme_color",
            "orientation",
            "icons",
        ):
            self.assertIn(field, self.manifest, "manifest missing %s" % field)

    def test_manifest_values(self):
        self.assertEqual(self.manifest["name"], "Focus Flow")
        self.assertEqual(self.manifest["start_url"], "./")
        self.assertEqual(self.manifest["scope"], "./")
        self.assertEqual(self.manifest["display"], "standalone")
        self.assertEqual(self.manifest["orientation"], "any")
        self.assertTrue(self.manifest["background_color"].startswith("#"))
        self.assertTrue(self.manifest["theme_color"].startswith("#"))

    def test_icons_cover_192_and_512_and_exist(self):
        sizes = set()
        for icon in self.manifest["icons"]:
            self.assertIn("src", icon)
            self.assertIn("sizes", icon)
            self.assertTrue(
                icon.get("type", "").startswith("image/"),
                "icon %s has no image type" % icon.get("src"),
            )
            path = os.path.join(APP_DIR, icon["src"])
            self.assertTrue(
                os.path.isfile(path), "manifest icon missing on disk: %s" % icon["src"]
            )
            sizes.update(icon["sizes"].split())
        self.assertIn("192x192", sizes)
        self.assertIn("512x512", sizes)

    def test_maskable_icon_present(self):
        purposes = {icon.get("purpose") for icon in self.manifest["icons"]}
        self.assertIn("maskable", purposes)

    def test_icons_are_valid_pngs_with_declared_size(self):
        for icon in self.manifest["icons"]:
            path = os.path.join(APP_DIR, icon["src"])
            width, height = png_dimensions(path)
            declared = icon["sizes"].split()[0]
            expected = tuple(int(part) for part in declared.split("x"))
            self.assertEqual(
                (width, height),
                expected,
                "icon %s is %dx%d but declares %s"
                % (icon["src"], width, height, declared),
            )


class ServiceWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_text(SERVICE_WORKER_PATH)

    def test_lifecycle_handlers_defined(self):
        for handler in ("install", "activate", "fetch"):
            self.assertIn(
                'addEventListener("%s"' % handler,
                self.source,
                "service worker missing %s handler" % handler,
            )

    def test_uses_versioned_cache_name(self):
        match = re.search(r'CACHE_NAME\s*=\s*"([^"]+)"', self.source)
        self.assertIsNotNone(match, "service worker has no CACHE_NAME")
        self.assertRegex(match.group(1), r"^focus-flow-v\d+$")

    def test_precache_covers_core_assets(self):
        for asset in (
            '"./"',
            '"./index.html"',
            '"./styles.css"',
            '"./main.js"',
            '"./timer.js"',
            '"./history.js"',
            '"./manifest.webmanifest"',
            '"./healthz"',
        ):
            self.assertIn(asset, self.source, "precache list missing %s" % asset)

    def test_history_module_is_precached(self):
        self.assertIn('"./history.js"', self.source)

    def test_cache_name_is_focus_flow_v2(self):
        match = re.search(r'CACHE_NAME\s*=\s*"([^"]+)"', self.source)
        self.assertIsNotNone(match, "service worker has no CACHE_NAME")
        self.assertEqual(match.group(1), "focus-flow-v2")

    def test_ignores_non_get_and_cross_origin(self):
        self.assertIn('request.method !== "GET"', self.source)
        self.assertIn("url.origin !== self.location.origin", self.source)

    def test_install_and_activate_take_control(self):
        self.assertIn("skipWaiting", self.source)
        self.assertIn("clients.claim", self.source)

    def test_navigation_falls_back_to_cached_index(self):
        self.assertIn('request.mode === "navigate"', self.source)
        self.assertIn('caches.match("./index.html")', self.source)


class IconSourceTests(unittest.TestCase):
    def test_svg_source_and_generator_committed(self):
        for name in ("icon.svg", "generate_icons.py"):
            path = os.path.join(ICONS_DIR, name)
            self.assertTrue(os.path.isfile(path), "missing icon source: %s" % name)


if __name__ == "__main__":
    unittest.main()
