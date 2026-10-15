"""Runtime configuration read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    db_path: str = "data/watchtower.db"
    host: str = "0.0.0.0"
    port: int = 8080
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "watchtower@localhost"
    mail_to: str = ""
    scheduler_enabled: bool = False
    scheduler_interval: int = 3600
    review_horizon_days: int = 14

    @classmethod
    def from_env(cls, env=None) -> "Config":
        env = env if env is not None else os.environ

        def get(name, default):
            value = env.get(name)
            return default if value is None or value == "" else value

        return cls(
            db_path=get("WATCHTOWER_DB", "data/watchtower.db"),
            host=get("WATCHTOWER_HOST", "0.0.0.0"),
            port=int(get("WATCHTOWER_PORT", "8080")),
            smtp_host=get("WATCHTOWER_SMTP_HOST", ""),
            smtp_port=int(get("WATCHTOWER_SMTP_PORT", "587")),
            smtp_user=get("WATCHTOWER_SMTP_USER", ""),
            smtp_password=get("WATCHTOWER_SMTP_PASSWORD", ""),
            mail_from=get("WATCHTOWER_MAIL_FROM", "watchtower@localhost"),
            mail_to=get("WATCHTOWER_MAIL_TO", ""),
            scheduler_enabled=_as_bool(get("WATCHTOWER_SCHEDULER_ENABLED", "0")),
            scheduler_interval=int(get("WATCHTOWER_SCHEDULER_INTERVAL", "3600")),
            review_horizon_days=int(get("WATCHTOWER_REVIEW_HORIZON_DAYS", "14")),
        )

    def build_sender(self):
        from .reminders import LoggingSender, SmtpSender

        if self.smtp_host:
            return SmtpSender(
                host=self.smtp_host,
                port=self.smtp_port,
                user=self.smtp_user or None,
                password=self.smtp_password or None,
                mail_from=self.mail_from,
            )
        return LoggingSender()
