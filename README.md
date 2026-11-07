# LendWise Loan Management - Backend (FastAPI + MongoDB)

Production backend skeleton for the LendWise React frontend. **Architecture and structure only - endpoints are not implemented yet.**

- **Architecture & API plan (PDF):** `LendWise_Backend_Architecture.pdf`
- **Same document in Markdown:** `docs/ARCHITECTURE.md`
- **API catalog (source of truth, 72 APIs / 14 modules):** `docs/api-catalog.yaml`

| Owner | Modules | APIs |
|---|---|---|
| Soughat | M1 Authentication, M2 Users & Profile, M5 Eligibility, KYC & Rules [rules & EMI], M12 Audit Trail, M14 Support & Health (+ core, Docker, CI) | 17 |
| Shahid | M4 Loan Applications, M5 Eligibility, KYC & Rules [KYC & bank], M10 Documents, M11 Notifications | 19 |
| Manar | M6 Agent Management, M7 Agent Assignments, M8 Agent Verification & Review | 19 |
| Shabazz | M3 Customer Management, M9 Manager Decisions & Disbursement, M13 Dashboards & Analytics | 17 |

## Run locally

```bash
cp .env.example .env
docker compose up --build
# API docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001     Mailpit: http://localhost:8025
```

## Where to start (each owner)

Open `app/<your module>/router.py` - the docstring lists every endpoint you own (method, path, roles, purpose).
Build in this order: `models.py` -> `repository.py` -> `schemas.py` -> `service.py` -> `router.py` -> tests.
Use the shared pieces in `app/core`, `app/common` and `app/db` (permissions, errors, pagination, response helpers, transactions), plus `app/audit` and `app/loans/state_machine.py`, instead of writing your own.

If you change an endpoint, update `docs/api-catalog.yaml` first.
