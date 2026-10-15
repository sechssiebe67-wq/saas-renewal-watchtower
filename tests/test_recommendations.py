import datetime as dt
import unittest

from watchtower.models import Subscription
from watchtower.recommendations import (
    ACTION_CANCEL,
    ACTION_KEEP,
    ACTION_NEGOTIATE,
    ACTION_REVIEW,
    ACTION_SHRINK,
    URGENCY_OVERDUE,
    URGENCY_URGENT,
    recommend,
)

TODAY = dt.date(2026, 1, 1)


class RecommendationTests(unittest.TestCase):
    def test_cancel_when_underused_and_near(self):
        sub = Subscription(name="Slack", amount=100.0, deadline=TODAY + dt.timedelta(days=10),
                           seats_total=40, seats_used=8)
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.action, ACTION_CANCEL)
        self.assertEqual(rec.potential_savings, 100.0)

    def test_shrink_when_medium_usage(self):
        sub = Subscription(name="GitHub", amount=200.0, deadline=TODAY + dt.timedelta(days=50),
                           seats_total=50, seats_used=30)
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.action, ACTION_SHRINK)
        self.assertAlmostEqual(rec.potential_savings, 80.0, places=2)

    def test_negotiate_on_price_increase(self):
        sub = Subscription(name="Salesforce", amount=110.0, previous_amount=100.0,
                           deadline=TODAY + dt.timedelta(days=40), seats_total=10, seats_used=10)
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.action, ACTION_NEGOTIATE)
        self.assertGreater(rec.potential_savings, 0)

    def test_review_without_deadline(self):
        sub = Subscription(name="Unknown", amount=10.0)
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.action, ACTION_REVIEW)

    def test_keep_when_healthy(self):
        sub = Subscription(name="Zoom", amount=50.0, deadline=TODAY + dt.timedelta(days=120),
                           seats_total=10, seats_used=10)
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.action, ACTION_KEEP)

    def test_urgency_overdue(self):
        sub = Subscription(name="Late", amount=50.0, deadline=TODAY - dt.timedelta(days=2))
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.urgency, URGENCY_OVERDUE)

    def test_urgency_urgent(self):
        sub = Subscription(name="Soon", amount=50.0, deadline=TODAY + dt.timedelta(days=5))
        rec = recommend(sub, TODAY)
        self.assertEqual(rec.urgency, URGENCY_URGENT)


if __name__ == "__main__":
    unittest.main()
