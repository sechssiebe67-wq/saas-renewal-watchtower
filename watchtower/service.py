"""Business logic that ties storage, extraction, recommendations and reminders."""

from __future__ import annotations

import datetime as _dt
from typing import Optional

from .extraction import ExtractionResult, extract
from .models import BILLING_PERIODS, PERIODS_PER_YEAR, Subscription, parse_date
from .pdf import extract_text
from .recommendations import recommend
from .reminders import DEFAULT_OFFSETS, build_reminder, due_offsets
from .storage import Storage
from .summary import WeeklySummary, build_weekly_summary


def _to_float(value) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0


def _to_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _to_optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


class WatchtowerService:
    def __init__(self, storage: Storage, sender=None, mail_to: str = "",
                 review_horizon_days: int = 14, clock=None):
        self.storage = storage
        self.sender = sender
        self.mail_to = mail_to
        self.review_horizon_days = review_horizon_days
        self._clock = clock or _dt.date.today

    def today(self) -> _dt.date:
        return self._clock()

    # -- subscriptions ---------------------------------------------------
    def enrich(self, subscription: Subscription, today: Optional[_dt.date] = None) -> dict:
        today = today or self.today()
        rec = recommend(subscription, today)
        days = subscription.days_until_deadline(today)
        utilization = subscription.utilization()
        return {
            "subscription": subscription,
            "recommendation": rec,
            "days_until": days,
            "utilization_percent": round(utilization * 100, 1) if utilization is not None else None,
            "unused_seats": subscription.unused_seats(),
            "annual_cost": subscription.annual_cost(),
        }

    def dashboard(self, today: Optional[_dt.date] = None) -> dict:
        today = today or self.today()
        rows = [self.enrich(sub, today) for sub in self.storage.list_by_deadline()]
        return {
            "rows": rows,
            "kpis": self.kpis(today),
            "summary": self.weekly_summary(today),
        }

    def get_enriched(self, subscription_id: int, today: Optional[_dt.date] = None) -> Optional[dict]:
        subscription = self.storage.get_subscription(subscription_id)
        if subscription is None:
            return None
        return self.enrich(subscription, today)

    def list_enriched(self, today: Optional[_dt.date] = None) -> list:
        today = today or self.today()
        return [self.enrich(sub, today) for sub in self.storage.list_by_deadline()]

    def save_subscription(self, subscription: Subscription) -> int:
        if subscription.id:
            self.storage.update_subscription(subscription)
            return subscription.id
        return self.storage.add_subscription(subscription)

    def delete_subscription(self, subscription_id: int) -> None:
        self.storage.delete_subscription(subscription_id)

    def update_seats(self, subscription_id: int, seats_used, seats_total=None) -> None:
        used = _to_optional_int(seats_used)
        if used is None:
            raise ValueError("seats_used must be an integer")
        self.storage.update_seats(subscription_id, used, _to_optional_int(seats_total))

    # -- capture / extraction -------------------------------------------
    def capture(self, text: str, filename: str = "", source: str = "upload") -> ExtractionResult:
        return extract(text)

    def capture_file(self, filename: str, data: bytes) -> ExtractionResult:
        text = extract_text(filename, data)
        result = extract(text)
        if not text.strip():
            result.warnings.append("no_text_recovered")
        return result

    @staticmethod
    def subscription_from_form(form) -> Subscription:
        def field(name, default=""):
            value = form.get(name)
            return default if value is None else value

        billing = field("billing_period", "monthly")
        if billing not in BILLING_PERIODS:
            billing = "monthly"
        return Subscription(
            id=_to_optional_int(field("id")),
            name=field("name").strip(),
            vendor=field("vendor").strip(),
            amount=_to_float(field("amount")),
            currency=(field("currency", "EUR").strip() or "EUR").upper(),
            billing_period=billing,
            deadline=parse_date(field("deadline")),
            renewal_date=parse_date(field("renewal_date")),
            notice_days=_to_optional_int(field("notice_days")),
            seats_total=_to_optional_int(field("seats_total")),
            seats_used=_to_optional_int(field("seats_used")),
            previous_amount=_to_optional_float(field("previous_amount")),
            owner=field("owner").strip(),
            notes=field("notes").strip(),
            source=field("source", "manual").strip() or "manual",
            source_filename=field("source_filename").strip(),
            confidence=_to_optional_float(field("confidence")),
        )

    @staticmethod
    def draft_from_extraction(extraction: ExtractionResult) -> dict:
        """Produce editable form defaults from an extraction result."""
        def value(field):
            return field.value if field is not None else ""

        deadline = extraction.deadline.value if extraction.deadline else None
        renewal = extraction.renewal_date.value if extraction.renewal_date else None
        return {
            "name": value(extraction.vendor),
            "vendor": value(extraction.vendor),
            "amount": value(extraction.amount),
            "currency": value(extraction.currency) or "EUR",
            "billing_period": value(extraction.billing_period) or "monthly",
            "deadline": deadline.isoformat() if deadline else "",
            "renewal_date": renewal.isoformat() if renewal else "",
            "notice_days": value(extraction.notice_days),
            "seats_total": value(extraction.seats_total),
            "confidence": extraction.overall_confidence(),
            "source": "upload",
        }

    # -- reminders -------------------------------------------------------
    def pending_reminders(self, today: Optional[_dt.date] = None,
                          recipient: Optional[str] = None) -> list:
        today = today or self.today()
        recipient = self.mail_to if recipient is None else recipient
        reminders = []
        for subscription in self.storage.list_subscriptions():
            days = subscription.days_until_deadline(today)
            offsets = due_offsets(days, DEFAULT_OFFSETS)
            if not offsets:
                continue
            # Only the most urgent reached threshold matters; larger windows are
            # considered already passed once this one fires.
            offset = min(offsets)
            if self.storage.was_reminder_sent(subscription.id, offset, subscription.deadline):
                continue
            reminders.append(build_reminder(subscription, offset, recipient, today))
        reminders.sort(key=lambda r: (r.deadline, r.subscription_name))
        return reminders

    def dispatch_reminders(self, today: Optional[_dt.date] = None,
                           recipient: Optional[str] = None, sender=None) -> list:
        sender = sender or self.sender
        if sender is None:
            from .reminders import LoggingSender

            sender = LoggingSender()
        sent = []
        for reminder in self.pending_reminders(today, recipient):
            if sender.send(reminder):
                self.storage.record_sent_reminder(reminder, transport=sender.name)
                sent.append(reminder)
        return sent

    # -- summary / kpis --------------------------------------------------
    def weekly_summary(self, today: Optional[_dt.date] = None,
                       horizon_days: Optional[int] = None) -> WeeklySummary:
        today = today or self.today()
        horizon = self.review_horizon_days if horizon_days is None else horizon_days
        return build_weekly_summary(self.storage.list_subscriptions(), today, horizon)

    def kpis(self, today: Optional[_dt.date] = None) -> dict:
        today = today or self.today()
        subscriptions = self.storage.list_subscriptions()
        annual_cost = sum(sub.annual_cost() for sub in subscriptions)
        periods_savings = 0.0
        annual_savings = 0.0
        overdue = 0
        due_soon = 0
        for subscription in subscriptions:
            rec = recommend(subscription, today)
            periods_savings += rec.potential_savings
            factor = PERIODS_PER_YEAR.get(subscription.billing_period, 0.0)
            annual_savings += rec.potential_savings * (factor or 1.0)
            days = subscription.days_until_deadline(today)
            if days is not None and days < 0:
                overdue += 1
            if days is not None and 0 <= days <= 30:
                due_soon += 1
        return {
            "total": len(subscriptions),
            "annual_cost": round(annual_cost, 2),
            "potential_savings_period": round(periods_savings, 2),
            "potential_savings_annual": round(annual_savings, 2),
            "overdue": overdue,
            "due_soon": due_soon,
        }
