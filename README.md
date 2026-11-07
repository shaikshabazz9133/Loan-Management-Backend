# LendWise Loan Management - Backend (FastAPI + MongoDB)

Backend skeleton for the LendWise React frontend. **Structure only - endpoints are not implemented yet.**
Each module's `router.py` docstring lists the endpoints to build (method, path, roles, purpose) - 72 APIs across 14 modules.

## Project structure

```
loan-management-backend/
├── app/
│   ├── main.py
│   ├── core/              # config, security, permissions, exceptions, logging
│   ├── db/                # MongoDB connection, indexes, transaction helpers
│   ├── common/            # enums, pagination, response helpers
│   ├── auth/              # login, tokens, OTP, password reset
│   ├── users/             # user accounts and own profile
│   ├── customers/         # manager views of customers
│   ├── loans/             # loan applications + status state machine
│   ├── eligibility/       # KYC, bank checks, business rules, EMI
│   ├── agents/            # agent management
│   ├── assignments/       # open requests, accept / decline
│   ├── reviews/           # agent verification, credit check, recommend
│   ├── managers/          # approve / reject / disburse
│   ├── documents/         # S3 uploads and downloads
│   ├── notifications/     # in-app inbox
│   ├── audit/             # audit trail
│   ├── analytics/         # dashboards and reports
│   └── support/           # health checks, help & support
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── scripts/               # initial admin, index creation, seed rules
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env                   # local only; never commit
├── .dockerignore
├── .gitignore
└── README.md
```

Each module package contains `router.py`, `schemas.py`, `service.py`, `repository.py` and `models.py`.
Build in this order: `models.py` -> `repository.py` -> `schemas.py` -> `service.py` -> `router.py` -> tests.

## Run locally

```bash
cp .env.example .env
docker compose up --build
# API docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001     Mailpit: http://localhost:8025
```

Settings defaults (business rules, auth, documents, pagination) live in `app/core/config.py`; any value can be overridden with an environment variable in `.env`.
