"""Domain models for the watchtower.

The models are deliberately dependency-free dataclasses so they can be used by
the storage layer, the extraction pipeline, the recommendation engine and the
web layer without pulling in a framework.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

BILLING_PERIODS = ("monthly", "quarterly", "yearly", "one_time")

PERIODS_PER_YEAR = {
    "monthly": 12.0,
    "quarterly": 4.0,
    "yearly": 1.0,
    "one_time": 0.0,
}


def parse_date(value) -> Optional[_dt.date]:
    """Parse an ISO date (``YYYY-MM-DD``) or ``datetime.date``.

    Returns ``None`` for empty or invalid input instead of raising, because the
    value frequently comes from extracted user data.
    """
    if value is None or value == "":
        return None
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    try:
        return _dt.date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def format_date(value) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else ""


@dataclass
class Subscription:
    """A single watched subscription."""

    id: Optional[int] = None
    name: str = ""
    vendor: str = ""
    amount: float = 0.0
    currency: str = "EUR"
    billing_period: str = "monthly"
    deadline: Optional[_dt.date] = None
    renewal_date: Optional[_dt.date] = None
    notice_days: Optional[int] = None
    seats_total: Optional[int] = None
    seats_used: Optional[int] = None
    previous_amount: Optional[float] = None
    owner: str = ""
    notes: str = ""
    source: str = "manual"
    source_filename: str = ""
    confidence: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def days_until_deadline(self, today: _dt.date) -> Optional[int]:
        if self.deadline is None:
            return None
        return (self.deadline - today).days

    def utilization(self) -> Optional[float]:
        """Seat utilisation in ``[0, 1]`` or ``None`` when unknown."""
        if self.seats_total is None or self.seats_total <= 0:
            return None
        if self.seats_used is None:
            return None
        used = max(0, self.seats_used)
        return min(1.0, used / float(self.seats_total))

    def unused_seats(self) -> Optional[int]:
        if self.seats_total is None or self.seats_used is None:
            return None
        return max(0, self.seats_total - self.seats_used)

    def annual_cost(self) -> float:
        return round(self.amount * PERIODS_PER_YEAR.get(self.billing_period, 0.0), 2)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "amount": self.amount,
            "currency": self.currency,
            "billing_period": self.billing_period,
            "deadline": format_date(self.deadline),
            "renewal_date": format_date(self.renewal_date),
            "notice_days": self.notice_days,
            "seats_total": self.seats_total,
            "seats_used": self.seats_used,
            "previous_amount": self.previous_amount,
            "owner": self.owner,
            "notes": self.notes,
            "source": self.source,
            "source_filename": self.source_filename,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> "Subscription":
        keys = row.keys()

        def get(key, default=None):
            return row[key] if key in keys else default

        return cls(
            id=get("id"),
            name=get("name", "") or "",
            vendor=get("vendor", "") or "",
            amount=float(get("amount", 0.0) or 0.0),
            currency=get("currency", "EUR") or "EUR",
            billing_period=get("billing_period", "monthly") or "monthly",
            deadline=parse_date(get("deadline")),
            renewal_date=parse_date(get("renewal_date")),
            notice_days=get("notice_days"),
            seats_total=get("seats_total"),
            seats_used=get("seats_used"),
            previous_amount=get("previous_amount"),
            owner=get("owner", "") or "",
            notes=get("notes", "") or "",
            source=get("source", "manual") or "manual",
            source_filename=get("source_filename", "") or "",
            confidence=get("confidence"),
            created_at=get("created_at"),
            updated_at=get("updated_at"),
        )


@dataclass
class SentReminder:
    id: Optional[int] = None
    subscription_id: Optional[int] = None
    subscription_name: str = ""
    offset_days: int = 0
    deadline: Optional[_dt.date] = None
    action: str = ""
    recipient: str = ""
    subject: str = ""
    sent_at: Optional[str] = None
    transport: str = "log"

    @classmethod
    def from_row(cls, row) -> "SentReminder":
        keys = row.keys()

        def get(key, default=None):
            return row[key] if key in keys else default

        return cls(
            id=get("id"),
            subscription_id=get("subscription_id"),
            subscription_name=get("subscription_name", "") or "",
            offset_days=int(get("offset_days", 0) or 0),
            deadline=parse_date(get("deadline")),
            action=get("action", "") or "",
            recipient=get("recipient", "") or "",
            subject=get("subject", "") or "",
            sent_at=get("sent_at"),
            transport=get("transport", "log") or "log",
        )


@dataclass
class Event:
    id: Optional[int] = None
    subscription_id: Optional[int] = None
    kind: str = ""
    detail: str = ""
    created_at: Optional[str] = None
