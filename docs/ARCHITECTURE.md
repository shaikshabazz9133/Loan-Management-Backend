# LendWise Loan Management - Backend Architecture

**Stack:** Python FastAPI, MongoDB, Redis, Celery, S3, Docker, YAML  
**Team:** Soughat, Shahid, Manar, Shabazz  
**Date:** 6 November 2026

> **14 modules, 72 APIs (33 reusable across roles).** Source of truth for the API list: `docs/api-catalog.yaml`. Endpoints are **not implemented yet**; each `router.py` lists its endpoints as a TODO.

## 1. At a glance

| Owner | Modules | APIs |
|---|---|---|
| **Soughat** | M1 Authentication, M2 Users & Profile, M5 Eligibility, KYC & Rules [rules & EMI], M12 Audit Trail, M14 Support & Health | 17 |
| **Shahid** | M4 Loan Applications, M5 Eligibility, KYC & Rules [KYC & bank], M10 Documents, M11 Notifications | 19 |
| **Manar** | M6 Agent Management, M7 Agent Assignments, M8 Agent Verification & Review | 19 |
| **Shabazz** | M3 Customer Management, M9 Manager Decisions & Disbursement, M13 Dashboards & Analytics | 17 |
| **Total** | 14 modules | **72** |

Methods: GET 34, POST 28, PATCH 7, DELETE 2, PUT 1

## 2. Technology stack

| Layer | Choice | Why |
|---|---|---|
| API framework | Python 3.12, FastAPI, Pydantic v2 | Async, typed, automatic OpenAPI docs |
| Database | MongoDB 7 (replica set), Motor + Beanie ODM | Flexible application document, 2dsphere geo queries, transactions |
| Cache / broker | Redis 7 | Caching, rate limits, sessions, Celery broker |
| Background jobs | Celery workers + Celery beat | Notifications, credit pull, virus scan, payouts, exports |
| File storage | AWS S3 (MinIO locally) | KYC documents via presigned URLs, encrypted at rest |
| Gateway | Nginx | TLS, rate limiting, security headers, load balancing |
| Containers | Docker, Docker Compose (YAML) | Same image for dev, CI, staging, production |
| Configuration | YAML files + environment variables | base.yaml -> {env}.yaml -> env vars; secrets only in env |
| CI/CD | GitHub Actions (YAML) | Lint, type-check, tests, build and push image |
| Observability | structlog JSON logs, Prometheus, Sentry | Request IDs, metrics, error tracking |
| Auth | JWT (access 15 min, refresh 7 days), argon2 | Role-based access: customer, agent, manager |

## 3. System architecture

```
React web app (Customer / Agent / Manager portals)
        | HTTPS
        v
Nginx  (TLS, rate limiting, security headers)
        |
        v
FastAPI API x N replicas (stateless)  --- events --->  Celery workers + beat
   |            |            |                              |
   v            v            v                              v
MongoDB      Redis        S3 / MinIO          SMS / e-mail, credit bureau, KYC provider,
(replica set) (cache,     (KYC documents)     payout gateway, Google Maps
              broker)
```

## 4. Code architecture (layers)

| Layer | Location | Responsibility |
|---|---|---|
| Router | `app/<module>/router.py` | HTTP only: parse request, call service, return schema. No business logic. |
| Schemas | `app/<module>/schemas.py` | Pydantic request / response models (DTOs); role-specific response models. |
| Service | `app/<module>/service.py` | Business rules, permission checks, state transitions, emits domain events. |
| Repository | `app/<module>/repository.py` | MongoDB queries only. Atomic updates and aggregation pipelines live here. |
| Models | `app/<module>/models.py` | Beanie documents and embedded models with indexes. |
| Core | `app/core/` | Config, security, permissions (RBAC), exceptions, logging, middleware, idempotency. |
| Common | `app/common/` | Enums, pagination, response helpers, validators, masking, geo, domain events. |
| Integrations | `app/integrations/` | Adapters for S3, SMS, e-mail, credit bureau, KYC provider, payouts, maps. |
| Workers | `app/workers/` | Celery tasks triggered by domain events or schedules. |

### Folder structure

```
loan-management-backend/
|-- app/
|   |-- main.py                 # app factory, router registration
|   |-- core/                   # config, security, permissions, exceptions, logging,
|   |                           #   deps, middleware, idempotency
|   |-- db/                     # MongoDB connection, indexes, transaction helpers
|   |-- common/                 # enums, pagination, response helpers, validators, masking, geo, events
|   |-- auth/                   # one package per module, each with:
|   |                           #   router.py  schemas.py  service.py  repository.py  models.py
|   |-- users/  customers/  loans/ (+ state_machine.py)  eligibility/ (+ emi.py)
|   |-- agents/  assignments/  reviews/  managers/
|   |-- documents/  notifications/  audit/  analytics/  support/
|   |-- integrations/           # storage (S3), sms, email, credit_bureau, kyc_provider, payouts, maps
|   `-- workers/                # celery_app.py, tasks/ (notify, documents, credit, payouts, reports)
|-- tests/                      # unit/, integration/, conftest.py
|-- scripts/                    # initial admin, index creation, seed rules
|-- config/                     # base.yaml, development.yaml, production.yaml, logging.yaml
|-- docker/                     # nginx/nginx.conf
|-- docs/                       # ARCHITECTURE.md, api-catalog.yaml
|-- .github/workflows/ci.yml
|-- Dockerfile  docker-compose.yml  docker-compose.prod.yml  .dockerignore  .gitignore
|-- requirements.txt  requirements-dev.txt  pyproject.toml  Makefile
|-- .env.example
|-- .env                        # local only; never commit
`-- README.md
```

## 5. Loan application lifecycle

| Status | Meaning |
|---|---|
| `open` | Submitted; visible to manager and to active agents within 2 km |
| `accepted` | An agent accepted it (first to accept wins) |
| `in_verification` | Agent is running the credit check and field / document checks |
| `agent_approved` | Agent recommended it; waiting for manager |
| `agent_rejected` | Agent rejected it with a reason (final) |
| `approved` | Manager approved; ready to disburse |
| `disbursing` | Payout sent to the gateway; waiting for confirmation |
| `disbursed` | Amount credited; UTR stored (final) |
| `rejected` | Manager rejected it with a reason (final) |
| `cancelled` | Customer withdrew before an agent accepted (final) |

| From | To | Who | API | Guard |
|---|---|---|---|---|
| open | accepted | Agent | `POST /applications/{id}/accept` | Agent active, within 2 km, not declined; atomic |
| open | cancelled | Customer | `POST /applications/{id}/cancel` | Owner only |
| open | rejected | Manager | `POST /applications/{id}/reject` | Reason required |
| accepted | in_verification | Agent | `verification/start, checks, credit-check` | Owning agent only |
| accepted / in_verification | open | System | `PATCH /agents/{id}/status (deactivate)` | Releases case to the area pool |
| in_verification | agent_approved | Agent | `POST /applications/{id}/recommend` | Credit >= 650, all checks done, docs present |
| accepted / in_verification | agent_rejected | Agent | `POST /applications/{id}/agent-reject` | Reason required |
| agent_approved | approved | Manager | `POST /applications/{id}/approve` | Credit >= 650 |
| agent_approved | rejected | Manager | `POST /applications/{id}/reject` | Reason required |
| approved | disbursing | Manager | `POST /applications/{id}/disburse` | Idempotency-Key; verified bank account |
| disbursing | disbursed / approved | Provider | `POST /webhooks/payouts` | HMAC verified; failure returns to approved |

## 6. Data model (MongoDB collections)

| Collection | Key fields | Indexes |
|---|---|---|
| `users` | role, name, email, mobile, password_hash, status; agent: {employee_code, area, location (GeoJSON), active} | email, mobile (unique); location 2dsphere |
| `applications` | app_no, customer_id, agent_id, status, loan {amount, tenure, purpose, rate, emi}, applicant, kyc {aadhaar_enc, aadhaar_last4, pan_enc}, bank {holder, account_enc, last4, ifsc}, address, location, declined_by[], verification {checks, comments}, credit_check, decisions, version | status+created_at, agent_id+status, customer_id; location 2dsphere; app_no unique |
| `documents` | application_id, owner_id, type, s3_key, mime, size, sha256, scan_status | application_id+type |
| `application_events` | application_id, at, actor {id, role, name}, action, from_status, to_status, note | application_id+at (append-only) |
| `disbursements` | application_id, amount, mode, account_snapshot (masked), provider_ref, utr, status, attempts | application_id unique; utr unique |
| `notifications` | user_id, type, title, body, link, read, created_at | user_id+read+created_at |
| `audit_logs` | actor, action, entity, entity_id, before/after diff, ip, request_id | entity+entity_id, actor_id |
| `config` | versioned business rules (radius, min credit score, rate, tenures...) | version |
| `sessions / otp_codes / idempotency_keys` | hashed refresh tokens, OTP hashes, idempotent responses | TTL indexes (auto-expire) |
| `counters` | sequence for human-readable app numbers (LN-1020) | _id |

## 7. Key production design decisions

- **First agent to accept wins.** POST /accept runs one atomic findOneAndUpdate with the filter {_id, status: "open", agent_id: null, "declined_by.agent_id": {$ne: me}} and sets agent_id + status. If it returns nothing, respond 409 ALREADY_ACCEPTED. No locks and no race conditions, even with many API replicas.
- **2 km area matching.** Agents and applications store GeoJSON points with 2dsphere indexes. Open requests for an agent use $geoWithin/$centerSphere with the configured radius, so changing the radius needs no code change.
- **Role-aware responses.** One endpoint, several response schemas. Before accepting, an agent receives only amount, address and location. Aadhaar, PAN and account numbers are always masked except for the owning agent and the manager.
- **State machine in one place.** app/loans/state_machine.py defines every allowed transition, the role that may trigger it and its guards. Services call transition(...); repositories update with the expected current status and version (optimistic locking).
- **Documents never pass through the API.** The client asks for a presigned S3 URL, uploads directly, then confirms. Files are virus-scanned by a worker, stored with SSE-KMS encryption and downloaded through 5-minute presigned URLs.
- **Idempotent money and submit operations.** POST /applications and POST /disburse require an Idempotency-Key header, so retries and double clicks never create duplicate applications or duplicate payouts.
- **Slow work is asynchronous.** Credit bureau pulls, SMS / e-mail, virus scans, payouts and exports run in Celery with retries and backoff. The API returns quickly and the UI updates from status and notifications.
- **Every change is audited.** Each state change writes an application_events record (shown as History in the UI) and an audit_logs record with actor, IP and request ID.

## 8. Security and compliance

- JWT access tokens (15 min) + rotating refresh tokens (7 days) stored hashed; reuse of an old refresh token revokes the session.
- Passwords hashed with argon2; account lockout after 5 failed logins; OTP attempts limited.
- RBAC through one reusable dependency, require_roles(...), plus ownership checks in services (customer owns the application, agent owns the accepted case).
- Aadhaar, PAN and bank account numbers are encrypted at field level (AES-GCM, key from KMS); only last-4 and an HMAC blind index are stored in clear for search. Follow UIDAI rules for an Aadhaar Data Vault before going live.
- Rate limits at Nginx and in the app (login 10/min, OTP 3/min); request size limited to 1 MB.
- Payout webhooks verified with HMAC signatures and replay protection.
- PII never written to logs (masking filter); CORS restricted to the frontend origin; security headers and TLS 1.2+.
- Dependency and image scanning in CI; secrets only in environment variables or a secret manager, never in YAML or Git.

## 9. Observability and reliability

- Structured JSON logs with request_id, user_id and route on every line.
- Prometheus metrics: latency, error rate per endpoint, queue length, payout success rate.
- Sentry for exceptions in API and workers.
- Health probes: /health (liveness) and /health/ready (Mongo, Redis, S3).
- MongoDB replica set (Atlas in production) with daily backups and point-in-time recovery.
- API is stateless and runs as 2+ replicas behind Nginx; workers scale independently.

## 10. Docker, YAML and environments

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build, Python 3.12 slim, non-root user, health check |
| `docker-compose.yml` | Dev stack: api (hot reload), worker, beat, MongoDB replica set, Redis, MinIO, Mailpit |
| `docker-compose.prod.yml` | Production: api x2 (gunicorn + uvicorn workers), workers, beat, Redis, Nginx; MongoDB Atlas + AWS S3 |
| `config/base.yaml` | Defaults: business rules (2 km, 650, 50% FOIR, 12%), auth TTLs, documents, rate limits |
| `config/development.yaml / production.yaml` | Per-environment overrides (docs on/off, JSON logs, Aadhaar demo mode, sandbox) |
| `config/logging.yaml` | Logging configuration |
| `docker/nginx/nginx.conf` | TLS, HTTP->HTTPS redirect, rate limit zones, security headers, proxy to API |
| `.github/workflows/ci.yml` | Ruff, mypy, pytest with Mongo/Redis services, build and push image on main |
| `.env.example` | All secrets and connection strings (copy to .env) |

Run locally: `cp .env.example .env && docker compose up --build`, then open http://localhost:8000/docs.

## 11. API catalog by module

Base path `/api/v1`. **R** = reusable (one endpoint serves several roles, response scoped by role).

### M1 Authentication (`app/auth/`) - owner **Soughat** (9 APIs)

Sign-up, login (email or mobile), JWT access/refresh rotation, OTP, password reset.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 1 | POST | `/auth/register` | Public |  | Customer sign-up (name, email, mobile, password, terms) |
| 2 | POST | `/auth/login` | Public | yes | Login with email or mobile; returns tokens + role for redirect |
| 3 | POST | `/auth/refresh` | Public | yes | Rotate access/refresh tokens (refresh-token reuse detection) |
| 4 | POST | `/auth/logout` | Any | yes | Revoke current refresh token / session |
| 5 | POST | `/auth/otp/send` | Public | yes | Send OTP to mobile (sign-up verification, reset) |
| 6 | POST | `/auth/otp/verify` | Public | yes | Verify OTP and return a short-lived verification token |
| 7 | POST | `/auth/forgot-password` | Public | yes | Start password reset (same response whether or not user exists) |
| 8 | POST | `/auth/reset-password` | Public | yes | Set new password using reset token |
| 9 | POST | `/auth/change-password` | Any | yes | Change password when logged in |

### M2 Users & Profile (`app/users/`) - owner **Soughat** (2 APIs)

Shared user accounts (customer, agent, manager) and the signed-in user's own profile.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 10 | GET | `/auth/me` | Any | yes | Current user, role and permissions |
| 11 | PATCH | `/auth/me` | Any | yes | Update own profile (mobile change needs OTP) |

### M3 Customer Management (`app/customers/`) - owner **Shabazz** (4 APIs)

Manager views of customers, their application history, block/unblock.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 12 | GET | `/customers` | Manager |  | Search / filter / paginate customers |
| 13 | GET | `/customers/{id}` | Manager |  | Customer profile and stats |
| 14 | GET | `/customers/{id}/applications` | Manager |  | Customer application history |
| 15 | PATCH | `/customers/{id}/status` | Manager |  | Block / unblock customer |

### M4 Loan Applications (`app/loans/`) - owner **Shahid** (6 APIs)

Submit, list and track applications; role-aware responses; timeline, history and the status state machine.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 16 | POST | `/applications` | Customer |  | Submit application (KYC, loan, tenure, address, GPS, bank, document ids); Idempotency-Key |
| 17 | GET | `/applications` | Customer, Agent, Manager | yes | Role-scoped list with filters, search and pagination |
| 18 | GET | `/applications/{id}` | Customer, Agent, Manager | yes | Role-aware detail (agent sees amount/address/location only before accepting) |
| 19 | GET | `/applications/{id}/timeline` | Customer, Agent, Manager | yes | 6-step progress (submitted -> disbursed) |
| 20 | GET | `/applications/{id}/history` | Customer, Agent, Manager | yes | Event log of every action |
| 21 | POST | `/applications/{id}/cancel` | Customer |  | Withdraw before an agent accepts |

### M5 Eligibility, KYC & Rules (`app/eligibility/`) - owner **Soughat, Shahid** (7 APIs)

Aadhaar, PAN, IFSC and bank validation; business-rule configuration and the EMI calculator.

| # | Method | Endpoint | Roles | R | Owner | Purpose |
|---|---|---|---|---|---|---|
| 22 | GET | `/config` | Any | yes | Soughat | Master data - loan purposes, employment types, tenures, rate, radius, min credit score |
| 23 | PUT | `/config` | Manager |  | Soughat | Update business rules (versioned, audited) |
| 24 | GET | `/config/emi` | Any | yes | Soughat | EMI calculator (amount, tenure) - used by apply form and agent view |
| 25 | POST | `/kyc/aadhaar/validate` | Customer | yes | Shahid | Format + Verhoeff checksum; optional OTP e-KYC via provider |
| 26 | POST | `/kyc/pan/validate` | Customer | yes | Shahid | Format + PAN status/name match via provider |
| 27 | GET | `/kyc/ifsc/{ifsc}` | Any | yes | Shahid | Bank and branch lookup (cached in Redis) |
| 28 | POST | `/kyc/bank/verify` | Customer, Manager | yes | Shahid | Penny-drop account verification and holder-name match |

### M6 Agent Management (`app/agents/`) - owner **Manar** (9 APIs)

Manager CRUD for agents including GeoJSON location; geo search of nearby agents.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 29 | POST | `/agents` | Manager |  | Create agent with location (lat/lng), area and credentials |
| 30 | GET | `/agents` | Manager |  | List / search / filter (active, area) |
| 31 | GET | `/agents/{id}` | Manager |  | Agent details |
| 32 | PATCH | `/agents/{id}` | Manager |  | Edit agent incl. location |
| 33 | PATCH | `/agents/{id}/status` | Manager |  | Activate / deactivate; releases unfinished cases to the open pool |
| 34 | DELETE | `/agents/{id}` | Manager |  | Soft delete (blocked if applications exist) |
| 35 | GET | `/agents/{id}/applications` | Manager |  | Customers / applications handled by the agent |
| 36 | GET | `/agents/{id}/performance` | Manager |  | Processed, recommendation rate, manager agreement |
| 37 | GET | `/agents/nearby` | Customer, Manager | yes | Active agents within radius of lat/lng (2dsphere) |

### M7 Agent Assignments (`app/assignments/`) - owner **Manar** (3 APIs)

Area request pool within the agent radius, atomic first-to-accept, decline.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 38 | GET | `/agent/open-requests` | Agent |  | Open requests within 2 km of the agent, excluding declined |
| 39 | POST | `/applications/{id}/accept` | Agent |  | Atomic claim - first agent wins (findOneAndUpdate) |
| 40 | POST | `/applications/{id}/decline` | Agent |  | Hide request for this agent (optional reason) |

### M8 Agent Verification & Review (`app/reviews/`) - owner **Manar** (7 APIs)

Field/document checks, credit check, comments, recommend or reject.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 41 | POST | `/applications/{id}/verification/start` | Agent |  | Move to in-verification |
| 42 | PATCH | `/applications/{id}/verification/checks` | Agent |  | Tick field and document checks |
| 43 | POST | `/applications/{id}/credit-check` | Agent |  | Credit bureau pull once (async); stores score |
| 44 | POST | `/applications/{id}/comments` | Agent |  | Add verification comment |
| 45 | GET | `/applications/{id}/comments` | Agent, Manager | yes | List verification comments |
| 46 | POST | `/applications/{id}/recommend` | Agent |  | Recommend to manager (credit >= 650 and all checks done) |
| 47 | POST | `/applications/{id}/agent-reject` | Agent |  | Reject with mandatory reason |

### M9 Manager Decisions & Disbursement (`app/managers/`) - owner **Shabazz** (6 APIs)

Final approval/rejection and payout to the verified bank account.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 48 | POST | `/applications/{id}/approve` | Manager |  | Final approval (only after agent recommendation and credit >= 650) |
| 49 | POST | `/applications/{id}/reject` | Manager |  | Final rejection with mandatory reason |
| 50 | POST | `/applications/{id}/disburse` | Manager |  | Payout via IMPS/NEFT/RTGS; Idempotency-Key; returns UTR |
| 51 | GET | `/disbursements` | Manager |  | List payouts with status and filters |
| 52 | GET | `/disbursements/{id}` | Customer, Manager | yes | Disbursement receipt |
| 53 | POST | `/webhooks/payouts` | Provider |  | HMAC-signed payout status callback (UTR, success/failure) |

### M10 Documents (`app/documents/`) - owner **Shahid** (5 APIs)

Direct-to-S3 uploads with presigned URLs, metadata, virus scan, secure download.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 54 | POST | `/documents/upload-url` | Customer | yes | Presigned PUT URL (type, size and MIME validated) |
| 55 | POST | `/documents` | Customer | yes | Confirm upload and save metadata; queues virus scan |
| 56 | GET | `/applications/{id}/documents` | Customer, Agent, Manager | yes | List documents of an application |
| 57 | GET | `/documents/{id}/download-url` | Customer, Agent, Manager | yes | Short-lived presigned GET URL |
| 58 | DELETE | `/documents/{id}` | Customer |  | Remove a document before submission |

### M11 Notifications (`app/notifications/`) - owner **Shahid** (4 APIs)

In-app inbox; SMS/e-mail/push are sent by background workers on domain events.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 59 | GET | `/notifications` | Any | yes | Paginated notification inbox |
| 60 | GET | `/notifications/unread-count` | Any | yes | Badge count for the bell icon |
| 61 | PATCH | `/notifications/{id}/read` | Any | yes | Mark one as read |
| 62 | PATCH | `/notifications/read-all` | Any | yes | Mark all as read |

### M12 Audit Trail (`app/audit/`) - owner **Soughat** (1 API)

Append-only audit log and application events written on every state change; audit search.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 63 | GET | `/audit-logs` | Manager |  | Search audit trail by entity, actor and date range |

### M13 Dashboards & Analytics (`app/analytics/`) - owner **Shabazz** (7 APIs)

Role dashboards (aggregation pipelines, Redis cached), charts and exports.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 64 | GET | `/dashboard/customer` | Customer |  | Customer stat cards and latest application |
| 65 | GET | `/dashboard/agent` | Agent |  | Agent stat cards and to-do list |
| 66 | GET | `/dashboard/manager` | Manager |  | Manager stat cards and action alerts |
| 67 | GET | `/reports/applications/monthly` | Manager |  | Monthly applications chart |
| 68 | GET | `/reports/applications/outcomes` | Manager |  | Approved vs rejected vs in-progress |
| 69 | GET | `/reports/agents/performance` | Manager |  | Agent performance chart |
| 70 | GET | `/reports/export` | Manager |  | CSV/XLSX export (async job, download link) |

### M14 Support & Health (`app/support/`) - owner **Soughat** (2 APIs)

Liveness/readiness probes; home for customer help and support tickets.

| # | Method | Endpoint | Roles | R | Purpose |
|---|---|---|---|---|---|
| 71 | GET | `/health` | Public | yes | Liveness probe for Docker / load balancer |
| 72 | GET | `/health/ready` | Internal | yes | Readiness - checks MongoDB, Redis and object storage |

## 12. Reusable APIs and shared components

**33 reusable endpoints** (marked R above) are written once and serve several portals, for example `GET /applications`, `GET /applications/{id}`, timeline, history, documents, notifications, `/config`, `/config/emi`, IFSC lookup and `/agents/nearby`.

| Shared component | Reused by |
|---|---|
| `core.permissions.require_roles(*roles)` | One RBAC dependency for all 72 endpoints |
| `Page[T] pagination + filter params` | Same list contract for applications, customers, agents, notifications... |
| `Error envelope + exception handlers` | Consistent error JSON with code and request_id |
| `state_machine.transition()` | Single place for status rules used by loans, assignments, reviews, managers |
| `audit.record()` | History + audit for every module |
| `geo.within_radius()` | Used by open requests, nearby agents, submit preview |
| `masking.*` | Aadhaar / PAN / account masking in responses and logs |
| `emi.calculate()` | Apply form, agent view, reports |
| `storage.presign_*()` | Documents and report exports |
| `Idempotency-Key middleware` | Submit and disburse |

## 13. Team assignment

### Soughat - 17 APIs
Platform lead - core framework, Docker/YAML, CI/CD, auth, config, audit

- M1 Authentication (9)
- M2 Users & Profile (2)
- M5 Eligibility, KYC & Rules [rules & EMI] (3)
- M12 Audit Trail (1)
- M14 Support & Health (2)

### Shahid - 19 APIs
Customer journey - applications, documents, KYC & bank, notifications

- M4 Loan Applications (6)
- M5 Eligibility, KYC & Rules [KYC & bank] (4)
- M10 Documents (5)
- M11 Notifications (4)

### Manar - 19 APIs
Agent domain - agent management, geo matching, accept/decline, verification

- M6 Agent Management (9)
- M7 Agent Assignments (3)
- M8 Agent Verification & Review (7)

### Shabazz - 17 APIs
Manager domain - customers, approvals, disbursement, dashboards & reports

- M3 Customer Management (4)
- M9 Manager Decisions & Disbursement (6)
- M13 Dashboards & Analytics (7)

### Dependencies between members

- Everyone depends on Soughat's core: auth dependency, error format, pagination, audit and state machine (deliver in week 1).
- Shahid owns the application document schema; Manar (accept/verify) and Shabazz (approve/disburse) build on it.
- Manar's recommend sets agent_approved, which Shabazz's approve requires; agree the guard rules together.
- Shabazz's dashboards aggregate data from all modules; they start with fixtures and switch to real data in week 4.

### Suggested plan

| When | Phase | Work |
|---|---|---|
| Week 1 | Foundation | Soughat: core (config, security, RBAC deps, errors, pagination, audit, state machine), Docker, CI, auth login/register/me. Others: models, schemas and repository for their modules; agree the OpenAPI contract with the frontend. |
| Week 2-3 | Module build | All four build their endpoints in parallel against the shared core, with unit tests for services. |
| Week 4 | Integrations | Sandbox adapters: credit bureau (Manar), KYC + S3 + SMS/e-mail (Shahid), payouts + webhooks (Shabazz), workers (Soughat). |
| Week 5 | Frontend integration | Replace the React localStorage store with API calls; end-to-end tests of the full loan flow. |
| Week 6 | Hardening | Load test (accept race, dashboards), security review, staging deploy, runbooks. |

## 14. Definition of done (every endpoint)

- Endpoint matches the catalog (method, path, roles) and appears in OpenAPI with examples.
- Uses require_roles, the error envelope and pagination from core; no duplicated helpers.
- Unit tests for service rules and an integration test per endpoint; coverage above 80% for the module.
- State changes go through the state machine and write audit + history.
- No PII in logs; sensitive fields masked in responses.
- Reviewed by one other team member (pairs: Soughat <-> Shahid, Manar <-> Shabazz).
