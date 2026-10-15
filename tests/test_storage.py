import datetime as dt
import unittest

from watchtower.models import Subscription
from watchtower.reminders import Reminder
from watchtower.storage import Storage

TODAY = dt.date(2026, 1, 1)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = Storage(":memory:")

    def tearDown(self):
        self.storage.close()

    def _sample(self):
        return Subscription(name="Slack", vendor="Slack", amount=96.0, currency="EUR",
                            deadline=dt.date(2026, 2, 1))

    def test_add_and_get(self):
        sub_id = self.storage.add_subscription(self._sample())
        fetched = self.storage.get_subscription(sub_id)
        self.assertEqual(fetched.name, "Slack")
        self.assertEqual(fetched.deadline, dt.date(2026, 2, 1))
        self.assertEqual(self.storage.count_subscriptions(), 1)

    def test_update(self):
        sub_id = self.storage.add_subscription(self._sample())
        sub = self.storage.get_subscription(sub_id)
        sub.amount = 120.0
        self.storage.update_subscription(sub)
        self.assertEqual(self.storage.get_subscription(sub_id).amount, 120.0)

    def test_delete(self):
        sub_id = self.storage.add_subscription(self._sample())
        self.storage.delete_subscription(sub_id)
        self.assertIsNone(self.storage.get_subscription(sub_id))

    def test_sorted_by_deadline_none_last(self):
        self.storage.add_subscription(self._sample())
        self.storage.add_subscription(Subscription(name="NoDate", amount=1.0))
        self.storage.add_subscription(Subscription(name="Early", amount=1.0,
                                                   deadline=dt.date(2026, 1, 15)))
        ordered = [s.name for s in self.storage.list_by_deadline()]
        self.assertEqual(ordered, ["Early", "Slack", "NoDate"])

    def test_update_seats_records_event(self):
        sub_id = self.storage.add_subscription(self._sample())
        self.storage.update_seats(sub_id, 10, 20)
        sub = self.storage.get_subscription(sub_id)
        self.assertEqual(sub.seats_used, 10)
        self.assertEqual(sub.seats_total, 20)
        events = self.storage.list_events(sub_id)
        self.assertEqual(events[0].kind, "seats_updated")

    def test_reminder_dedupe(self):
        sub_id = self.storage.add_subscription(self._sample())
        reminder = Reminder(subscription_id=sub_id, subscription_name="Slack", offset_days=30,
                            deadline=dt.date(2026, 2, 1), action="cancel", recipient="a@b",
                            subject="s", body="b")
        self.assertFalse(self.storage.was_reminder_sent(sub_id, 30, dt.date(2026, 2, 1)))
        self.storage.record_sent_reminder(reminder, transport="log")
        self.storage.record_sent_reminder(reminder, transport="log")
        self.assertTrue(self.storage.was_reminder_sent(sub_id, 30, dt.date(2026, 2, 1)))
        self.assertEqual(len(self.storage.list_sent_reminders()), 1)


if __name__ == "__main__":
    unittest.main()
