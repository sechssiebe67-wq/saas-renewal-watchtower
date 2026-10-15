"""Weekly summary of upcoming deadlines and potential savings."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterable, Optional

from .models import Subscription
from .recommendations import recommend


@dataclass
class WeeklySummary:
    generated_on: _dt.date
    horizon_days: int
    items: list = field(default_factory=list)
    total_potential_savings: float = 0.0
    overdue_count: int = 0

    def to_dict(self) -> dict:
        return {
            "generated_on": self.generated_on.isoformat(),
            "horizon_days": self.horizon_days,
            "items": self.items,
            "total_potential_savings": round(self.total_potential_savings, 2),
            "overdue_count": self.overdue_count,
        }

    def as_text(self) -> str:
        lines = [
            "Wochen-Zusammenfassung – {}".format(self.generated_on.isoformat()),
            "Horizont: {} Tage".format(self.horizon_days),
            "",
        ]
        if not self.items:
            lines.append("Keine Fristen im gewählten Zeitraum.")
        for item in self.items:
            lines.append(
                "- {name}: {deadline} ({days} Tage, {urgency}) → {action}, Einsparung {savings:.2f} {currency}".format(
                    name=item["name"],
                    deadline=item["deadline"],
                    days=item["days_until"],
                    urgency=item["urgency_label"],
                    action=item["action_label"],
                    savings=item["potential_savings"],
                    currency=item["currency"],
                )
            )
        lines.append("")
        lines.append(
            "Gesamtes Einsparpotenzial: {:.2f}".format(self.total_potential_savings)
        )
        return "\n".join(lines)


def build_weekly_summary(
    subscriptions: Iterable[Subscription],
    today: Optional[_dt.date] = None,
    horizon_days: int = 14,
) -> WeeklySummary:
    today = today or _dt.date.today()
    summary = WeeklySummary(generated_on=today, horizon_days=horizon_days)
    for subscription in subscriptions:
        days = subscription.days_until_deadline(today)
        if days is None:
            continue
        if days > horizon_days:
            continue
        rec = recommend(subscription, today)
        item = {
            "id": subscription.id,
            "name": subscription.name,
            "vendor": subscription.vendor,
            "deadline": subscription.deadline.isoformat(),
            "days_until": days,
            "currency": subscription.currency,
            "amount": subscription.amount,
            "action": rec.action,
            "action_label": rec.label,
            "urgency": rec.urgency,
            "urgency_label": rec.urgency_label,
            "reason": rec.reason,
            "potential_savings": rec.potential_savings,
        }
        summary.items.append(item)
        summary.total_potential_savings += rec.potential_savings
        if days < 0:
            summary.overdue_count += 1
    summary.items.sort(key=lambda item: item["days_until"])
    return summary
