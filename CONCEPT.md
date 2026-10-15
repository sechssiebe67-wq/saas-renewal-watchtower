# SaaS Renewal Watchtower

## Goal

SaaS subscriptions renew silently. By the time an invoice arrives, a contract has
already rolled over at the old conditions, unused seats were paid for, or a price
increase hid in the fine print. **SaaS Renewal Watchtower** is a lightweight
watchtower for teams without a procurement department: it extracts renewal and
cancellation deadlines from uploaded invoices and contracts, compares them with
the actually used seats, and sends a concrete recommended action (cancel, shrink
or negotiate) 60 / 30 / 7 days before the deadline. The single number that
measures value is **avoided follow-up cost per quarter**.

## Intended users

- Ops-, IT- and finance owners in small and mid-sized companies (20–300 people)
  with 15+ SaaS subscriptions.
- Companies without a dedicated procurement function that track renewals in
  spreadsheets or not at all.

## Capabilities (current increment)

The MVP is a single self-contained web application with persistent SQLite storage
and no external services:

- **Capture**
  - Manual entry of subscription name, vendor, amount, currency, billing period,
    renewal date, cancellation deadline, notice period, seat counts and notes.
  - Upload of invoice / contract files (`.pdf`, `.txt`, `.md`) and paste-in of raw
    text.
- **Extraction with confidence**
  - Heuristic extraction of renewal date, cancellation deadline, notice period,
    paid amount, currency, seats and vendor from the uploaded text.
  - Every extracted field carries a confidence value and the matching evidence
    snippet, shown in the UI before the user saves the subscription.
  - PDF text is recovered with a dependency-free extractor (FlateDecode streams via
    `zlib` plus `Tj`/`TJ`/`BT`/`ET` operators). When a PDF cannot be read the user
    is told to enter the data manually.
- **Overview**
  - Dashboard and subscription list sorted by the next deadline, with urgency
    badges and seat-utilisation bars.
- **Recommendation instead of a bare list**
  - Rules turn deadline proximity, seat utilisation and detected price increases
    into an action: `cancel`, `shrink`, `negotiate`, `review` or `keep`, together
    with a reason and the estimated savings per billing period.
- **Reminders**
  - 60 / 30 / 7 day reminder generation with the recommended action in the subject
    and body. Sending is idempotent (a unique key per subscription/offset/deadline
    prevents double sends) and is delivered through a pluggable sender: logging
    by default, SMTP when configured.
  - An optional background scheduler dispatches due reminders without human
    intervention; it can also be triggered from the UI and the CLI.
- **Weekly summary**
  - A summary of upcoming deadlines in the next 14 days and the total potential
    savings per quarter, available in the UI and as text output.
- **Health and operations**
  - `GET /healthz` returns `{"status":"ok"}` with storage status for Kubernetes
    probes.

## Differentiation

Deliberately **not** a full SaaS-management or procurement suite. Three focuses:

1. Deadline and notice-period extraction from existing documents instead of
   manual upkeep.
2. Recommendation instead of a plain list.
3. Onboarding in under an hour without integrations.

It sits next to feedback, ticketing or voice-of-customer products in the
portfolio: this is cost and contract lifecycle, not customer input.

## Architecture

- Pure Python 3 standard library for the application, tests and deployment image
  (`sqlite3`, `zlib`, `http.server`/`wsgiref`, `smtplib`, `email`). This keeps the
  image tiny, the build reproducible on `linux/amd64` and `linux/arm64`, and CI
  green without a dependency install step.
- WSGI application served by a threaded `wsgiref` server on port `8080`.
- SQLite database file configurable through `WATCHTOWER_DB` (default
  `data/watchtower.db`; the container uses `/data/watchtower.db` on a
  persistent volume).
- Helm chart in `deploy/helm/saas-renewal-watchtower/` with non-root execution,
  resource requests/limits, ingress configuration and a `ReadWriteOnce` volume.

## Configuration

| Env var | Default | Purpose |
| --- | --- | --- |
| `WATCHTOWER_DB` | `data/watchtower.db` | SQLite path |
| `WATCHTOWER_HOST` | `0.0.0.0` | Bind address |
| `WATCHTOWER_PORT` | `8080` | HTTP port |
| `WATCHTOWER_SMTP_HOST` | *(unset)* | SMTP host; logging sender when unset |
| `WATCHTOWER_SMTP_PORT` | `587` | SMTP port |
| `WATCHTOWER_SMTP_USER` / `WATCHTOWER_SMTP_PASSWORD` | *(unset)* | SMTP credentials |
| `WATCHTOWER_MAIL_FROM` | `watchtower@localhost` | Sender address |
| `WATCHTOWER_MAIL_TO` | *(unset)* | Default reminder recipient |
| `WATCHTOWER_SCHEDULER_ENABLED` | `0` | Enable background reminder scheduler |
| `WATCHTOWER_SCHEDULER_INTERVAL` | `3600` | Scheduler interval in seconds |

## Next direction

- Pluggable, better OCR for scanned PDFs (still optional, so the base install stays
  dependency-free).
- Historical amount tracking and price-increase trend chart per vendor.
- Import/export of a subscription book and CSV onboarding.
- Alternative notification channels (chat webhook, calendar feed).
- Annual negotiation report as a paid add-on (unvalidated revenue hypothesis).

## Revenue hypothesis

Flat **49 EUR/month** for up to 30 watched subscriptions and **149 EUR/month** for
up to 150, cancellable monthly. Target: 40 paying accounts in the first two
quarters after a pilot.

## Risks

- Poorly scanned or inconsistent invoices can produce wrong deadlines and destroy
  trust → confidence display, evidence snippets and manual correction of every
  field.
- Users may not maintain seat data → recommendations degrade gracefully and show
  when utilisation is unknown.
- Willingness to pay is unvalidated → concierge pilot and price test precede
  broader build-out.
- Adjacent suites may bundle the same feature → focus on extraction plus an
  actionable recommendation.

## Validation plan

1. 8–10 semi-structured interviews with Ops/Finance owners to confirm that a
   missed deadline occurs and costs money.
2. Concierge pilot with 3 companies over 6 weeks; success is at least one
   implemented recommendation.
3. Price test (49 EUR/month commitment) before building more automation.
   Stop criterion: no incident with measurable damage in 10 interviews and no
   implemented recommendation in the pilot.

## Factory requirements (from the sales pipeline)

The product satisfies the pipeline's hard requirements: web deployable, original,
expandable, real user value, defined audience, standalone, autonomous, Kubernetes
compatible (Helm + Argo CD), resource efficient, secure, testable, maintainable,
legally compliant, health-monitored and uniquely named. Database independence is
intentionally relaxed: persistent SQLite storage adds meaningful value to a
renewal history. The maximum of 10 simultaneously active product repositories and
the creation → development → review → deployment → monitoring → iteration →
archival → reactivation lifecycle continue to apply.
