# Focus Flow — Concept

## Goal

Focus Flow is a distraction-free, offline-capable **focus timer** delivered as a
static web application. It helps people structure their work into deliberate
work/break cycles using the Pomodoro technique, without accounts, databases,
tracking, or any external service.

The repository goal is to keep the whole product small enough to understand in
one sitting: a handful of plain HTML/CSS/JS files, a minimal container image,
and a Helm chart that renders on the existing k3s / Argo CD pipeline. Anyone can
serve the `app/` directory with any static file server and get the full product.

### Why this exists

- **Real user value:** structured work/break cycles reduce context switching and
  help sustain attention; the timer removes the need for a phone or a third-party
  SaaS account.
- **Low cost and low maintenance:** there is no backend, no database, and no
  runtime network traffic, so operating costs approach zero and there is nothing
  to patch beyond the base container image.
- **Privacy by construction:** all state lives in the browser's `localStorage`.
  No data ever leaves the device, so there is no personal data to protect or
  leak.

## Intended users

- **Students** who need to pace study blocks and scheduled breaks.
- **Remote knowledge workers** who want a lightweight timer that does not add
  another account or browser extension.
- **Anyone** who benefits from structured work/break cycles, including people
  with attention or task-initiation difficulties.

The product is usable on a phone, tablet, or desktop, and works fully offline
after the first load.

## Current capabilities (MVP)

- Configurable **work**, **short break**, and **long break** durations.
- A timer **state machine** for work / short break / long break phases.
- **Start, pause, reset, and skip** controls.
- **Keyboard shortcuts:** `Space` start/pause, `R` reset, `S` skip.
- **Session counter** with an automatic **long break every 4 work sessions**
  (interval configurable).
- **Audible and visual notifications** when a phase ends.
- **Local persistence** of settings and the current session count via
  `localStorage`.
- **Dark / light theme** toggle that is remembered.
- **Responsive layout** for mobile (360px), tablet (768px), and desktop (1280px).
- **Accessible markup:** semantic landmarks, a skip link, an ARIA live region
  that announces timer/phase updates, visible focus states, and a
  high-contrast palette.

## Next direction

- Optional **ambient sound** (e.g. brown noise / rain) using the Web Audio API.
- **Task labels** per session, kept locally, with a simple per-day log.
- **Weekly stats view** computed entirely from `localStorage`.
- **PWA install support** (service worker + manifest) for an app-like,
  fully offline experience.
- **Internationalisation (i18n)** with a small message catalog.

## How the repository meets its own criteria

### Hard requirements (MUST)

| Requirement | How Focus Flow satisfies it |
| --- | --- |
| Web Deployable | Static SPA served from `app/`; runs in any browser. |
| Originality | A no-account, offline, single-file focus timer with explicit privacy and k3s/GitOps packaging; not a copy of an existing product. |
| Expandable | Pure timer engine (`app/timer.js`) is decoupled from the DOM layer (`app/main.js`), so features slot in without rewrites. |
| Real User Value | Structures work/break cycles to improve focus and reduce context switching. |
| Clearly Defined Audience | Students, remote knowledge workers, and anyone needing structured cycles. |
| Standalone | No dependency on any other AI Product Factory application. |
| Autonomous Operation | No backend; nothing to administer after deployment. |
| Kubernetes Compatible | `Dockerfile` + `helm/` chart with `Deployment`, `Service`, `Ingress`, probes, and resource limits. |
| Resource Efficient | Tiny nginx:alpine image, static files only, small CPU/RAM requests and limits in `helm/values.yaml`. |
| Security | No secrets, no runtime external calls, no telemetry, no user input leaves the browser; container runs as non-root. |
| Testable | `tests/` verifies assets, structure, and Helm rendering via `unittest`. |
| Maintainable | Plain HTML/CSS/JS with no build step and clear project structure. |
| Legal Compliance | Original code, no third-party assets, no personal data collected. |
| Health Monitoring | `/healthz` static endpoint used by liveness/readiness probes. |
| Unique Product Identity | Product name "Focus Flow", own repository, own subdomain via the Helm ingress. |

### Soft requirements (SHOULD)

| Requirement | How Focus Flow addresses it |
| --- | --- |
| Database Independence | Uses only `localStorage`; no database. |
| Monetization Potential | Future paid themes/ambient packs or a hosted team dashboard; the core stays free. |
| Low Operating Costs | Static assets, near-zero CPU/RAM, no external APIs. |
| Fast MVP Development | No build tooling; the MVP is a few files. |
| Low Maintenance | No backend or data migrations to maintain. |
| Market Differentiation | Privacy-first, offline, no-account, and packaged as a Kubernetes-native OSS app. |
| Growth Potential | Serving more users costs effectively nothing. |
| User Retention | Daily use pattern; persistent settings and session counts. |
| Discoverability | Clear name, description, and docs; shareable as a URL. |
| Mobile Friendly | Responsive layout and touch-friendly controls. |
| Accessibility | Semantic landmarks, ARIA live region, keyboard shortcuts, focus states, contrast. |
| Minimal Dependencies | Zero runtime JS/CSS dependencies. |
| Measurable Success | `/healthz` for reliability; session count persisted locally for engagement. |
| Reusability | Reuses the standard static-container + Helm deployment template. |
| Innovation Potential | Ambient sound, stats, and PWA support are natural next steps. |

## Repository criteria (canonical definitions)

These are the requirements every product in this repository must be evaluated
against. The tables above map Focus Flow to each one.

### Hard Requirements (MUST)

Every product must satisfy these requirements before the Salesman can approve its development.

- **Web Deployable:** Must run as a web application and be accessible through a browser.
- **Originality:** Must not be a direct copy of an existing product, whether internally developed or commercially available. Existing concepts may be combined or significantly improved to create something unique.
- **Expandable:** Must have an architecture that allows additional features and future improvements.
- **Real User Value:** Must solve a real problem, provide entertainment, improve productivity, or offer another clearly identifiable benefit.
- **Clearly Defined Audience:** Must have at least one identifiable target audience.
- **Standalone:** Must function independently without requiring another AI Product Factory application.
- **Autonomous Operation:** Must operate without continuous human intervention after deployment.
- **Kubernetes Compatible:** Must be containerized and deployable on the existing k3s cluster using Helm and Argo CD.
- **Resource Efficient:** Must stay within defined CPU, RAM, and storage budgets.
- **Security:** Must follow basic security practices, including dependency scanning, safe secret handling, and input validation.
- **Testable:** Must support automated testing and have measurable acceptance criteria.
- **Maintainable:** Must contain readable source code, clear project structure, and sufficient technical documentation.
- **Legal Compliance:** Must respect software licences, copyright, privacy regulations, and applicable laws.
- **Health Monitoring:** Must expose a reliable way to verify whether the deployment is healthy.
- **Unique Product Identity:** Must have a unique repository name, product name, and subdomain.

### Soft Requirements (SHOULD)

These requirements should influence the Salesman's evaluation and ranking.

- **Database Independence:** Should preferably work without a database. A database is allowed when persistent storage adds meaningful value.
- **Monetization Potential:** Should have a realistic path to revenue, such as subscriptions, advertisements, one-time purchases, or paid features.
- **Low Operating Costs:** Should require minimal infrastructure, external APIs, and paid services.
- **Fast MVP Development:** Should ideally have a deployable minimum viable product within a limited development budget.
- **Low Maintenance:** Should require minimal ongoing maintenance and manual administration.
- **Market Differentiation:** Should offer a meaningful advantage over existing alternatives.
- **Growth Potential:** Should be able to attract additional users without a proportional increase in operating costs.
- **User Retention:** Should provide reasons for users to return regularly.
- **Discoverability:** Should be understandable, searchable, and easy to share.
- **Mobile Friendly:** Should work well on smartphones, tablets, and desktop browsers.
- **Accessibility:** Should follow established accessibility principles.
- **Minimal Dependencies:** Should avoid unnecessary external services and vendor lock-in.
- **Measurable Success:** Should provide metrics that help evaluate adoption, reliability, and product value.
- **Reusability:** Should preferably reuse existing components, design patterns, and deployment templates.
- **Innovation Potential:** Should have opportunities for unique features or future experimentation.

### Product Rejection Criteria

The Salesman must reject a product idea if:

- It is merely a clone without meaningful differentiation.
- Its purpose or target audience cannot be explained clearly.
- It cannot run within the available infrastructure budget.
- It requires unavailable credentials, licences, hardware, or external services.
- It introduces unacceptable security, legal, or privacy risks.
- It has no realistic path to a working MVP.
- It requires continuous manual operation.
- It offers no meaningful advantage over an already active product.
- Its projected value does not justify its development and operating costs.

### Product Lifecycle Requirements

Every approved product must support:

1. **Creation:** A dedicated GitHub repository is created.
2. **Development:** The AI Developer implements the MVP.
3. **Review:** Automated testing and AI code review validate the product.
4. **Deployment:** Helm and GitOps configuration deploy the application.
5. **Monitoring:** Operational health and product performance are evaluated.
6. **Iteration:** The product can receive additional features and improvements.
7. **Archival:** The repository is preserved while the deployment and Helm chart are removed.
8. **Reactivation:** An archived product can be rebuilt and deployed again if its potential improves.

The maximum number of simultaneously active product repositories is **10**.

## Operating notes

- **Run locally:** `python3 -m http.server 8080` from `app/`, then open
  <http://localhost:8080>.
- **Run tests:** `python3 -m unittest discover -s tests -p 'test_*.py' -v`.
- **Render the chart:** `helm template focus-flow helm`.
- **Deploy:** build the image from `Dockerfile`, publish it, and let Argo CD
  sync the `helm/` chart into k3s.
