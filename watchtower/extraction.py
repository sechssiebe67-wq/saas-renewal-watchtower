"""Heuristic extraction of renewal data from invoice / contract text.

The extractor is intentionally dependency-free. It does not try to be a perfect
OCR/NLP pipeline; instead it finds date, amount, notice-period and seat patterns
and attaches a confidence value plus the evidence snippet so a human can verify
the guess before saving.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Optional

from .models import BILLING_PERIODS

MONTHS = {
    "jan": 1, "january": 1, "januar": 1,
    "feb": 2, "february": 2, "februar": 2,
    "mar": 3, "march": 3, "märz": 3, "maerz": 3,
    "apr": 4, "april": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "juni": 6,
    "jul": 7, "july": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "okt": 10, "october": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dec": 12, "dez": 12, "december": 12, "dezember": 12,
}

CURRENCY_SYMBOLS = {
    "€": "EUR",
    "eur": "EUR",
    "$": "USD",
    "usd": "USD",
    "£": "GBP",
    "gbp": "GBP",
    "chf": "CHF",
}

# Keywords that hint at the meaning of a nearby date.
DEADLINE_KEYWORDS = (
    "kündigungsfrist", "kuendigungsfrist", "kündigung", "kuendigung",
    "cancellation", "cancel by", "notice period", "notice date", "termin",
    "frist", "endet am", "gültig bis", "gueltig bis", "valid until",
    "läuft ab", "laeuft ab", "expires", "expiry", "deadline",
)
RENEWAL_KEYWORDS = (
    "verlängerung", "verlaengerung", "verlängert", "verlaengert", "renewal",
    "renews", "renewed", "verlängert sich", "verlaengert sich", "next billing",
    "vertragsbeginn", "start date", "beginnt am",
)
AMOUNT_KEYWORDS = (
    "gesamt", "total", "summe", "betrag", "amount", "rechnungsbetrag",
    "zu zahlen", "zahlbar", "due", "price", "preis",
)

DATE_PATTERNS = [
    # 31.12.2026 or 31.12.26
    re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b"),
    # 2026-12-31
    re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"),
    # 31/12/2026 or 12/31/2026
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b"),
    # December 31, 2026  /  31 December 2026
    re.compile(
        r"\b(\d{1,2})\.?\s+([A-Za-zäöüÄÖÜ]{3,9})\.?\s+(\d{4})\b"
    ),
    re.compile(
        r"\b([A-Za-zäöüÄÖÜ]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b"
    ),
]

AMOUNT_PATTERN = re.compile(
    r"(?:(?P<sym>€|\$|£)\s?(?P<a1>\d{1,3}(?:[.\s,]\d{3})*(?:[.,]\d{1,2})?)"
    r"|(?P<a2>\d{1,3}(?:[.\s,]\d{3})*(?:[.,]\d{1,2})?)\s?(?P<code>EUR|USD|GBP|CHF|eur|usd|gbp|chf))"
)
NOTICE_PATTERN = re.compile(
    r"(\d{1,3})[ \t]*(?:tage|tag|days?|wochen|weeks?)[ \t]*(?:zum|zum ende|vor|before|notice|kündigungsfrist|kuendigungsfrist)?",
    re.IGNORECASE,
)
NOTICE_KEYWORDS = (
    "kündigungsfrist", "kuendigungsfrist", "notice period", "cancellation",
    "frist", "kündigung", "kuendigung",
)
NOTICE_KEYWORD_PATTERN = re.compile(
    r"(kündigungsfrist|kuendigungsfrist|notice period|cancellation period|frist von)[^\d\n]{0,20}?(\d{1,3})",
    re.IGNORECASE,
)
SEATS_PATTERN = re.compile(
    r"(\d{1,6})[ \t]*(?:seats?|lizenzen|licen[cs]es?|users?|benutzer|arbeitsplätze|arbeitsplaetze|mitarbeiter)\b",
    re.IGNORECASE,
)
SEATS_TOTAL_PATTERN = re.compile(
    r"(\d{1,6})[ \t]*(?:seats?|lizenzen|licen[cs]es?|users?|benutzer)[ \t]*(?:total|gesamt|inklusive|including|lizenziert|licensed)",
    re.IGNORECASE,
)
CURRENCY_CODE_PATTERN = re.compile(r"\b(EUR|USD|GBP|CHF)\b", re.IGNORECASE)


@dataclass
class ExtractedField:
    value: object
    confidence: float
    evidence: str = ""

    def to_dict(self) -> dict:
        value = self.value
        if isinstance(value, _dt.date):
            value = value.isoformat()
        return {"value": value, "confidence": round(self.confidence, 3), "evidence": self.evidence}


@dataclass
class ExtractionResult:
    amount: Optional[ExtractedField] = None
    currency: Optional[ExtractedField] = None
    billing_period: Optional[ExtractedField] = None
    renewal_date: Optional[ExtractedField] = None
    deadline: Optional[ExtractedField] = None
    notice_days: Optional[ExtractedField] = None
    seats_total: Optional[ExtractedField] = None
    vendor: Optional[ExtractedField] = None
    text: str = ""
    warnings: list = field(default_factory=list)

    def fields(self) -> list:
        return [
            self.amount, self.currency, self.billing_period, self.renewal_date,
            self.deadline, self.notice_days, self.seats_total, self.vendor,
        ]

    def overall_confidence(self) -> float:
        present = [f.confidence for f in self.fields() if f is not None]
        if not present:
            return 0.0
        return round(sum(present) / len(present), 3)

    def to_dict(self) -> dict:
        return {
            "amount": self.amount.to_dict() if self.amount else None,
            "currency": self.currency.to_dict() if self.currency else None,
            "billing_period": self.billing_period.to_dict() if self.billing_period else None,
            "renewal_date": self.renewal_date.to_dict() if self.renewal_date else None,
            "deadline": self.deadline.to_dict() if self.deadline else None,
            "notice_days": self.notice_days.to_dict() if self.notice_days else None,
            "seats_total": self.seats_total.to_dict() if self.seats_total else None,
            "vendor": self.vendor.to_dict() if self.vendor else None,
            "overall_confidence": self.overall_confidence(),
            "warnings": list(self.warnings),
        }


def _normalize_number(raw: str) -> Optional[float]:
    """Parse a localized number into a float.

    Handles ``1.234,56`` (German), ``1,234.56`` (English) and ``1234.56``.
    """
    raw = raw.strip().replace(" ", "")
    if not raw:
        return None
    has_comma = "," in raw
    has_dot = "." in raw
    if has_comma and has_dot:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif has_comma:
        # comma as decimal separator unless it looks like a thousands group
        if re.fullmatch(r"\d{1,3}(,\d{3})+", raw):
            raw = raw.replace(",", "")
        else:
            raw = raw.replace(",", ".")
    elif has_dot and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        raw = raw.replace(".", "")
    try:
        return float(raw)
    except ValueError:
        return None


def _coerce_year(year: int) -> int:
    if year < 100:
        return 2000 + year
    return year


def _safe_date(year, month, day) -> Optional[_dt.date]:
    try:
        return _dt.date(_coerce_year(int(year)), int(month), int(day))
    except ValueError:
        return None


def _month_number(token: str) -> Optional[int]:
    return MONTHS.get(token.lower().strip("."))


def _parse_date_match(match: re.Match, text: str):
    groups = match.groups()
    if len(groups) == 3:
        a, b, c = groups
        # ISO: year first
        if len(a) == 4:
            return _safe_date(a, b, c)
        # month-name first: "December 31, 2026"
        if a and a.isalpha():
            month = _month_number(a)
            if month:
                return _safe_date(c, month, b)
        # month-name third: "31 December 2026"
        if c and c.isalpha():
            month = _month_number(c)
            if month:
                return _safe_date(b, month, a)
        # numeric: prefer day.month.year (European) when first > 12
        try:
            ia, ib, ic = int(a), int(b), int(c)
        except ValueError:
            return None
        if ia > 12:
            return _safe_date(ic, ib, ia)
        if ib > 12:
            return _safe_date(ic, ia, ib)
        # ambiguous -> assume day.month for dot/slash with European context
        if "." in match.group(0):
            return _safe_date(ic, ib, ia)
        return _safe_date(ic, ia, ib)
    return None


def _find_dates(text: str) -> list:
    found = []
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            date = _parse_date_match(match, text)
            if date is None or date.year < 2000 or date.year > 2100:
                continue
            start = max(0, match.start() - 60)
            end = min(len(text), match.end() + 60)
            found.append(
                (match.start(), date, match.group(0), text[start:end], match.start() - start)
            )
    found.sort(key=lambda item: item[0])
    return found


def _nearest_keyword_distance(context: str, keywords, anchor: int):
    low = context.lower()
    best = None
    for keyword in keywords:
        index = low.find(keyword)
        while index != -1:
            distance = abs(index - anchor)
            if best is None or distance < best:
                best = distance
            index = low.find(keyword, index + 1)
    return best


def _decide(deadline_distance, renewal_distance) -> str:
    if deadline_distance is None and renewal_distance is None:
        return "ambiguous"
    if renewal_distance is None:
        return "deadline"
    if deadline_distance is None:
        return "renewal"
    return "deadline" if deadline_distance <= renewal_distance else "renewal"


def _classify_date(line: str, line_anchor: int, context: str, anchor: int) -> str:
    """Return ``deadline``, ``renewal`` or ``ambiguous`` for a date occurrence.

    The line containing the date is the strongest signal ("Kündigungstermin:
    13.02.2027"). Only when the line carries no keyword do we fall back to the
    surrounding context.
    """
    decision = _decide(
        _nearest_keyword_distance(line, DEADLINE_KEYWORDS, line_anchor),
        _nearest_keyword_distance(line, RENEWAL_KEYWORDS, line_anchor),
    )
    if decision != "ambiguous":
        return decision
    return _decide(
        _nearest_keyword_distance(context, DEADLINE_KEYWORDS, anchor),
        _nearest_keyword_distance(context, RENEWAL_KEYWORDS, anchor),
    )


def _detect_billing_period(text: str) -> Optional[ExtractedField]:
    low = text.lower()
    checks = [
        ("yearly", ("jährlich", "jaehrlich", "per year", "/year", "annual", "yearly", "p.a.")),
        ("quarterly", ("quartal", "quarter", "/quarter")),
        ("monthly", ("monatlich", "per month", "/month", "monthly", "mo.")),
    ]
    for period, keywords in checks:
        for keyword in keywords:
            index = low.find(keyword)
            if index != -1:
                evidence = text[max(0, index - 40):index + len(keyword) + 40].strip()
                return ExtractedField(period, 0.75, evidence)
    return None


def extract_vendor(text: str) -> Optional[ExtractedField]:
    """Best-effort vendor guess from the first meaningful line."""
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) < 3 or len(stripped) > 80:
            continue
        low = stripped.lower()
        excluded = (
            "rechnung", "invoice", "seite", "page", "datum", "date", "gesamtbetrag",
            "betrag", "summe", "total", "kündigung", "kuendigung", "verlängerung",
            "verlaengerung", "lizenzen", "license", "seats", "benutzer", "abrechnung",
        )
        if any(token in low for token in excluded):
            continue
        if re.search(r"\d{4}", stripped):
            continue
        return ExtractedField(stripped, 0.4, stripped)
    return None


def extract(text: str) -> ExtractionResult:
    """Extract structured fields from raw invoice / contract text."""
    result = ExtractionResult(text=text or "")
    if not text or not text.strip():
        result.warnings.append("empty_text")
        return result

    # Amount: prefer a value on a line that also mentions a total/amount keyword.
    best_amount = None
    for match in AMOUNT_PATTERN.finditer(text):
        raw = match.group("a1") or match.group("a2")
        value = _normalize_number(raw)
        if value is None:
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        confidence = 0.7
        if any(keyword in line.lower() for keyword in AMOUNT_KEYWORDS):
            confidence = 0.92
        candidate = ExtractedField(round(value, 2), confidence, line.strip())
        if best_amount is None or candidate.confidence > best_amount.confidence:
            best_amount = candidate
    result.amount = best_amount

    symbol_match = None
    for match in AMOUNT_PATTERN.finditer(text):
        if match.group("code"):
            symbol_match = match.group("code")
        elif match.group("sym"):
            symbol_match = match.group("sym")
        if symbol_match:
            break
    if symbol_match:
        code = CURRENCY_SYMBOLS.get(symbol_match.lower())
        if code:
            result.currency = ExtractedField(code, 0.85, symbol_match)
    if result.currency is None:
        code_match = CURRENCY_CODE_PATTERN.search(text)
        if code_match:
            result.currency = ExtractedField(code_match.group(1).upper(), 0.6, code_match.group(0))

    result.billing_period = _detect_billing_period(text)

    # Dates: classify by the nearest keyword. Prefer keyword-anchored dates over
    # an ambiguous first date, which often is only the invoice date.
    deadline_candidate = None
    renewal_candidate = None
    ambiguous_candidate = None
    for start, date, token, context, anchor in _find_dates(text):
        line_start = text.rfind("\n", 0, start) + 1
        line_end = text.find("\n", start)
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end]
        role = _classify_date(line, start - line_start, context, anchor)
        if role == "deadline":
            if deadline_candidate is None:
                deadline_candidate = ExtractedField(date, 0.9, context.strip())
        elif role == "renewal":
            if renewal_candidate is None:
                renewal_candidate = ExtractedField(date, 0.9, context.strip())
        elif ambiguous_candidate is None:
            ambiguous_candidate = ExtractedField(date, 0.45, context.strip())
    result.deadline = deadline_candidate or ambiguous_candidate
    result.renewal_date = renewal_candidate

    # Only use the broad "N Tage" pattern when a notice keyword is present, to
    # avoid mistaking payment terms ("zahlbar in 30 Tagen") for a notice period.
    notice_match = NOTICE_KEYWORD_PATTERN.search(text)
    if notice_match is None and any(keyword in text.lower() for keyword in NOTICE_KEYWORDS):
        notice_match = NOTICE_PATTERN.search(text)
    if notice_match:
        groups = [g for g in notice_match.groups() if g and g.isdigit()]
        if groups:
            result.notice_days = ExtractedField(int(groups[-1]), 0.8, notice_match.group(0).strip())

    seats_match = SEATS_TOTAL_PATTERN.search(text) or SEATS_PATTERN.search(text)
    if seats_match:
        value = int(seats_match.group(1))
        confidence = 0.8 if SEATS_TOTAL_PATTERN.search(text) else 0.6
        result.seats_total = ExtractedField(value, confidence, seats_match.group(0).strip())

    result.vendor = extract_vendor(text)

    if not any(f is not None for f in result.fields()):
        result.warnings.append("no_fields_detected")
    return result
