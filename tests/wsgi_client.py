"""A tiny WSGI test client so product tests need no third-party packages."""

from __future__ import annotations

import io
import json as _json
from urllib.parse import urlencode


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = dict(headers)
        self.body = body

    @property
    def text(self):
        return self.body.decode("utf-8", errors="replace")

    def json(self):
        return _json.loads(self.body.decode("utf-8"))


class Client:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, data=None, files=None, json=None, content_type=None, query=""):
        body = b""
        headers = []
        if json is not None:
            body = _json.dumps(json).encode("utf-8")
            content_type = "application/json"
        elif files:
            body, content_type = _encode_multipart(data or {}, files)
        elif data is not None:
            body = urlencode(data).encode("utf-8")
            content_type = "application/x-www-form-urlencoded"

        environ = {
            "REQUEST_METHOD": method.upper(),
            "PATH_INFO": path,
            "QUERY_STRING": query,
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(body),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "CONTENT_LENGTH": str(len(body)),
        }
        if content_type:
            environ["CONTENT_TYPE"] = content_type

        captured = {}

        def start_response(status, response_headers):
            captured["status"] = int(status.split(" ", 1)[0])
            captured["headers"] = response_headers

        chunks = self.app(environ, start_response)
        response_body = b"".join(chunks)
        return Response(captured["status"], captured["headers"], response_body)

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


def _encode_multipart(fields, files):
    boundary = "----watchtowerboundary"
    delim = b"--" + boundary.encode("ascii")
    out = bytearray()
    for name, value in fields.items():
        out += delim + b"\r\n"
        out += 'Content-Disposition: form-data; name="{}"\r\n\r\n'.format(name).encode("utf-8")
        out += str(value).encode("utf-8") + b"\r\n"
    for name, (filename, content) in files.items():
        if isinstance(content, str):
            content = content.encode("utf-8")
        out += delim + b"\r\n"
        out += 'Content-Disposition: form-data; name="{}"; filename="{}"\r\n'.format(
            name, filename
        ).encode("utf-8")
        out += b"Content-Type: application/octet-stream\r\n\r\n"
        out += content + b"\r\n"
    out += delim + b"--\r\n"
    return bytes(out), "multipart/form-data; boundary={}".format(boundary)
