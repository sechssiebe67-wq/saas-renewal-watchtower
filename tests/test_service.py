import datetime as dt
import unittest

from watchtower.reminders import RecordingSender
from watchtower.service import WatchtowerService
from watchtower.storage import Storage

TODAY = dt.date(2026, 1, 1)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.storage = Storage(":memory:")
        self.sender = RecordingSender()
        self.service = WatchtowerService(
            self.storage, sender=self.sender, mail_to="ops@example.com",
            clock=lambda: TODAY,
        )

    def tearDown(self):
        self.storage.close()

    def test_form_roundtrip(self):
        form = {
            "name": "GitHub", "vendor": "GitHub Inc.", "amount": "210,50",
            "currency": "eur", "billing_period": "monthly", "deadline": "2027-01-15",
            "notice_days": "30", "seats_total": "50", "seats_used": "18",
        }
        sub = self.service.subscription_from_form(form)
        self.assertEqual(sub.amount, 210.50)
        self.assertEqual(sub.currency, "EUR")
        self.assertEqual(sub.deadline, dt.date(2027, 1, 15))
        self.assertEqual(sub.seats_used, 18)

    def test_dashboard_and_kpis(self):
        self.service.save_subscription(self._sub("A", 10, TODAY + dt.timedelta(days=5), 20, 4))
        self.service.save_subscription(self._sub("B", 20, TODAY + dt.timedelta(days=90), 10, 10))
        data = self.service.dashboard()
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["kpis"]["total"], 2)
        self.assertEqual(data["kpis"]["due_soon"], 1)

    def test_dispatch_idempotent(self):
        self.service.save_subscription(self._sub("Slack", 96, TODAY + dt.timedelta(days=7), 40, 5))
        first = self.service.dispatch_reminders()
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].offset_days, 7)
        second = self.service.dispatch_reminders()
        self.assertEqual(second, [])
        self.assertEqual(len(self.sender.sent), 1)

    def test_reminder_windows(self):
        self.service.save_subscription(self._sub("X", 100, TODAY + dt.timedelta(days=55), 10, 10))
        self.assertEqual([r.offset_days for r in self.service.dispatch_reminders()], [60])
        self.service._clock = lambda: TODAY + dt.timedelta(days=30)
        self.assertEqual([r.offset_days for r in self.service.dispatch_reminders()], [30])
        self.service._clock = lambda: TODAY + dt.timedelta(days=53)
        self.assertEqual([r.offset_days for r in self.service.dispatch_reminders()], [7])

    def test_weekly_summary(self):
        self.service.save_subscription(self._sub("A", 10, TODAY + dt.timedelta(days=3), 20, 4))
        self.service.save_subscription(self._sub("B", 10, TODAY + dt.timedelta(days=40), 20, 20))
        summary = self.service.weekly_summary()
        self.assertEqual(len(summary.items), 1)
        self.assertIn("Wochen-Zusammenfassung", summary.as_text())

    def test_draft_from_extraction(self):
        from watchtower.extraction import extract

        result = extract("Gesamtbetrag: 49,00 EUR\nKündigungstermin: 13.02.2027\n")
        draft = self.service.draft_from_extraction(result)
        self.assertEqual(draft["amount"], 49.0)
        self.assertEqual(draft["deadline"], "2027-02-13")

    def _sub(self, name, amount, deadline, seats_total, seats_used):
        from watchtower.models import Subscription

        return Subscription(name=name, amount=amount, deadline=deadline,
                            seats_total=seats_total, seats_used=seats_used,
                            billing_period="monthly")


if __name__ == "__main__":
    unittest.main()
