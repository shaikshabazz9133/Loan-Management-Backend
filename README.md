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

## Run locally (without Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # then set MONGODB_URI (Atlas: replace <db_password>) and SECRET_KEY
python -m scripts.create_manager  # one time: creates the manager account
uvicorn app.main:app --reload     # API docs: http://localhost:8000/docs
pytest -v                         # tests use an in-memory database
```

Or with Docker: `docker compose up --build`.

Settings defaults (business rules, auth, documents, pagination) live in `app/core/config.py`; any value can be overridden with an environment variable in `.env`.

## Authentication APIs

Base URL `http://localhost:8000/api/v1`. JSON is camelCase. Send the access token as `Authorization: Bearer <accessToken>`.

| Method | Path | Who | Body |
|---|---|---|---|
| POST | `/auth/register` | Public (customer sign-up) | `{name, email, mobile, password, termsAccepted}` |
| POST | `/auth/login` | Public (all roles) | `{identifier, password, remember}` - identifier = email or mobile |
| POST | `/auth/refresh` | Public | `{refreshToken}` |
| GET | `/auth/me` | Signed in | - |
| POST | `/agents` | Manager | `{name, email, mobile, password, area, city, location: {lat, lng}, active}` |
| GET | `/agents` | Manager | - |
| PATCH | `/agents/{id}` | Manager | any of the create fields, e.g. `{active: false}`; omit `password` to keep it |
| DELETE | `/agents/{id}` | Manager | - |

`register`, `login` and `refresh` return `{accessToken, refreshToken, tokenType, user}`; `user.role` (`customer` / `agent` / `manager`) tells the frontend which portal to open.

Who signs in how:
1. **Customer** creates an account with `/auth/register` and is signed in immediately.
2. **Manager** account is created once by `python -m scripts.create_manager` (login details from `MANAGER_EMAIL` / `MANAGER_MOBILE` / `MANAGER_PASSWORD` in `.env`).
3. **Agent** accounts are created only by the manager (`POST /agents`); the agent then signs in with that email/mobile and password. Inactive agents cannot sign in.

Errors always look like `{"error": {"code": "EMAIL_TAKEN", "message": "...", "details": {"field": "message"}}}` (`details` only for validation errors).
