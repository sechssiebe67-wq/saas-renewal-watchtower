"""SQLite persistence for subscriptions, sent reminders and events.

The database is the only stateful component. It is accessed through a single
connection guarded by a re-entrant lock so the threaded WSGI server can share it.
"""

from __future__ import annotations

import datetime as _dt
import os
import sqlite3
import threading
from typing import Optional

from .models import Event, SentReminder, Subscription, format_date
from .reminders import Reminder

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    vendor TEXT NOT NULL DEFAULT '',
    amount REAL NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'EUR',
    billing_period TEXT NOT NULL DEFAULT 'monthly',
    deadline TEXT,
    renewal_date TEXT,
    notice_days INTEGER,
    seats_total INTEGER,
    seats_used INTEGER,
    previous_amount REAL,
    owner TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    source_filename TEXT NOT NULL DEFAULT '',
    confidence REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER,
    subscription_name TEXT NOT NULL DEFAULT '',
    offset_days INTEGER NOT NULL,
    deadline TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT '',
    recipient TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    transport TEXT NOT NULL DEFAULT 'log',
    sent_at TEXT NOT NULL,
    UNIQUE (subscription_id, offset_days, deadline)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER,
    kind TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
"""



def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class Storage:
    def __init__(self, path: str):
        self.path = path
        if path not in (":memory:",) and not path.startswith("file:"):
            parent = os.path.dirname(os.path.abspath(path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- subscriptions ---------------------------------------------------
    def add_subscription(self, subscription: Subscription) -> int:
        now = _now_iso()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO subscriptions (
                    name, vendor, amount, currency, billing_period, deadline,
                    renewal_date, notice_days, seats_total, seats_used,
                    previous_amount, owner, notes, source, source_filename,
                    confidence, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    subscription.name, subscription.vendor, subscription.amount,
                    subscription.currency, subscription.billing_period,
                    format_date(subscription.deadline),
                    format_date(subscription.renewal_date),
                    subscription.notice_days, subscription.seats_total,
                    subscription.seats_used, subscription.previous_amount,
                    subscription.owner, subscription.notes, subscription.source,
                    subscription.source_filename, subscription.confidence,
                    now, now,
                ),
            )
            self._conn.commit()
            subscription.id = cursor.lastrowid
            subscription.created_at = now
            subscription.updated_at = now
            return cursor.lastrowid

    def update_subscription(self, subscription: Subscription) -> None:
        now = _now_iso()
        with self._lock:
            self._conn.execute(
                """
                UPDATE subscriptions SET
                    name=?, vendor=?, amount=?, currency=?, billing_period=?,
                    deadline=?, renewal_date=?, notice_days=?, seats_total=?,
                    seats_used=?, previous_amount=?, owner=?, notes=?, source=?,
                    source_filename=?, confidence=?, updated_at=?
                WHERE id=?
                """,
                (
                    subscription.name, subscription.vendor, subscription.amount,
                    subscription.currency, subscription.billing_period,
                    format_date(subscription.deadline),
                    format_date(subscription.renewal_date),
                    subscription.notice_days, subscription.seats_total,
                    subscription.seats_used, subscription.previous_amount,
                    subscription.owner, subscription.notes, subscription.source,
                    subscription.source_filename, subscription.confidence,
                    now, subscription.id,
                ),
            )
            self._conn.commit()
            subscription.updated_at = now

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM subscriptions WHERE id=?", (subscription_id,)
            ).fetchone()
        return Subscription.from_row(row) if row else None

    def list_subscriptions(self) -> list:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM subscriptions").fetchall()
        return [Subscription.from_row(row) for row in rows]

    def list_by_deadline(self) -> list:
        """Subscriptions with a deadline first, sorted ascending."""
        subscriptions = self.list_subscriptions()
        subscriptions.sort(
            key=lambda s: (s.deadline is None, s.deadline or _dt.date.max)
        )
        return subscriptions

    def delete_subscription(self, subscription_id: int) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM subscriptions WHERE id=?", (subscription_id,))
            self._conn.execute(
                "DELETE FROM sent_reminders WHERE subscription_id=?", (subscription_id,)
            )
            self._conn.commit()

    def update_seats(self, subscription_id: int, seats_used: int, seats_total=None) -> None:
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise KeyError("subscription {} not found".format(subscription_id))
        subscription.seats_used = seats_used
        if seats_total is not None:
            subscription.seats_total = seats_total
        self.update_subscription(subscription)
        self.add_event(subscription_id, "seats_updated", "used={}".format(seats_used))

    def count_subscriptions(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM subscriptions").fetchone()
        return int(row["n"])

    # -- reminders -------------------------------------------------------
    def was_reminder_sent(self, subscription_id, offset_days: int, deadline) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM sent_reminders WHERE subscription_id=? AND offset_days=? AND deadline=?",
                (subscription_id, offset_days, format_date(deadline)),
            ).fetchone()
        return row is not None

    def record_sent_reminder(self, reminder: Reminder, transport: str = "log",
                             sent_at: Optional[str] = None) -> None:
        sent_at = sent_at or _now_iso()
        with self._lock:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO sent_reminders (
                    subscription_id, subscription_name, offset_days, deadline,
                    action, recipient, subject, body, transport, sent_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    reminder.subscription_id, reminder.subscription_name,
                    reminder.offset_days, format_date(reminder.deadline),
                    reminder.action, reminder.recipient, reminder.subject,
                    reminder.body, transport, sent_at,
                ),
            )
            self._conn.commit()

    def list_sent_reminders(self, limit: int = 100) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM sent_reminders ORDER BY sent_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [SentReminder.from_row(row) for row in rows]

    # -- events ----------------------------------------------------------
    def add_event(self, subscription_id, kind: str, detail: str = "") -> None:
        now = _now_iso()
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (subscription_id, kind, detail, created_at) VALUES (?,?,?,?)",
                (subscription_id, kind, detail, now),
            )
            self._conn.commit()

    def list_events(self, subscription_id, limit: int = 50) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE subscription_id=? ORDER BY id DESC LIMIT ?",
                (subscription_id, limit),
            ).fetchall()
        return [
            Event(
                id=row["id"],
                subscription_id=row["subscription_id"],
                kind=row["kind"],
                detail=row["detail"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
