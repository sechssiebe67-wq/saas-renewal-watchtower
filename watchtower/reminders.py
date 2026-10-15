"""Reminder generation and delivery.

A reminder is created 60, 30 and 7 days before a cancellation deadline and
contains the recommended action. Delivery is pluggable: a logging sender is the
default, SMTP is used when configured.
"""

from __future__ import annotations

import datetime as _dt
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable, Optional

from .models import Subscription, format_date
from .recommendations import Recommendation, recommend

LOGGER = logging.getLogger("watchtower.reminders")

DEFAULT_OFFSETS = (60, 30, 7)


@dataclass
class Reminder:
    subscription_id: Optional[int]
    subscription_name: str
    offset_days: int
    deadline: _dt.date
    action: str
    recipient: str
    subject: str
    body: str

    def to_dict(self) -> dict:
        return {
            "subscription_id": self.subscription_id,
            "subscription_name": self.subscription_name,
            "offset_days": self.offset_days,
            "deadline": format_date(self.deadline),
            "action": self.action,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
        }


def due_offsets(days_until: Optional[int], offsets: Iterable[int] = DEFAULT_OFFSETS) -> list:
    """Return the offsets whose threshold has been reached, largest first."""
    if days_until is None:
        return []
    return [offset for offset in sorted(offsets, reverse=True) if 0 <= days_until <= offset]


def build_reminder(
    subscription: Subscription,
    offset_days: int,
    recipient: str,
    today: Optional[_dt.date] = None,
) -> Reminder:
    today = today or _dt.date.today()
    rec: Recommendation = recommend(subscription, today)
    deadline = subscription.deadline or today
    subject = (
        "[Watchtower] Frist in {offset} Tagen: {name} – handeln: {action}".format(
            offset=offset_days,
            name=subscription.name or "Abo",
            action=rec.label,
        )
    )
    savings = ""
    if rec.potential_savings > 0:
        savings = "Geschätztes Einsparpotenzial: {:.2f} {} pro Abrechnungszeitraum.\n".format(
            rec.potential_savings, subscription.currency
        )
    body = (
        "Hallo,\n\n"
        "das Abo \"{name}\" (Anbieter: {vendor}) verlängert sich zum {deadline}.\n"
        "Die Kündigungsfrist endet in {offset} Tagen.\n\n"
        "Empfohlene Aktion: {action}\n"
        "Begründung: {reason}\n"
        "{savings}\n"
        "Auslastung: {seats}\n\n"
        "Bitte prüfen und rechtzeitig handeln.\n\n"
        "-- SaaS Renewal Watchtower\n"
    ).format(
        name=subscription.name or "Abo",
        vendor=subscription.vendor or "unbekannt",
        deadline=format_date(deadline),
        offset=offset_days,
        action=rec.label,
        reason=rec.reason,
        savings=savings,
        seats=_seats_text(subscription),
    )
    return Reminder(
        subscription_id=subscription.id,
        subscription_name=subscription.name,
        offset_days=offset_days,
        deadline=deadline,
        action=rec.action,
        recipient=recipient,
        subject=subject,
        body=body,
    )


def _seats_text(subscription: Subscription) -> str:
    if subscription.seats_total is None:
        return "nicht erfasst"
    used = subscription.seats_used if subscription.seats_used is not None else "?"
    return "{}/{} Seats genutzt".format(used, subscription.seats_total)


class Sender:
    """Delivery abstraction."""

    name = "base"

    def send(self, reminder: Reminder) -> bool:  # pragma: no cover - interface
        raise NotImplementedError


class LoggingSender(Sender):
    name = "log"

    def send(self, reminder: Reminder) -> bool:
        LOGGER.info(
            "reminder offset=%s to=%s subject=%s\n%s",
            reminder.offset_days,
            reminder.recipient or "(unset)",
            reminder.subject,
            reminder.body,
        )
        return True


class SmtpSender(Sender):
    name = "smtp"

    def __init__(self, host, port, user=None, password=None, mail_from="watchtower@localhost",
                 use_tls=True):
        self.host = host
        self.port = int(port)
        self.user = user
        self.password = password
        self.mail_from = mail_from
        self.use_tls = use_tls

    def send(self, reminder: Reminder) -> bool:
        if not reminder.recipient:
            LOGGER.warning("No recipient configured; reminder kept in log only.")
            return LoggingSender().send(reminder)
        message = EmailMessage()
        message["From"] = self.mail_from
        message["To"] = reminder.recipient
        message["Subject"] = reminder.subject
        message.set_content(reminder.body)
        with smtplib.SMTP(self.host, self.port, timeout=15) as client:
            if self.use_tls:
                client.starttls()
            if self.user:
                client.login(self.user, self.password or "")
            client.send_message(message)
        return True


class RecordingSender(Sender):
    """In-memory sender used by tests and previews."""

    name = "record"

    def __init__(self):
        self.sent: list = []

    def send(self, reminder: Reminder) -> bool:
        self.sent.append(reminder)
        return True
