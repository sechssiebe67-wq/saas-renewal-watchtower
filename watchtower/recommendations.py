"""Turn subscription facts into a concrete recommended action.

The goal is the product's core differentiator: not a bare list of deadlines but a
recommendation. The rules are intentionally simple and explainable.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

from .models import Subscription

ACTION_CANCEL = "cancel"
ACTION_SHRINK = "shrink"
ACTION_NEGOTIATE = "negotiate"
ACTION_REVIEW = "review"
ACTION_KEEP = "keep"
ACTION_UNKNOWN = "unknown"

ACTION_LABELS = {
    ACTION_CANCEL: "Kündigen",
    ACTION_SHRINK: "Verkleinern",
    ACTION_NEGOTIATE: "Verhandeln",
    ACTION_REVIEW: "Prüfen",
    ACTION_KEEP: "Behalten",
    ACTION_UNKNOWN: "Unbekannt",
}

URGENCY_OVERDUE = "overdue"
URGENCY_URGENT = "urgent"
URGENCY_SOON = "soon"
URGENCY_UPCOMING = "upcoming"
URGENCY_NONE = "none"

URGENCY_LABELS = {
    URGENCY_OVERDUE: "Überfällig",
    URGENCY_URGENT: "Dringend",
    URGENCY_SOON: "Bald",
    URGENCY_UPCOMING: "Anstehend",
    URGENCY_NONE: "Später",
}

# Utilisation thresholds.
LOW_UTILISATION = 0.5
MEDIUM_UTILISATION = 0.8
# A price increase above this fraction triggers a negotiation hint.
PRICE_INCREASE_THRESHOLD = 0.05
NEGOTIATION_SAVINGS_RATE = 0.10


@dataclass
class Recommendation:
    action: str
    reason: str
    urgency: str
    potential_savings: float
    confidence: float

    @property
    def label(self) -> str:
        return ACTION_LABELS.get(self.action, self.action)

    @property
    def urgency_label(self) -> str:
        return URGENCY_LABELS.get(self.urgency, self.urgency)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "label": self.label,
            "reason": self.reason,
            "urgency": self.urgency,
            "urgency_label": self.urgency_label,
            "potential_savings": round(self.potential_savings, 2),
            "confidence": round(self.confidence, 3),
        }


def _urgency_for_days(days: Optional[int]) -> str:
    if days is None:
        return URGENCY_NONE
    if days < 0:
        return URGENCY_OVERDUE
    if days <= 7:
        return URGENCY_URGENT
    if days <= 30:
        return URGENCY_SOON
    if days <= 60:
        return URGENCY_UPCOMING
    return URGENCY_NONE


def recommend(subscription: Subscription, today: Optional[_dt.date] = None) -> Recommendation:
    today = today or _dt.date.today()
    days = subscription.days_until_deadline(today)
    urgency = _urgency_for_days(days)
    utilization = subscription.utilization()

    if subscription.deadline is None:
        return Recommendation(
            ACTION_REVIEW,
            "Kein Kündigungstermin hinterlegt – Datum aus Vertrag ergänzen.",
            URGENCY_NONE,
            0.0,
            0.3,
        )

    # Price increase detection.
    price_increase = (
        subscription.previous_amount is not None
        and subscription.previous_amount > 0
        and subscription.amount > subscription.previous_amount * (1 + PRICE_INCREASE_THRESHOLD)
    )

    if utilization is not None and utilization < LOW_UTILISATION and (days is None or days <= 60):
        savings = subscription.amount
        return Recommendation(
            ACTION_CANCEL,
            "Nur {:.0f}% der {:.0f} Lizenzen genutzt und Frist naht – Kündigung prüfen."
            .format(utilization * 100, subscription.seats_total or 0),
            urgency,
            savings,
            0.85,
        )

    if utilization is not None and utilization < MEDIUM_UTILISATION:
        savings = round(subscription.amount * (1 - utilization), 2)
        return Recommendation(
            ACTION_SHRINK,
            "Nur {:.0f}% der Lizenzen genutzt – auf {} Seats verkleinern."
            .format(utilization * 100, max(0, subscription.seats_used or 0)),
            urgency,
            savings,
            0.8,
        )

    if price_increase:
        savings = round(subscription.amount * NEGOTIATION_SAVINGS_RATE, 2)
        return Recommendation(
            ACTION_NEGOTIATE,
            "Preis stieg von {} auf {} – Erhöhung hinterfragen oder verhandeln."
            .format(subscription.previous_amount, subscription.amount),
            urgency,
            savings,
            0.7,
        )

    if days <= 30:
        return Recommendation(
            ACTION_REVIEW,
            "Frist in {} Tagen – Konditionen und Auslastung prüfen.".format(days),
            urgency,
            0.0,
            0.6,
        )

    return Recommendation(
        ACTION_KEEP,
        "Auslastung in Ordnung, Frist in {} Tagen – weiter beobachten.".format(days),
        urgency,
        0.0,
        0.5,
    )
