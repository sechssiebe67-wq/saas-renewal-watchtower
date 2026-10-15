# SaaS Renewal Watchtower

A lightweight watchtower that finds SaaS renewal and cancellation deadlines in
uploaded invoices and contracts, compares them with the seats actually in use,
and sends a concrete recommended action — **cancel, shrink or negotiate** — 60,
30 and 7 days before the deadline. The value is measured in avoided follow-up
cost per quarter.

It is deliberately **not** a full SaaS-management suite: it extracts from existing
documents instead of demanding manual upkeep, recommends instead of just listing,
and works without integrations.

See [CONCEPT.md](CONCEPT.md) for the product concept, audience and roadmap.

## Features

- Manual subscription entry (name, vendor, amount, billing period, deadline,
  notice period, seats, notes).
- Upload of invoices/contracts (`.pdf`, `.txt`, `.md`) or paste-in of text, with
  **per-field confidence and evidence snippets** before saving.
- Dependency-free PDF text recovery (FlateDecode streams via `zlib`).
- Dashboard and list sorted by next deadline, with urgency badges and seat
  utilisation bars.
- Rule-based recommendation with reason and estimated savings per billing period.
- 60/30/7-day reminder generation and idempotent dispatch (logging sender by
  default, SMTP when configured).
- Weekly summary of upcoming deadlines and total potential savings.
- `GET /healthz` and JSON APIs (`/api/subscriptions`, `/api/summary`).

## Quick start (no dependencies)

Requires Python 3.8+ and uses only the standard library.

```sh
python3 -m watchtower seed          # optional example data
python3 -m watchtower serve         # http://localhost:8080
```

Open <http://localhost:8080>. Data is stored in `data/watchtower.db` by default.

### CLI

```sh
python3 -m watchtower summary                       # weekly summary as text
python3 -m watchtower reminders                     # list due reminders
python3 -m watchtower dispatch                      # send due reminders
python3 -m watchtower extract invoice.pdf           # show extracted fields
python3 -m watchtower add --name "GitHub" --amount 210 \
    --deadline 2027-01-15 --seats-total 25 --seats-used 8
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `WATCHTOWER_DB` | `data/watchtower.db` | SQLite path |
| `WATCHTOWER_HOST` | `0.0.0.0` | Bind address |
| `WATCHTOWER_PORT` | `8080` | HTTP port |
| `WATCHTOWER_SMTP_HOST` | *(unset)* | SMTP host; logging sender when unset |
| `WATCHTOWER_SMTP_PORT` | `587` | SMTP port |
| `WATCHTOWER_SMTP_USER` / `WATCHTOWER_SMTP_PASSWORD` | *(unset)* | SMTP credentials |
| `WATCHTOWER_MAIL_FROM` | `watchtower@localhost` | Sender address |
| `WATCHTOWER_MAIL_TO` | *(unset)* | Default reminder recipient |
| `WATCHTOWER_SCHEDULER_ENABLED` | `0` | Run the background reminder scheduler |
| `WATCHTOWER_SCHEDULER_INTERVAL` | `3600` | Scheduler interval in seconds |
| `WATCHTOWER_REVIEW_HORIZON_DAYS` | `14` | Weekly-summary horizon |

## Docker

```sh
docker build -t watchtower .
docker run --rm -p 8080:8080 -v watchtower-data:/data watchtower
```

The image runs as UID 10001, listens on `8080`, stores the database in `/data`
and declares a `/healthz` healthcheck. It builds for `linux/amd64` and
`linux/arm64`.

## Kubernetes / Helm

Exactly one chart lives in
[`deploy/helm/saas-renewal-watchtower/`](deploy/helm/saas-renewal-watchtower/).
It renders the image as `image.repository@image.digest`, supports ingress via
`ingress.enabled`, `ingress.host` and `ingress.className`, runs non-root with
resource requests/limits and mounts a persistent volume for `/data`.

```sh
helm template watchtower deploy/helm/saas-renewal-watchtower \
  --set image.digest=sha256:... \
  --set ingress.enabled=true \
  --set ingress.host=watchtower.example.com \
  --set ingress.className=nginx
```

The factory manager publishes the chart; product workflows do not receive
infrastructure credentials.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

Product tests are standard-library only, so they run in CI without a dependency
install. Pipeline/automation tests live in `.github/scripts` and are documented
in [`.github/README.md`](.github/README.md).

## Project layout

```
watchtower/
  models.py            domain dataclasses
  extraction.py        confidence-scored field extraction
  pdf.py               dependency-free PDF text recovery
  recommendations.py   action rules (cancel/shrink/negotiate/review/keep)
  reminders.py         reminder content, windows and senders
  summary.py           weekly summary
  storage.py           SQLite persistence
  service.py           business logic
  server.py            threaded WSGI server + optional scheduler
  cli.py               command line interface
  web/                 WSGI app, router and HTML rendering
deploy/helm/           Helm chart
tests/                 product tests
Dockerfile             multi-arch image
```
