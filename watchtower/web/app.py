"""Minimal dependency-free WSGI application and router."""

from __future__ import annotations

import json
import logging
import re
import traceback
from urllib.parse import parse_qs

from . import render

LOGGER = logging.getLogger("watchtower.web")

REASON = {
    200: "OK",
    303: "See Other",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
    500: "Internal Server Error",
}

_SUBSCRIPTION_RE = re.compile(r"^/subscriptions/(\d+)$")
_SEATS_RE = re.compile(r"^/subscriptions/(\d+)/seats$")
_DELETE_RE = re.compile(r"^/subscriptions/(\d+)/delete$")


class Request:
    def __init__(self, environ):
        self.environ = environ
        self.method = environ.get("REQUEST_METHOD", "GET").upper()
        self.path = environ.get("PATH_INFO", "/") or "/"
        self.query = parse_qs(environ.get("QUERY_STRING", ""))
        self._form = None
        self._files = None

    @property
    def form(self):
        if self._form is None:
            self._parse_body()
        return self._form

    @property
    def files(self):
        if self._files is None:
            self._parse_body()
        return self._files

    def _parse_body(self):
        self._form = {}
        self._files = {}
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return
        body = self.environ.get("wsgi.input")
        body = body.read(length) if body is not None else b""
        content_type = self.environ.get("CONTENT_TYPE", "")
        if content_type.startswith("application/json"):
            try:
                data = json.loads(body.decode("utf-8") or "{}")
                if isinstance(data, dict):
                    self._form = {key: str(value) for key, value in data.items()}
            except (ValueError, UnicodeDecodeError):
                pass
        elif content_type.startswith("multipart/form-data"):
            boundary = _boundary(content_type)
            if boundary:
                self._form, self._files = _parse_multipart(body, boundary)
        else:
            parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
            self._form = {key: values[0] for key, values in parsed.items()}


def _boundary(content_type: str):
    match = re.search(r'boundary="?([^";]+)"?', content_type)
    return match.group(1).encode("utf-8") if match else None


def _disposition_param(disposition: str, name: str):
    match = re.search(r'{0}="([^"]*)"'.format(re.escape(name)), disposition)
    return match.group(1) if match else None


def _parse_multipart(body: bytes, boundary: bytes):
    fields = {}
    files = {}
    delimiter = b"--" + boundary
    for section in body.split(delimiter):
        section = section.strip(b"\r\n")
        if not section or section == b"--":
            continue
        header_blob, _, content = section.partition(b"\r\n\r\n")
        content = content.rstrip(b"\r\n")
        headers = {}
        for line in header_blob.split(b"\r\n"):
            if b":" in line:
                key, _, value = line.partition(b":")
                headers[key.strip().lower()] = value.strip()
        disposition = headers.get(b"content-disposition", b"").decode("utf-8", "replace")
        field_name = _disposition_param(disposition, "name")
        filename = _disposition_param(disposition, "filename")
        if field_name is None:
            continue
        if filename is not None:
            files[field_name] = (filename, content)
        else:
            fields[field_name] = content.decode("utf-8", "replace")
    return fields, files


class WatchtowerApp:
    def __init__(self, service):
        self.service = service

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            status, headers, body = self.dispatch(request)
        except Exception:  # pragma: no cover - defensive
            LOGGER.error("Unhandled error:\n%s", traceback.format_exc())
            body = render.error_page(500, "Interner Fehler.")
            headers = [("Content-Type", "text/html; charset=utf-8")]
            status = 500
        header_map = {}
        for key, value in headers:
            header_map[key] = value
        header_map.setdefault("Content-Type", "text/html; charset=utf-8")
        header_map["Content-Length"] = str(len(body))
        header_map["X-Content-Type-Options"] = "nosniff"
        header_map["Cache-Control"] = "no-store"
        start_response(
            "{} {}".format(status, REASON.get(status, "")),
            list(header_map.items()),
        )
        return [body]

    # -- routing ---------------------------------------------------------
    def dispatch(self, request: Request):
        path = request.path
        method = request.method

        if path == "/healthz":
            return self._healthz()
        if path == "/static/app.css":
            return self._css()
        if path == "/api/subscriptions":
            return self._api_subscriptions()
        if path == "/api/summary":
            return self._api_summary()
        if path == "/":
            return self._dashboard()
        if path == "/subscriptions":
            if method == "POST":
                return self._create_subscription(request)
            return self._subscriptions()
        if path == "/subscriptions/new":
            return self._new_subscription()
        if path == "/upload":
            if method == "POST":
                return self._handle_upload(request)
            return self._page(render.upload_page())
        if path == "/extract":
            if method == "POST":
                return self._handle_upload(request)
            return self._page(render.upload_page())
        if path == "/reminders":
            return self._reminders()
        if path == "/reminders/dispatch":
            if method == "POST":
                return self._dispatch_reminders(request)
            return self._error(405, "Nur POST erlaubt.")
        if path == "/summary":
            return self._summary(request)

        match = _SUBSCRIPTION_RE.match(path)
        if match:
            if method == "POST":
                return self._update_subscription(request, int(match.group(1)))
            return self._subscription_detail(int(match.group(1)))
        match = _SEATS_RE.match(path)
        if match and method == "POST":
            return self._update_seats(request, int(match.group(1)))
        match = _DELETE_RE.match(path)
        if match and method == "POST":
            return self._delete_subscription(int(match.group(1)))

        return self._error(404, "Seite nicht gefunden.")

    # -- handlers --------------------------------------------------------
    def _page(self, body: bytes, status: int = 200):
        return status, [("Content-Type", "text/html; charset=utf-8")], body

    def _error(self, status: int, message: str):
        return self._page(render.error_page(status, message), status)

    def _redirect(self, location: str):
        return 303, [("Location", location)], b""

    def _healthz(self):
        try:
            count = self.service.storage.count_subscriptions()
            payload = {"status": "ok", "subscriptions": count}
            status = 200
        except Exception as exc:  # pragma: no cover - defensive
            payload = {"status": "error", "detail": str(exc)}
            status = 503
        body = json.dumps(payload).encode("utf-8")
        return status, [("Content-Type", "application/json")], body

    def _css(self):
        return 200, [("Content-Type", "text/css; charset=utf-8")], render.CSS.encode("utf-8")

    def _api_subscriptions(self):
        rows = self.service.list_enriched()
        payload = [
            dict(row["subscription"].to_dict(), **{
                "days_until_deadline": row["days_until"],
                "utilization_percent": row["utilization_percent"],
                "annual_cost": row["annual_cost"],
                "recommendation": row["recommendation"].to_dict(),
            })
            for row in rows
        ]
        body = json.dumps({"subscriptions": payload}).encode("utf-8")
        return 200, [("Content-Type", "application/json")], body

    def _api_summary(self):
        summary = self.service.weekly_summary()
        return 200, [("Content-Type", "application/json")], json.dumps(summary.to_dict()).encode("utf-8")

    def _dashboard(self):
        return self._page(render.dashboard_page(self.service.dashboard()))

    def _subscriptions(self):
        return self._page(render.subscriptions_page(self.service.list_enriched()))

    def _new_subscription(self):
        return self._page(render.new_subscription_page())

    def _create_subscription(self, request: Request):
        subscription = self.service.subscription_from_form(request.form)
        if not subscription.name:
            return self._error(400, "Abo-Name ist erforderlich.")
        subscription_id = self.service.save_subscription(subscription)
        return self._redirect("/subscriptions/{}".format(subscription_id))

    def _update_subscription(self, request: Request, subscription_id: int):
        existing = self.service.storage.get_subscription(subscription_id)
        if existing is None:
            return self._error(404, "Abo nicht gefunden.")
        subscription = self.service.subscription_from_form(request.form)
        subscription.id = subscription_id
        self.service.save_subscription(subscription)
        return self._redirect("/subscriptions/{}".format(subscription_id))

    def _subscription_detail(self, subscription_id: int):
        row = self.service.get_enriched(subscription_id)
        if row is None:
            return self._error(404, "Abo nicht gefunden.")
        events = self.service.storage.list_events(subscription_id)
        sent = [
            reminder for reminder in self.service.storage.list_sent_reminders(limit=200)
            if reminder.subscription_id == subscription_id
        ]
        return self._page(render.subscription_detail_page(row, events, sent))

    def _update_seats(self, request: Request, subscription_id: int):
        if self.service.storage.get_subscription(subscription_id) is None:
            return self._error(404, "Abo nicht gefunden.")
        try:
            self.service.update_seats(
                subscription_id,
                request.form.get("seats_used"),
                request.form.get("seats_total"),
            )
        except ValueError:
            return self._error(400, "Seats müssen Zahlen sein.")
        return self._redirect("/subscriptions/{}".format(subscription_id))

    def _delete_subscription(self, subscription_id: int):
        if self.service.storage.get_subscription(subscription_id) is None:
            return self._error(404, "Abo nicht gefunden.")
        self.service.delete_subscription(subscription_id)
        return self._redirect("/")

    def _handle_upload(self, request: Request):
        text = request.form.get("text", "")
        filename = ""
        if "file" in request.files:
            filename, data = request.files["file"]
            if filename and data:
                extraction = self.service.capture_file(filename, data)
            else:
                extraction = self.service.capture(text, source="paste")
        else:
            extraction = self.service.capture(text, source="paste")
        draft = self.service.draft_from_extraction(extraction)
        return self._page(
            render.extraction_preview_page(draft, extraction, filename, extraction.text)
        )

    def _reminders(self):
        today = self.service.today()
        pending = self.service.pending_reminders(today)
        sent = self.service.storage.list_sent_reminders()
        return self._page(render.reminders_page(pending, sent, self.service.mail_to))

    def _dispatch_reminders(self, request: Request):
        sent = self.service.dispatch_reminders()
        LOGGER.info("Dispatched %s reminders", len(sent))
        return self._redirect("/reminders")

    def _summary(self, request: Request):
        horizon = self.service.review_horizon_days
        if "horizon" in request.query:
            try:
                horizon = int(request.query["horizon"][0])
            except ValueError:
                pass
        summary = self.service.weekly_summary(horizon_days=horizon)
        as_text = request.query.get("format", [""])[0] == "txt"
        if request.query.get("format", [""])[0] == "json":
            return 200, [("Content-Type", "application/json")], json.dumps(summary.to_dict()).encode("utf-8")
        return self._page(render.summary_page(summary, as_text=as_text))


def create_app(service):
    """Return a WSGI application for the given service."""
    return WatchtowerApp(service)
