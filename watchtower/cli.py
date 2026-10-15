"""Command line interface for operations and demos.

Usage::

    python -m watchtower serve
    python -m watchtower summary
    python -m watchtower reminders
    python -m watchtower dispatch
    python -m watchtower add --name "GitHub" --amount 210 --deadline 2027-01-15 --seats-total 25 --seats-used 8
    python -m watchtower extract invoice.txt
    python -m watchtower seed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys

from .config import Config
from .models import Subscription, parse_date
from .server import build_service
from .storage import Storage


def _build(args):
    config = Config.from_env()
    if getattr(args, "db", None):
        config.db_path = args.db
    return config, build_service(config)


def cmd_serve(args) -> int:
    config, _ = _build(args)
    if getattr(args, "port", None):
        config.port = args.port
    from .server import run

    run(config)
    return 0


def cmd_summary(args) -> int:
    _, service = _build(args)
    print(service.weekly_summary().as_text())
    return 0


def cmd_reminders(args) -> int:
    _, service = _build(args)
    pending = service.pending_reminders()
    if not pending:
        print("Keine fälligen Erinnerungen.")
        return 0
    for reminder in pending:
        print("[{}d] {} -> {}".format(reminder.offset_days, reminder.subscription_name, reminder.subject))
    return 0


def cmd_dispatch(args) -> int:
    _, service = _build(args)
    sent = service.dispatch_reminders()
    print("{} Erinnerung(en) versendet.".format(len(sent)))
    return 0


def cmd_add(args) -> int:
    _, service = _build(args)
    subscription = Subscription(
        name=args.name,
        vendor=args.vendor or "",
        amount=args.amount,
        currency=args.currency,
        billing_period=args.billing_period,
        deadline=parse_date(args.deadline),
        notice_days=args.notice_days,
        seats_total=args.seats_total,
        seats_used=args.seats_used,
        previous_amount=args.previous_amount,
    )
    subscription_id = service.save_subscription(subscription)
    print("Abo #{} gespeichert.".format(subscription_id))
    return 0


def cmd_extract(args) -> int:
    _, service = _build(args)
    with open(args.path, "rb") as handle:
        data = handle.read()
    import os

    extraction = service.capture_file(os.path.basename(args.path), data)
    for label, field in [
        ("Betrag", extraction.amount),
        ("Währung", extraction.currency),
        ("Frist", extraction.deadline),
        ("Verlängerung", extraction.renewal_date),
        ("Kündigungsfrist", extraction.notice_days),
        ("Seats", extraction.seats_total),
        ("Anbieter", extraction.vendor),
    ]:
        if field is None:
            print("{:<20} nicht erkannt".format(label))
            continue
        value = field.value
        if isinstance(value, _dt.date):
            value = value.isoformat()
        print("{:<20} {} (Konfidenz {:.0%})".format(label, value, field.confidence))
    return 0


def cmd_seed(args) -> int:
    """Populate a few example subscriptions for local demos."""
    config, service = _build(args)
    today = _dt.date.today()
    examples = [
        Subscription(name="GitHub Enterprise", vendor="GitHub", amount=210.0, currency="EUR",
                     billing_period="monthly", deadline=today + _dt.timedelta(days=45),
                     notice_days=30, seats_total=50, seats_used=18, source="manual",
                     previous_amount=190.0),
        Subscription(name="Salesforce Sales Cloud", vendor="Salesforce", amount=1800.0,
                     currency="EUR", billing_period="monthly",
                     deadline=today + _dt.timedelta(days=12), notice_days=60,
                     seats_total=20, seats_used=19, source="manual"),
        Subscription(name="Slack Pro", vendor="Slack", amount=96.0, currency="EUR",
                     billing_period="monthly", deadline=today + _dt.timedelta(days=5),
                     notice_days=7, seats_total=40, seats_used=12, source="manual"),
    ]
    for example in examples:
        service.save_subscription(example)
    print("{} Beispiel-Abos in {} angelegt.".format(len(examples), config.db_path))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="watchtower", description="SaaS Renewal Watchtower")
    parser.add_argument("--db", help="SQLite database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="Start the HTTP server")
    p_serve.add_argument("--port", type=int, default=0)
    p_serve.set_defaults(func=cmd_serve)

    sub.add_parser("summary", help="Print the weekly summary").set_defaults(func=cmd_summary)
    sub.add_parser("reminders", help="List pending reminders").set_defaults(func=cmd_reminders)
    sub.add_parser("dispatch", help="Send due reminders").set_defaults(func=cmd_dispatch)
    sub.add_parser("seed", help="Insert example data").set_defaults(func=cmd_seed)

    p_add = sub.add_parser("add", help="Add a subscription")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--vendor", default="")
    p_add.add_argument("--amount", type=float, default=0.0)
    p_add.add_argument("--currency", default="EUR")
    p_add.add_argument("--billing-period", default="monthly")
    p_add.add_argument("--deadline")
    p_add.add_argument("--notice-days", type=int)
    p_add.add_argument("--seats-total", type=int)
    p_add.add_argument("--seats-used", type=int)
    p_add.add_argument("--previous-amount", type=float)
    p_add.set_defaults(func=cmd_add)

    p_extract = sub.add_parser("extract", help="Extract fields from a file")
    p_extract.add_argument("path")
    p_extract.set_defaults(func=cmd_extract)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "port", None) == 0:
        args.port = None
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
