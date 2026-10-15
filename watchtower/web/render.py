"""HTML rendering helpers.

No template engine is used to keep the application dependency-free. All dynamic
values pass through :func:`esc`.
"""

from __future__ import annotations

import datetime as _dt
import html
from typing import Optional

CSS = """
:root { --bg:#0f172a; --panel:#1e293b; --muted:#94a3b8; --fg:#e2e8f0;
  --accent:#38bdf8; --ok:#4ade80; --warn:#fbbf24; --bad:#f87171; --line:#334155; }
* { box-sizing: border-box; }
body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  background:var(--bg); color:var(--fg); line-height:1.5; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
header.top { background:var(--panel); border-bottom:1px solid var(--line); }
.wrap { max-width:1100px; margin:0 auto; padding:16px 20px; }
nav a { margin-right:18px; font-weight:600; }
nav a.active { color:#fff; border-bottom:2px solid var(--accent); padding-bottom:2px; }
h1 { font-size:1.5rem; margin:18px 0 4px; }
h2 { font-size:1.1rem; margin:24px 0 8px; }
.sub { color:var(--muted); margin-top:0; }
.cards { display:flex; flex-wrap:wrap; gap:12px; margin:16px 0; }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:12px 16px; min-width:150px; flex:1; }
.card .n { font-size:1.6rem; font-weight:700; }
.card .l { color:var(--muted); font-size:.85rem; }
table { width:100%; border-collapse:collapse; background:var(--panel);
  border:1px solid var(--line); border-radius:10px; overflow:hidden; }
th, td { text-align:left; padding:9px 12px; border-bottom:1px solid var(--line);
  vertical-align:top; }
th { background:#16213e; font-size:.8rem; text-transform:uppercase; color:var(--muted); }
tr:last-child td { border-bottom:none; }
.badge { display:inline-block; padding:2px 8px; border-radius:999px; font-size:.75rem;
  font-weight:700; }
.b-overdue,.b-urgent { background:#7f1d1d; color:#fecaca; }
.b-soon { background:#78350f; color:#fde68a; }
.b-upcoming { background:#1e3a8a; color:#bfdbfe; }
.b-none,.b-keep { background:#14532d; color:#bbf7d0; }
.b-cancel { background:#7f1d1d; color:#fecaca; }
.b-shrink { background:#78350f; color:#fde68a; }
.b-negotiate { background:#3730a3; color:#c7d2fe; }
.b-review { background:#164e63; color:#a5f3fc; }
.bar { background:#0b1220; border-radius:6px; height:8px; width:110px;
  display:inline-block; overflow:hidden; vertical-align:middle; }
.bar > span { display:block; height:100%; background:var(--ok); }
.bar.low > span { background:var(--bad); }
.bar.mid > span { background:var(--warn); }
form.stack { background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:18px; max-width:640px; }
label { display:block; margin:10px 0 3px; font-size:.85rem; color:var(--muted); }
input, select, textarea { width:100%; padding:8px 10px; border-radius:8px;
  border:1px solid var(--line); background:#0b1220; color:var(--fg); }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:0 16px; }
button, .btn { background:var(--accent); color:#04121f; border:none; padding:9px 16px;
  border-radius:8px; font-weight:700; cursor:pointer; display:inline-block; }
button.ghost, .btn.ghost { background:transparent; color:var(--accent);
  border:1px solid var(--accent); }
button.danger { background:#7f1d1d; color:#fecaca; }
.conf { color:var(--muted); font-size:.78rem; }
.conf.high { color:var(--ok); }
.conf.low { color:var(--warn); }
.muted { color:var(--muted); }
pre { background:#0b1220; border:1px solid var(--line); border-radius:8px;
  padding:12px; overflow:auto; white-space:pre-wrap; }
.flash { background:#14532d; border:1px solid #166534; padding:10px 14px;
  border-radius:8px; margin:12px 0; }
footer { color:var(--muted); font-size:.8rem; padding:24px 0 40px; }
@media (max-width:700px) { .grid2 { grid-template-columns:1fr; } }
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def money(amount, currency="EUR") -> str:
    try:
        return "{:,.2f} {}".format(float(amount or 0), esc(currency))
    except (TypeError, ValueError):
        return "0.00 {}".format(esc(currency))


def layout(title: str, body: str, active: str = "") -> bytes:
    def nav(label, href, key):
        cls = ' class="active"' if key == active else ""
        return '<a href="{}"{}>{}</a>'.format(href, cls, esc(label))

    document = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} – SaaS Renewal Watchtower</title>
<link rel="stylesheet" href="/static/app.css">
</head>
<body>
<header class="top"><div class="wrap">
<nav>
{nav}
</nav>
</div></header>
<main class="wrap">
{body}
<footer>SaaS Renewal Watchtower · Fristen aus Rechnungen, Empfehlung statt Liste.</footer>
</main>
</body>
</html>""".format(
        title=esc(title),
        nav="".join([
            nav("Dashboard", "/", "dashboard"),
            nav("Abos", "/subscriptions", "subscriptions"),
            nav("Hochladen", "/upload", "upload"),
            nav("Erinnerungen", "/reminders", "reminders"),
            nav("Woche", "/summary", "summary"),
        ]),
        body=body,
    )
    return document.encode("utf-8")


def _urgency_badge(recommendation) -> str:
    return '<span class="badge b-{u}">{label}</span>'.format(
        u=esc(recommendation.urgency), label=esc(recommendation.urgency_label)
    )


def _action_badge(recommendation) -> str:
    return '<span class="badge b-{a}">{label}</span>'.format(
        a=esc(recommendation.action), label=esc(recommendation.label)
    )


def _util_bar(percent: Optional[float], unused: Optional[int]) -> str:
    if percent is None:
        return '<span class="muted">n/a</span>'
    cls = "low" if percent < 50 else ("mid" if percent < 80 else "")
    return (
        '<div class="bar {cls}"><span style="width:{w:.0f}%"></span></div> '
        '<span class="conf">{p:.0f}%</span>'.format(cls=cls, w=percent, p=percent)
        + (' <span class="muted">({} frei)</span>'.format(unused) if unused else "")
    )


def dashboard_page(data: dict) -> bytes:
    kpis = data["kpis"]
    rows = data["rows"]
    summary = data["summary"]

    cards = """
<div class="cards">
  <div class="card"><div class="n">{total}</div><div class="l">Abos überwacht</div></div>
  <div class="card"><div class="n">{annual}</div><div class="l">Kosten / Jahr</div></div>
  <div class="card"><div class="n">{savings}</div><div class="l">Einsparpotenzial / Jahr</div></div>
  <div class="card"><div class="n">{overdue}</div><div class="l">Überfällige Fristen</div></div>
  <div class="card"><div class="n">{soon}</div><div class="l">Fristen ≤ 30 Tage</div></div>
</div>""".format(
        total=kpis["total"],
        annual=money(kpis["annual_cost"]),
        savings=money(kpis["potential_savings_annual"]),
        overdue=kpis["overdue"],
        soon=kpis["due_soon"],
    )

    if rows:
        table_rows = "".join(_subscription_row(row) for row in rows)
        table = """
<table>
<thead><tr><th>Abo</th><th>Frist</th><th>Tage</th><th>Betrag</th>
<th>Auslastung</th><th>Empfehlung</th></tr></thead>
<tbody>{rows}</tbody>
</table>""".format(rows=table_rows)
    else:
        table = (
            '<p class="muted">Noch keine Abos erfasst. '
            '<a href="/subscriptions/new">Manuell anlegen</a> oder '
            '<a href="/upload">Rechnung hochladen</a>.</p>'
        )

    summary_html = _summary_block(summary)
    body = """
<h1>Watchtower</h1>
<p class="sub">Fristen aus Rechnungen und Verträgen, mit konkreter Handlungsempfehlung.</p>
{cards}
<h2>Fristen nach Dringlichkeit</h2>
{summary_html}
<h2>Alle Abos</h2>
<p><a class="btn" href="/subscriptions/new">+ Abo erfassen</a>
<a class="btn ghost" href="/upload">Rechnung hochladen</a></p>
{table}
""".format(cards=cards, summary_html=summary_html, table=table)
    return layout("Dashboard", body, "dashboard")


def _subscription_row(row: dict) -> str:
    sub = row["subscription"]
    rec = row["recommendation"]
    days = row["days_until"]
    days_text = "–" if days is None else ("{}".format(days) if days >= 0 else "{} (überfällig)".format(days))
    return """
<tr>
  <td><a href="/subscriptions/{id}">{name}</a><div class="muted">{vendor}</div></td>
  <td>{deadline}</td>
  <td>{days} {urgency}</td>
  <td>{amount}</td>
  <td>{util}</td>
  <td>{action}<div class="conf">{reason}</div>
      <div class="muted">Potenzial: {savings}</div></td>
</tr>""".format(
        id=esc(sub.id),
        name=esc(sub.name or "(ohne Namen)"),
        vendor=esc(sub.vendor),
        deadline=esc(sub.deadline.isoformat() if sub.deadline else "–"),
        days=esc(days_text),
        urgency=_urgency_badge(rec),
        amount=money(sub.amount, sub.currency),
        util=_util_bar(row["utilization_percent"], row["unused_seats"]),
        action=_action_badge(rec),
        reason=esc(rec.reason),
        savings=money(rec.potential_savings, sub.currency),
    )


def _summary_block(summary) -> str:
    if not summary.items:
        return '<p class="muted">Keine Fristen in den nächsten {} Tagen.</p>'.format(
            summary.horizon_days
        )
    items = "".join(
        """
<tr><td>{name}</td><td>{deadline}</td><td>{days}</td>
<td>{action}</td><td>{savings}</td></tr>""".format(
            name=esc(item["name"]),
            deadline=esc(item["deadline"]),
            days=esc(item["days_until"]),
            action=esc(item["action_label"]),
            savings=money(item["potential_savings"], item["currency"]),
        )
        for item in summary.items
    )
    html_block = """
<table>
<thead><tr><th>Abo</th><th>Frist</th><th>Tage</th><th>Empfehlung</th>
<th>Potenzial</th></tr></thead>
<tbody>{items}</tbody>
</table>
<p class="sub">Gesamtes Einsparpotenzial im Zeitraum: <strong>{total}</strong>
({overdue} überfällig)</p>""".format(
        items=items,
        total=money(summary.total_potential_savings),
        overdue=summary.overdue_count,
    )
    return html_block


def _subscription_form(defaults: dict, extraction_summary: str = "") -> str:
    def val(key, fallback=""):
        value = defaults.get(key, fallback)
        return "" if value is None else value

    return """
{extraction}
<form class="stack" method="post" action="/subscriptions">
  <input type="hidden" name="source" value="{source}">
  <label for="name">Abo-Name</label>
  <input id="name" name="name" required value="{name}">
  <div class="grid2">
    <div><label for="vendor">Anbieter</label>
      <input id="vendor" name="vendor" value="{vendor}"></div>
    <div><label for="owner">Verantwortlich</label>
      <input id="owner" name="owner" value="{owner}"></div>
  </div>
  <div class="grid2">
    <div><label for="amount">Betrag</label>
      <input id="amount" name="amount" inputmode="decimal" value="{amount}"></div>
    <div><label for="currency">Währung</label>
      <input id="currency" name="currency" value="{currency}"></div>
  </div>
  <div class="grid2">
    <div><label for="billing_period">Abrechnung</label>
      <select id="billing_period" name="billing_period">
        {billing_options}
      </select></div>
    <div><label for="notice_days">Kündigungsfrist (Tage)</label>
      <input id="notice_days" name="notice_days" inputmode="numeric" value="{notice_days}"></div>
  </div>
  <div class="grid2">
    <div><label for="deadline">Kündigungstermin (YYYY-MM-DD)</label>
      <input id="deadline" name="deadline" placeholder="2026-12-31" value="{deadline}"></div>
    <div><label for="renewal_date">Verlängerungsdatum (optional)</label>
      <input id="renewal_date" name="renewal_date" placeholder="2027-01-01" value="{renewal_date}"></div>
  </div>
  <div class="grid2">
    <div><label for="seats_total">Seats gebucht</label>
      <input id="seats_total" name="seats_total" inputmode="numeric" value="{seats_total}"></div>
    <div><label for="seats_used">Seats genutzt</label>
      <input id="seats_used" name="seats_used" inputmode="numeric" value="{seats_used}"></div>
  </div>
  <label for="previous_amount">Vorheriger Betrag (optional, für Preiserkennung)</label>
  <input id="previous_amount" name="previous_amount" value="{previous_amount}">
  <label for="notes">Notizen</label>
  <textarea id="notes" name="notes" rows="2">{notes}</textarea>
  <p><button type="submit">Speichern</button>
  <a class="btn ghost" href="/">Abbrechen</a></p>
</form>""".format(
        extraction=extraction_summary,
        source=esc(val("source", "manual")),
        name=esc(val("name")),
        vendor=esc(val("vendor")),
        owner=esc(val("owner")),
        amount=esc(val("amount")),
        currency=esc(val("currency", "EUR")),
        billing_options=_billing_options(val("billing_period", "monthly")),
        notice_days=esc(val("notice_days")),
        deadline=esc(val("deadline")),
        renewal_date=esc(val("renewal_date")),
        seats_total=esc(val("seats_total")),
        seats_used=esc(val("seats_used")),
        previous_amount=esc(val("previous_amount")),
        notes=esc(val("notes")),
    )


def _billing_options(selected: str) -> str:
    options = [
        ("monthly", "monatlich"),
        ("quarterly", "quartalsweise"),
        ("yearly", "jährlich"),
        ("one_time", "einmalig"),
    ]
    return "".join(
        '<option value="{v}"{sel}>{label}</option>'.format(
            v=v, label=label, sel=" selected" if v == selected else ""
        )
        for v, label in options
    )


def new_subscription_page(defaults=None) -> bytes:
    body = """
<h1>Neues Abo erfassen</h1>
<p class="sub">Betrag, Frist und Seats manuell eintragen.</p>
{form}""".format(form=_subscription_form(defaults or {}))
    return layout("Neues Abo", body, "subscriptions")


def extraction_preview_page(draft: dict, extraction, filename: str, raw_text: str) -> bytes:
    confidence = extraction.overall_confidence()
    conf_class = "high" if confidence >= 0.75 else ("low" if confidence < 0.5 else "")
    warnings = ""
    if extraction.warnings:
        warnings = '<div class="flash">Hinweise: {}</div>'.format(
            esc(", ".join(extraction.warnings))
        )
    field_rows = _extraction_fields(extraction)
    extraction_summary = """
{warnings}
<h2>Extraktion ({file})</h2>
<p class="conf {conf_class}">Gesamt-Konfidenz: {confidence:.0%}</p>
<table>
<thead><tr><th>Feld</th><th>Wert</th><th>Konfidenz</th><th>Beleg</th></tr></thead>
<tbody>{fields}</tbody>
</table>
<p class="muted">Erkannte Werte unten prüfen und korrigieren, dann speichern.</p>
<details><summary>Erkannter Text</summary><pre>{text}</pre></details>
""".format(
        warnings=warnings,
        file=esc(filename or "Text"),
        conf_class=conf_class,
        confidence=confidence,
        fields=field_rows,
        text=esc(raw_text[:6000]),
    )
    body = """
<h1>Extraktion prüfen</h1>
{form}""".format(form=_subscription_form(draft, extraction_summary))
    return layout("Extraktion prüfen", body, "upload")


def _extraction_fields(extraction) -> str:
    labels = [
        ("Betrag", extraction.amount),
        ("Währung", extraction.currency),
        ("Abrechnung", extraction.billing_period),
        ("Kündigungstermin", extraction.deadline),
        ("Verlängerung", extraction.renewal_date),
        ("Kündigungsfrist", extraction.notice_days),
        ("Seats", extraction.seats_total),
        ("Anbieter", extraction.vendor),
    ]
    rows = []
    for label, field in labels:
        if field is None:
            rows.append(
                '<tr><td>{}</td><td class="muted">nicht erkannt</td>'
                '<td class="muted">–</td><td></td></tr>'.format(esc(label))
            )
            continue
        value = field.value
        if isinstance(value, _dt.date):
            value = value.isoformat()
        conf_class = "high" if field.confidence >= 0.75 else ("low" if field.confidence < 0.5 else "")
        rows.append(
            '<tr><td>{label}</td><td>{value}</td>'
            '<td class="conf {cls}">{conf:.0%}</td>'
            '<td class="conf">{evidence}</td></tr>'.format(
                label=esc(label),
                value=esc(value),
                cls=conf_class,
                conf=field.confidence,
                evidence=esc((field.evidence or "")[:120]),
            )
        )
    return "".join(rows)


def upload_page(message: str = "") -> bytes:
    flash = '<div class="flash">{}</div>'.format(esc(message)) if message else ""
    body = """
<h1>Rechnung oder Vertrag hochladen</h1>
<p class="sub">PDF, Text oder eingefügter Inhalt. Die Daten werden nur lokal
verarbeitet und in dieser Instanz gespeichert.</p>
{flash}
<form class="stack" method="post" action="/upload" enctype="multipart/form-data">
  <label for="file">Datei (.pdf, .txt, .md)</label>
  <input id="file" type="file" name="file">
  <label for="text">… oder Text einfügen</label>
  <textarea id="text" name="text" rows="6" placeholder="Rechnungstext hier einfügen"></textarea>
  <p><button type="submit">Auslesen</button></p>
</form>""".format(flash=flash)
    return layout("Hochladen", body, "upload")


def subscription_detail_page(row: dict, events: list, sent: list) -> bytes:
    sub = row["subscription"]
    rec = row["recommendation"]
    events_html = "".join(
        "<li><span class='muted'>{}</span> {} {}</li>".format(
            esc(event.created_at), esc(event.kind), esc(event.detail)
        )
        for event in events
    ) or "<li class='muted'>keine Ereignisse</li>"
    sent_html = "".join(
        "<li>{} – {} an {}</li>".format(
            esc(reminder.sent_at), esc(reminder.subject), esc(reminder.recipient or "log")
        )
        for reminder in sent
    ) or "<li class='muted'>noch keine Erinnerung versendet</li>"
    body = """
<h1>{name}</h1>
<p class="sub">{vendor} · <a href="/subscriptions">zur Liste</a></p>
<div class="cards">
  <div class="card"><div class="n">{amount}</div><div class="l">Betrag / Periode</div></div>
  <div class="card"><div class="n">{annual}</div><div class="l">pro Jahr</div></div>
  <div class="card"><div class="n">{days}</div><div class="l">Tage bis Frist</div></div>
  <div class="card"><div class="n">{action}</div><div class="l">Empfehlung</div></div>
</div>
<table>
<tbody>
<tr><th>Frist</th><td>{deadline}</td><th>Verlängerung</th><td>{renewal}</td></tr>
<tr><th>Kündigungsfrist</th><td>{notice} Tage</td><th>Auslastung</th><td>{util}</td></tr>
<tr><th>Begründung</th><td colspan="3">{reason}</td></tr>
<tr><th>Einsparpotenzial</th><td colspan="3">{savings}</td></tr>
<tr><th>Konfidenz der Extraktion</th><td colspan="3">{confidence}</td></tr>
<tr><th>Quelle</th><td colspan="3">{source}</td></tr>
</tbody>
</table>

<h2>Seats aktualisieren</h2>
<form class="stack" method="post" action="/subscriptions/{id}/seats">
  <div class="grid2">
    <div><label for="seats_used">Genutzte Seats</label>
      <input id="seats_used" name="seats_used" inputmode="numeric" value="{seats_used}"></div>
    <div><label for="seats_total">Gebuchte Seats</label>
      <input id="seats_total" name="seats_total" inputmode="numeric" value="{seats_total}"></div>
  </div>
  <p><button type="submit">Aktualisieren</button></p>
</form>

<h2>Verlauf</h2>
<ul>{events}</ul>

<h2>Versandte Erinnerungen</h2>
<ul>{sent}</ul>

<form method="post" action="/subscriptions/{id}/delete"
      onsubmit="return confirm('Abo wirklich löschen?');">
  <button class="danger" type="submit">Abo löschen</button>
</form>""".format(
        name=esc(sub.name or "(ohne Namen)"),
        vendor=esc(sub.vendor),
        amount=money(sub.amount, sub.currency),
        annual=money(sub.annual_cost(), sub.currency),
        days=esc(row["days_until"] if row["days_until"] is not None else "–"),
        action=esc(rec.label),
        deadline=esc(sub.deadline.isoformat() if sub.deadline else "–"),
        renewal=esc(sub.renewal_date.isoformat() if sub.renewal_date else "–"),
        notice=esc(sub.notice_days if sub.notice_days is not None else "–"),
        util=_util_bar(row["utilization_percent"], row["unused_seats"]),
        reason=esc(rec.reason),
        savings=money(rec.potential_savings, sub.currency),
        confidence="{:.0%}".format(sub.confidence) if sub.confidence is not None else "manuell",
        source=esc(sub.source),
        id=esc(sub.id),
        seats_used=esc(sub.seats_used if sub.seats_used is not None else ""),
        seats_total=esc(sub.seats_total if sub.seats_total is not None else ""),
        events=events_html,
        sent=sent_html,
    )
    return layout(sub.name or "Abo", body, "subscriptions")


def subscriptions_page(rows: list) -> bytes:
    if rows:
        table = """
<table>
<thead><tr><th>Abo</th><th>Frist</th><th>Tage</th><th>Betrag</th>
<th>Auslastung</th><th>Empfehlung</th></tr></thead>
<tbody>{rows}</tbody>
</table>""".format(rows="".join(_subscription_row(row) for row in rows))
    else:
        table = '<p class="muted">Noch keine Abos erfasst.</p>'
    body = """
<h1>Abos</h1>
<p><a class="btn" href="/subscriptions/new">+ Abo erfassen</a>
<a class="btn ghost" href="/upload">Rechnung hochladen</a></p>
{table}""".format(table=table)
    return layout("Abos", body, "subscriptions")


def reminders_page(pending: list, sent: list, mail_to: str) -> bytes:
    pending_html = "".join(
        """
<tr><td>{name}</td><td>{offset}</td><td>{deadline}</td>
<td>{action}</td><td><details><summary>Vorschau</summary><pre>{body}</pre></details></td></tr>""".format(
            name=esc(reminder.subscription_name),
            offset=esc(reminder.offset_days),
            deadline=esc(reminder.deadline.isoformat()),
            action=esc(reminder.action),
            body=esc(reminder.body),
        )
        for reminder in pending
    ) or '<tr><td colspan="5" class="muted">Keine fälligen Erinnerungen.</td></tr>'
    sent_html = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            esc(reminder.sent_at), esc(reminder.subscription_name),
            esc(reminder.offset_days), esc(reminder.recipient or "log"),
        )
        for reminder in sent
    ) or '<tr><td colspan="4" class="muted">Noch nichts versendet.</td></tr>'
    body = """
<h1>Erinnerungen</h1>
<p class="sub">60 / 30 / 7 Tage vor Frist. Empfänger: {mail}.</p>
<form method="post" action="/reminders/dispatch">
  <p><button type="submit">Fällige Erinnerungen jetzt senden</button></p>
</form>
<h2>Fällig</h2>
<table>
<thead><tr><th>Abo</th><th>Tage</th><th>Frist</th><th>Aktion</th><th>Inhalt</th></tr></thead>
<tbody>{pending}</tbody>
</table>
<h2>Verlauf</h2>
<table>
<thead><tr><th>Zeit</th><th>Abo</th><th>Tage</th><th>Empfänger</th></tr></thead>
<tbody>{sent}</tbody>
</table>""".format(
        mail=esc(mail_to or "(nicht konfiguriert, Log-Ausgabe)"),
        pending=pending_html,
        sent=sent_html,
    )
    return layout("Erinnerungen", body, "reminders")


def summary_page(summary, as_text: bool = False) -> bytes:
    if as_text:
        return layout("Woche", "<pre>{}</pre>".format(esc(summary.as_text())), "summary")
    body = """
<h1>Wochen-Zusammenfassung</h1>
<p class="sub">Fristen der nächsten {horizon} Tage und Einsparpotenzial.</p>
<pre>{text}</pre>""".format(horizon=summary.horizon_days, text=esc(summary.as_text()))
    return layout("Woche", body, "summary")


def error_page(status: int, message: str) -> bytes:
    body = "<h1>{}</h1><p>{}</p><p><a href='/'>Zurück</a></p>".format(
        status, esc(message)
    )
    return layout("Fehler", body)
