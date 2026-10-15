"""HTTP server entrypoint and optional reminder scheduler."""

from __future__ import annotations

import logging
import threading
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from .config import Config
from .service import WatchtowerService
from .storage import Storage
from .web.app import create_app

LOGGER = logging.getLogger("watchtower")


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True
    allow_reuse_address = True


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        LOGGER.debug("%s - %s", self.address_string(), format % args)


def build_service(config: Config) -> WatchtowerService:
    storage = Storage(config.db_path)
    sender = config.build_sender()
    return WatchtowerService(
        storage,
        sender=sender,
        mail_to=config.mail_to,
        review_horizon_days=config.review_horizon_days,
    )


class Scheduler(threading.Thread):
    """Periodically dispatches due reminders without human intervention."""

    def __init__(self, service: WatchtowerService, interval: int):
        super().__init__(name="watchtower-scheduler", daemon=True)
        self.service = service
        self.interval = max(30, int(interval))
        self._stop = threading.Event()

    def run(self):
        LOGGER.info("Reminder scheduler started (interval=%ss)", self.interval)
        while not self._stop.is_set():
            try:
                sent = self.service.dispatch_reminders()
                if sent:
                    LOGGER.info("Scheduler dispatched %s reminders", len(sent))
            except Exception:  # pragma: no cover - keep scheduler alive
                LOGGER.exception("Scheduler dispatch failed")
            self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()


def run(config: Config = None) -> None:
    config = config or Config.from_env()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    service = build_service(config)
    app = create_app(service)
    scheduler = None
    if config.scheduler_enabled:
        scheduler = Scheduler(service, config.scheduler_interval)
        scheduler.start()
    httpd = make_server(
        config.host,
        config.port,
        app,
        server_class=ThreadingWSGIServer,
        handler_class=QuietRequestHandler,
    )
    LOGGER.info("SaaS Renewal Watchtower listening on %s:%s", config.host, config.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down")
    finally:
        if scheduler is not None:
            scheduler.stop()
        service.storage.close()


if __name__ == "__main__":  # pragma: no cover
    run()
