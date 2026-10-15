import datetime as dt
import unittest

from wsgi_client import Client
from watchtower.reminders import RecordingSender
from watchtower.service import WatchtowerService
from watchtower.storage import Storage
from watchtower.web.app import create_app

TODAY = dt.date(2026, 1, 1)


class WebTests(unittest.TestCase):
    def setUp(self):
        self.storage = Storage(":memory:")
        self.sender = RecordingSender()
        self.service = WatchtowerService(
            self.storage, sender=self.sender, mail_to="ops@example.com",
            clock=lambda: TODAY,
        )
        self.client = Client(create_app(self.service))

    def tearDown(self):
        self.storage.close()

    def test_healthz(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dashboard_empty(self):
        response = self.client.get("/")
        self.assertEqual(response.status, 200)
        self.assertIn("Watchtower", response.text)

    def test_create_subscription(self):
        response = self.client.post("/subscriptions", data={
            "name": "GitHub", "vendor": "GitHub", "amount": "210.50",
            "currency": "EUR", "billing_period": "monthly", "deadline": "2027-01-15",
            "notice_days": "30", "seats_total": "50", "seats_used": "18",
        })
        self.assertEqual(response.status, 303)
        self.assertEqual(self.storage.count_subscriptions(), 1)
        detail = self.client.get(response.headers["Location"])
        self.assertEqual(detail.status, 200)
        self.assertIn("GitHub", detail.text)

    def test_create_requires_name(self):
        response = self.client.post("/subscriptions", data={"name": ""})
        self.assertEqual(response.status, 400)

    def test_upload_paste_extraction(self):
        response = self.client.post("/upload", data={
            "text": "Gesamtbetrag: 49,00 EUR\nKündigungstermin: 13.02.2027\nLizenzen: 20 Benutzer\n",
        })
        self.assertEqual(response.status, 200)
        self.assertIn("Extraktion", response.text)
        self.assertIn("49.0", response.text)
        self.assertIn("2027-02-13", response.text)
        self.assertIn("20", response.text)

    def test_update_seats(self):
        sub_id = self.service.save_subscription(self._sub())
        response = self.client.post("/subscriptions/{}/seats".format(sub_id),
                                    data={"seats_used": "7", "seats_total": "20"})
        self.assertEqual(response.status, 303)
        self.assertEqual(self.storage.get_subscription(sub_id).seats_used, 7)

    def test_delete(self):
        sub_id = self.service.save_subscription(self._sub())
        response = self.client.post("/subscriptions/{}/delete".format(sub_id))
        self.assertEqual(response.status, 303)
        self.assertIsNone(self.storage.get_subscription(sub_id))

    def test_reminders_dispatch(self):
        sub_id = self.service.save_subscription(self._sub(deadline=TODAY + dt.timedelta(days=5)))
        page = self.client.get("/reminders")
        self.assertEqual(page.status, 200)
        self.assertIn("Fällig", page.text)
        response = self.client.post("/reminders/dispatch")
        self.assertEqual(response.status, 303)
        self.assertEqual(len(self.sender.sent), 1)
        self.assertEqual(len(self.storage.list_sent_reminders()), 1)

    def test_summary_json(self):
        self.service.save_subscription(self._sub(deadline=TODAY + dt.timedelta(days=3)))
        response = self.client.get("/summary", query="format=json")
        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.json()["items"]), 1)

    def test_api_subscriptions(self):
        self.service.save_subscription(self._sub())
        response = self.client.get("/api/subscriptions")
        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.json()["subscriptions"]), 1)

    def test_not_found(self):
        self.assertEqual(self.client.get("/does-not-exist").status, 404)

    def _sub(self, deadline=None):
        from watchtower.models import Subscription

        return Subscription(name="Slack", vendor="Slack", amount=96.0,
                            deadline=deadline or TODAY + dt.timedelta(days=7),
                            seats_total=40, seats_used=5)


if __name__ == "__main__":
    unittest.main()
