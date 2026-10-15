import datetime as dt
import unittest

from watchtower.models import Subscription
from watchtower.reminders import (
    LoggingSender,
    RecordingSender,
    build_reminder,
    due_offsets,
)

TODAY = dt.date(2026, 1, 1)


class ReminderTests(unittest.TestCase):
    def test_due_offsets(self):
        self.assertEqual(due_offsets(None), [])
        self.assertEqual(due_offsets(61), [])
        self.assertEqual(due_offsets(60), [60])
        self.assertEqual(due_offsets(45), [60])
        self.assertEqual(due_offsets(25), [60, 30])
        self.assertEqual(due_offsets(3), [60, 30, 7])
        self.assertEqual(due_offsets(-1), [])

    def test_build_reminder_contains_action(self):
        sub = Subscription(id=1, name="Slack", vendor="Slack", amount=96.0,
                           deadline=TODAY + dt.timedelta(days=7), seats_total=40, seats_used=5)
        reminder = build_reminder(sub, 7, "ops@example.com", TODAY)
        self.assertIn("Slack", reminder.subject)
        self.assertIn("7", reminder.subject)
        self.assertIn("Kündigen", reminder.body)
        self.assertEqual(reminder.deadline, TODAY + dt.timedelta(days=7))

    def test_recording_sender(self):
        sender = RecordingSender()
        sub = Subscription(id=1, name="X", amount=10.0, deadline=TODAY + dt.timedelta(days=7))
        reminder = build_reminder(sub, 7, "a@b", TODAY)
        self.assertTrue(sender.send(reminder))
        self.assertEqual(len(sender.sent), 1)

    def test_logging_sender_without_recipient(self):
        sender = LoggingSender()
        sub = Subscription(id=1, name="X", amount=10.0, deadline=TODAY + dt.timedelta(days=7))
        reminder = build_reminder(sub, 7, "", TODAY)
        self.assertTrue(sender.send(reminder))


if __name__ == "__main__":
    unittest.main()
