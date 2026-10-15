"""Dependency-free best-effort text recovery from PDF files.

Many invoice PDFs use FlateDecode (``zlib``) compressed content streams. This
module decompresses those streams and collects the strings inside text-showing
operators (``(...) Tj`` and ``[...] TJ``). It is not a complete PDF parser; when
it cannot recover anything the caller should fall back to manual entry.
"""

from __future__ import annotations

import re
import zlib

_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
_LITERAL_STRING_RE = re.compile(rb"\((?:\\.|[^\\()])*\)")
_HEX_STRING_RE = re.compile(rb"<([0-9A-Fa-f\s]+)>")

_ESCAPES = {
    b"n": b"\n",
    b"r": b"\r",
    b"t": b"\t",
    b"b": b"\b",
    b"f": b"\f",
    b"(": b"(",
    b")": b")",
    b"\\": b"\\",
}


def _decode_literal(raw: bytes) -> str:
    inner = raw[1:-1]
    out = bytearray()
    i = 0
    while i < len(inner):
        char = inner[i:i + 1]
        if char == b"\\" and i + 1 < len(inner):
            nxt = inner[i + 1:i + 2]
            if nxt in _ESCAPES:
                out += _ESCAPES[nxt]
                i += 2
                continue
            octal = re.match(rb"[0-7]{1,3}", inner[i + 1:])
            if octal:
                out.append(int(octal.group(0), 8) & 0xFF)
                i += 1 + len(octal.group(0))
                continue
            out += nxt
            i += 2
            continue
        out += char
        i += 1
    try:
        return out.decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - defensive
        return out.decode("latin-1", errors="replace")


def _decode_hex(raw: bytes) -> str:
    hexdigits = re.sub(rb"\s+", b"", raw)
    if len(hexdigits) % 2:
        hexdigits += b"0"
    try:
        data = bytes.fromhex(hexdigits.decode("ascii"))
    except (ValueError, UnicodeDecodeError):
        return ""
    return data.decode("utf-8", errors="replace")


def _extract_from_stream(stream: bytes) -> str:
    parts = []
    for match in _LITERAL_STRING_RE.finditer(stream):
        parts.append(_decode_literal(match.group(0)))
    for match in _HEX_STRING_RE.finditer(stream):
        decoded = _decode_hex(match.group(1))
        if decoded:
            parts.append(decoded)
    return " ".join(part for part in parts if part.strip())


def extract_pdf_text(data: bytes) -> str:
    if not data:
        return ""
    streams = _STREAM_RE.findall(data)
    if not streams:
        # Some producers omit the newline after the keyword.
        streams = re.findall(rb"stream\r?(.*?)endstream", data, re.DOTALL)
    chunks = []
    for raw in streams:
        content = None
        try:
            content = zlib.decompress(raw)
        except zlib.error:
            try:
                content = zlib.decompress(raw, -15)
            except zlib.error:
                content = raw
        text = _extract_from_stream(content)
        if text.strip():
            chunks.append(text)
    return "\n".join(chunks)


def extract_text(filename: str, data: bytes) -> str:
    """Recover text from a supported upload.

    Plain text formats are decoded directly; PDFs go through the recovery above.
    """
    lower = (filename or "").lower()
    if lower.endswith(".pdf") or data[:5] == b"%PDF-":
        return extract_pdf_text(data)
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
