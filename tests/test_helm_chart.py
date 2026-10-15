"""Tests for the Focus Flow Helm chart.

When the ``helm`` binary is available the chart is rendered with
``helm template`` and the resulting manifest is inspected. A lighter set of
static checks always runs so the suite still provides coverage on machines
without Helm.
"""

import os
import shutil
import subprocess
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHART_DIR = os.path.join(REPO_ROOT, "helm")
HELM_BIN = shutil.which("helm")


def read_chart_file(*parts):
    with open(os.path.join(CHART_DIR, *parts), encoding="utf-8") as handle:
        return handle.read()


class ChartStaticTests(unittest.TestCase):
    def test_chart_files_exist(self):
        for relative in (
            "Chart.yaml",
            "values.yaml",
            "templates/deployment.yaml",
            "templates/service.yaml",
            "templates/ingress.yaml",
        ):
            path = os.path.join(CHART_DIR, relative)
            self.assertTrue(os.path.isfile(path), "missing chart file: %s" % relative)

    def test_values_define_resources_and_probes(self):
        values = read_chart_file("values.yaml")
        for fragment in (
            "resources:",
            "requests:",
            "limits:",
            "cpu:",
            "memory:",
            "livenessProbe:",
            "readinessProbe:",
            "/healthz",
            "ingress:",
            "enabled: true",
        ):
            self.assertIn(fragment, values, "values.yaml missing: %s" % fragment)


@unittest.skipUnless(HELM_BIN, "helm binary is not installed")
class HelmRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [HELM_BIN, "template", "focus-flow", "helm"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError("helm template failed:\n%s" % result.stderr)
        cls.rendered = result.stdout

    def test_required_kinds_rendered(self):
        for kind in ("kind: Deployment", "kind: Service", "kind: Ingress"):
            self.assertIn(kind, self.rendered, "missing rendered %s" % kind)

    def test_deployment_has_health_probes(self):
        self.assertIn("livenessProbe:", self.rendered)
        self.assertIn("readinessProbe:", self.rendered)
        self.assertGreaterEqual(self.rendered.count("/healthz"), 2)

    def test_deployment_has_resource_limits(self):
        self.assertIn("resources:", self.rendered)
        self.assertIn("limits:", self.rendered)
        self.assertIn("requests:", self.rendered)
        self.assertIn("memory: 64Mi", self.rendered)
        self.assertIn("cpu: 100m", self.rendered)

    def test_container_port_matches_service(self):
        self.assertIn("containerPort: 8080", self.rendered)
        self.assertIn("targetPort: 8080", self.rendered)

    def test_runs_as_non_root(self):
        self.assertIn("runAsNonRoot: true", self.rendered)


if __name__ == "__main__":
    unittest.main()
