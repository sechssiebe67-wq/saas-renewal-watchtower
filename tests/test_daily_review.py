"""Tests for the Focus Flow ``dailyReview`` and ``badgeState`` helpers.

Three layers of coverage:

1. Static checks that ``app/history.js`` exports the daily-review and badge
   helpers and stays free of DOM/storage/network references, that every new
   ``app/i18n.js`` message key is present in all three locales, and that
   ``index.html`` / ``main.js`` carry the new daily breakdown and app-badge
   wiring.
2. When a ``node`` binary is available, the module source is copied to a
   temporary ``.mjs`` file and exercised through a small harness so the pure
   daily-review and badge maths is verified for real. If ``node`` is missing the
   logic tests are skipped, mirroring the pattern used by ``test_daily_goal.py``
   and ``test_weekly_review.py``. The harness runs with a ``TZ`` that observes
   daylight saving so the local-calendar day matching is genuinely exercised at
   the 23h spring-forward and 25h fall-back boundaries.
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

HARNESS = textwrap.dedent(
    """
    import {
      UNLABELLED,
      dailyReview,
      badgeState,
    } from "./history.mjs";

    const DAY = 24 * 60 * 60 * 1000;
    const HOUR = 60 * 60 * 1000;
    const NOW = Date.parse("2026-06-15T10:00:00Z");
    const failures = [];

    function check(name, condition) {
      if (!condition) failures.push(name);
    }

    function localStart(ts) {
      const d = new Date(ts);
      return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
    }

    const today = localStart(NOW);
    function work(dayOffset, seconds = 1500, label) {
      const entry = {
        endedAt: new Date(today + dayOffset * DAY + 9 * HOUR).toISOString(),
        phase: "work",
        durationSeconds: seconds,
      };
      if (label !== undefined) entry.label = label;
      return entry;
    }

    // Empty state shares `dailyGoalProgress`'s scalar shape and adds an empty
    // per-label list plus the scoped flag.
    const empty = dailyReview([], { now: NOW, goal: { minutes: 50 } });
    check("empty review has no per-label rows", empty.perLabel.length === 0);
    check("empty review has no labels", empty.labels.length === 0);
    check("empty review reports the target", empty.targetMinutes === 50);
    check("empty review reports zero focused minutes", empty.focusedMinutes === 0);
    check("empty review reports the remaining minutes", empty.remainingMinutes === 50);
    check("empty review reports zero percent", empty.percent === 0);
    check("empty review is not reached", empty.reached === false);
    check("empty review is not scoped", empty.scoped === false);
    check("empty review returns the local day start", empty.dayStart === today);

    const mixed = [
      work(0, 1500, "Thesis"),
      work(0, 600, "Admin"),
      work(0, 900),
      work(-1, 3000, "Thesis"),
    ];
    const frozen = JSON.stringify(mixed);

    const review = dailyReview(mixed, { now: NOW, goal: { minutes: 100 } });
    check("review sums today only", review.focusedMinutes === 50);
    check("review reports the percentage", review.percent === 50);
    check("review reports remaining minutes", review.remainingMinutes === 50);
    check("review is not reached", review.reached === false);
    check(
      "per-label rows are sorted by minutes then label",
      JSON.stringify(review.labels) ===
        JSON.stringify(["Thesis", UNLABELLED, "Admin"]),
    );
    const thesisRow = review.perLabel[0];
    check("per-label row keeps the label", thesisRow.label === "Thesis");
    check("per-label row counts sessions", thesisRow.sessions === 1);
    check("per-label row sums minutes", thesisRow.minutes === 25);
    check("per-label row reports share of target", thesisRow.percentOfTarget === 25);
    const unlabelledRow = review.perLabel[1];
    check("unlabelled row uses the fallback label", unlabelledRow.label === UNLABELLED);
    check("unlabelled row sums minutes", unlabelledRow.minutes === 15);
    check("dailyReview does not mutate its input", JSON.stringify(mixed) === frozen);

    const scoped = dailyReview(mixed, {
      now: NOW,
      goal: { minutes: 20, label: "Thesis" },
    });
    check("label scoping sums only that label", scoped.focusedMinutes === 25);
    check("label scoping reaches the scoped goal", scoped.reached === true);
    check("label scoping marks the review as scoped", scoped.scoped === true);
    check(
      "label scoping keeps only the matching row",
      scoped.perLabel.length === 1 && scoped.perLabel[0].label === "Thesis",
    );

    const aliased = dailyReview(mixed, {
      now: NOW,
      goal: { minutes: 100 },
      tags: { Thesis: "PhD", Admin: "PhD" },
    });
    check("aliases merge stored labels into one row", aliased.perLabel.length === 2);
    check("aliased row keeps the display label", aliased.perLabel[0].label === "PhD");
    check(
      "aliased row merges both stored labels",
      aliased.perLabel[0].sessions === 2 && aliased.perLabel[0].minutes === 35,
    );
    check(
      "unlabelled row survives alias merging",
      aliased.labels.includes(UNLABELLED),
    );

    const aliasScoped = dailyReview(mixed, {
      now: NOW,
      goal: { minutes: 50, label: "PhD" },
      tags: { Thesis: "PhD", Admin: "PhD" },
    });
    check("alias-scoped review matches the display label", aliasScoped.focusedMinutes === 35);
    check("alias-scoped review is scoped", aliasScoped.scoped === true);

    const unlabelled = dailyReview(mixed, {
      now: NOW,
      goal: { minutes: 5, label: UNLABELLED },
    });
    check("label scoping can target unlabelled entries", unlabelled.focusedMinutes === 15);
    check(
      "label scoping to unlabelled keeps that row",
      JSON.stringify(unlabelled.labels) === JSON.stringify([UNLABELLED]),
    );

    const none = dailyReview(mixed, { now: NOW, goal: { minutes: 0 } });
    check("no goal defines percent as 100", none.percent === 100);
    check("no goal is not reached", none.reached === false);
    check(
      "no goal reports zero share of target",
      none.perLabel.every((row) => row.percentOfTarget === 0),
    );

    const malformed = dailyReview(
      [
        null,
        42,
        { phase: "work" },
        { phase: "shortBreak", endedAt: new Date(today + HOUR).toISOString(), durationSeconds: 300 },
        { endedAt: "not-a-date", phase: "work", durationSeconds: 60 },
      ],
      { now: NOW, goal: { minutes: 5 } },
    );
    check("malformed entries are ignored", malformed.focusedMinutes === 0);
    check("malformed entries produce no rows", malformed.perLabel.length === 0);
    check(
      "dailyReview tolerates a missing log",
      dailyReview(null, { now: NOW, goal: { minutes: 5 } }).focusedMinutes === 0,
    );
    check(
      "dailyReview tolerates a missing goal",
      dailyReview(mixed, { now: NOW }).targetMinutes === 0,
    );

    const ties = dailyReview(
      [
        { endedAt: new Date(today + HOUR).toISOString(), phase: "work", durationSeconds: 600, label: "Zeta" },
        { endedAt: new Date(today + 2 * HOUR).toISOString(), phase: "work", durationSeconds: 600, label: "Alpha" },
      ],
      { now: NOW, goal: { minutes: 0 } },
    );
    check(
      "ties are broken by label ascending",
      JSON.stringify(ties.labels) === JSON.stringify(["Alpha", "Zeta"]),
    );

    // --- daylight-saving: 23h spring-forward day ---------------------------
    // US spring-forward is Sunday 8 March 2026 in America/New_York, so the
    // local day is only 23 hours long. A naive +24h window would drop an entry
    // logged in the final hour; both in-day entries must still bucket together
    // and the neighbouring days must stay out.
    const springNow = new Date(2026, 2, 8, 12, 0, 0).getTime();
    const springDayStart = new Date(2026, 2, 8).getTime();
    const spring = dailyReview(
      [
        { endedAt: new Date(2026, 2, 8, 1, 30).toISOString(), phase: "work", durationSeconds: 1500, label: "Thesis" },
        { endedAt: new Date(2026, 2, 8, 23, 30).toISOString(), phase: "work", durationSeconds: 900, label: "Thesis" },
        { endedAt: new Date(2026, 2, 7, 23, 30).toISOString(), phase: "work", durationSeconds: 600, label: "Thesis" },
        { endedAt: new Date(2026, 2, 9, 0, 30).toISOString(), phase: "work", durationSeconds: 600, label: "Thesis" },
      ],
      { now: springNow, goal: { minutes: 50 } },
    );
    check("spring-forward day start is local midnight", spring.dayStart === springDayStart);
    check("spring-forward day keeps both in-day entries", spring.focusedMinutes === 40);
    check(
      "spring-forward day does not leak neighbouring days",
      spring.perLabel.length === 1 && spring.perLabel[0].minutes === 40,
    );

    // --- daylight-saving: 25h fall-back day --------------------------------
    // US fall-back is Sunday 1 November 2026; the local day is 25 hours long.
    // An entry logged in the repeated final hour must not be dropped.
    const fallNow = new Date(2026, 10, 1, 12, 0, 0).getTime();
    const fallDayStart = new Date(2026, 10, 1).getTime();
    const fall = dailyReview(
      [
        { endedAt: new Date(2026, 10, 1, 1, 30).toISOString(), phase: "work", durationSeconds: 1500, label: "Admin" },
        { endedAt: new Date(2026, 10, 1, 23, 30).toISOString(), phase: "work", durationSeconds: 900, label: "Admin" },
        { endedAt: new Date(2026, 10, 2, 0, 30).toISOString(), phase: "work", durationSeconds: 600, label: "Admin" },
      ],
      { now: fallNow, goal: { minutes: 50 } },
    );
    check("fall-back day start is local midnight", fall.dayStart === fallDayStart);
    check("fall-back day keeps its final-hour entry", fall.focusedMinutes === 40);
    check(
      "fall-back day does not leak the next day",
      fall.perLabel.length === 1 && fall.perLabel[0].minutes === 40,
    );

    // badgeState: the on-device app-badge decision.
    check(
      "badgeState is null without a goal",
      badgeState({ goal: { minutes: 0 }, review: none }) === null,
    );
    check(
      "badgeState is null without a review",
      badgeState({ goal: { minutes: 50 } }) === null,
    );
    const badgeReview = dailyReview(mixed, { now: NOW, goal: { minutes: 100 } });
    check(
      "badgeState returns the clamped remaining minutes",
      badgeState({ goal: { minutes: 100 }, review: badgeReview }) === 50,
    );
    const reachedReview = dailyReview(mixed, { now: NOW, goal: { minutes: 50 } });
    check(
      "badgeState is null once the goal is reached",
      badgeState({ goal: { minutes: 50 }, review: reachedReview }) === null,
    );
    const overshotReview = dailyReview(mixed, { now: NOW, goal: { minutes: 10 } });
    check(
      "badgeState never returns a negative remainder",
      badgeState({ goal: { minutes: 10 }, review: overshotReview }) === null,
    );
    check(
      "badgeState clamps a huge target",
      badgeState({
        goal: { minutes: 99999 },
        review: dailyReview(mixed, { now: NOW, goal: { minutes: 99999 } }),
      }) === 1440 - 50,
    );
    check(
      "badgeState tolerates a malformed review",
      badgeState({ goal: { minutes: 50 }, review: "nope" }) === null,
    );

    process.stdout.write(JSON.stringify({ failures }));
    """
)


DAILY_REVIEW_I18N_KEYS = (
    "stats.dailyBreakdown",
    "stats.dailyBreakdownLabel",
    "stats.dailyLabelStats",
    "announce.dailyBreakdown",
    "announce.dailyBreakdownScoped",
    "announce.badge",
)


class DailyReviewStaticTests(unittest.TestCase):
    def test_history_exports_daily_review_helpers(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for function in ("dailyReview", "badgeState"):
            self.assertRegex(
                source,
                r"export\s+function\s+%s\b" % function,
                "history.js does not export %s" % function,
            )

    def test_daily_review_helpers_stay_pure(self):
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(
            re.search(r"\bdocument\b|\bwindow\b\s*[.\[]|\bnavigator\b|\bglobalThis\b", source),
            "history.js must stay DOM-free",
        )
        self.assertNotIn("localStorage", source)
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_daily_review_keys_present_in_every_locale(self):
        with open(I18N_PATH, encoding="utf-8") as handle:
            source = handle.read()
        for name in ("EN_MESSAGES", "DE_MESSAGES", "ES_MESSAGES"):
            match = re.search(r"const %s = \{(.*?)\n\};" % name, source, re.S)
            self.assertIsNotNone(match, "could not find %s" % name)
            block = match.group(1)
            for key in DAILY_REVIEW_I18N_KEYS:
                self.assertIn(
                    '"%s":' % key,
                    block,
                    "%s is missing message key %s" % (name, key),
                )

    def test_index_html_has_daily_breakdown(self):
        with open(INDEX_PATH, encoding="utf-8") as handle:
            html = handle.read()
        for fragment in (
            'id="stats-daily-breakdown-title"',
            'id="stats-daily-breakdown"',
            'data-i18n="stats.dailyBreakdown"',
        ):
            self.assertIn(fragment, html, "index.html missing %s" % fragment)
        self.assertIn(
            'data-i18n-attr="aria-label:stats.dailyBreakdownLabel"', html
        )
        self.assertRegex(
            html,
            r'<ul\s+id="stats-daily-breakdown"[\s\S]*?hidden',
            "the daily breakdown list must start hidden",
        )

    def test_main_js_wires_daily_review_and_badge(self):
        with open(MAIN_PATH, encoding="utf-8") as handle:
            js = handle.read()
        for symbol in (
            "dailyReview",
            "badgeState",
            "renderDailyBreakdown",
            "hideDailyBreakdown",
            "syncBadge",
            "setAppBadge",
            "clearAppBadge",
            "stats-daily-breakdown",
            "stats.dailyLabelStats",
            "announce.badge",
        ):
            self.assertIn(symbol, js, "main.js does not use %s" % symbol)


@unittest.skipUnless(NODE_BIN, "node is not installed")
class DailyReviewLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp(prefix="focus-flow-daily-review-")
        with open(HISTORY_PATH, encoding="utf-8") as handle:
            source = handle.read()
        with open(os.path.join(cls.tmp_dir, "history.mjs"), "w", encoding="utf-8") as handle:
            handle.write(source)
        copy_history_dependencies(cls.tmp_dir)
        harness_path = os.path.join(cls.tmp_dir, "harness.mjs")
        with open(harness_path, "w", encoding="utf-8") as handle:
            handle.write(HARNESS)

        # Run in a time zone that observes daylight saving so the local-calendar
        # day matching is genuinely exercised at the 23h / 25h boundaries.
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
            "daily review logic failures: %s"
            % ", ".join(self.payload["failures"]),
        )


if __name__ == "__main__":
    unittest.main()
