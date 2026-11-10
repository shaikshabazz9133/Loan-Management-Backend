# LendWise Loan Management - Backend (FastAPI + MongoDB)

Backend for the LendWise React frontend - 15 APIs across 6 modules, all used by the frontend.

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
│   └── agents/            # agent management
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

## Run with Docker (recommended - no MongoDB install or Atlas account needed)

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and open it, then:

```bash
cp .env.example .env      # first time only; the defaults work as-is
docker compose up -d      # first run downloads MongoDB and builds the API (a few minutes)
```

- API docs: http://localhost:8000/docs
- Manager login: `manager@example.com` / `manager123` (from `.env`, created automatically on start)
- Browse the data with MongoDB Compass: `mongodb://localhost:27017`, database `lendwise`

Two containers run: `mongo` (official `mongo:7.0` image) and `api` (this code, built from the `Dockerfile`).
Your data lives in the Docker volume `lendwise_mongo_data`, so it survives restarts. Each developer has their own database.
Edits in `app/` reload the API automatically. After changing `requirements.txt`, run `docker compose up -d --build`.

| Command | What it does |
|---|---|
| `docker compose up -d` | Start MongoDB + API in the background |
| `docker compose ps` | Show whether both are running |
| `docker compose logs -f api` | Follow the API logs (Ctrl+C to stop following) |
| `docker compose restart api` | Restart only the API |
| `docker compose down` | Stop everything (data is kept) |
| `docker compose down -v` | Stop and **delete all data** (fresh start) |
| `docker compose exec mongo mongosh lendwise` | MongoDB shell |

Port 8000 or 27017 already in use? Stop the other program, or pick other ports: `API_PORT=8001 MONGO_PORT=27018 docker compose up -d`.

## Run without Docker

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # MONGODB_URI: mongodb://localhost:27017 (Docker MongoDB) or your Atlas URL
docker compose up -d mongo        # optional: only the database in Docker
python -m scripts.create_manager  # one time: creates the manager account
uvicorn app.main:app --reload     # API docs: http://localhost:8000/docs
pytest -v                         # tests use an in-memory database
```

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
