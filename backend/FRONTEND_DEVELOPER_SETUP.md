# Frontend Developer Setup Guide for Froinn Backend

This guide explains how to run the backend locally without Docker so a frontend developer can connect to it and start building against real APIs.

The project is a FastAPI backend with:
- PostgreSQL + PostGIS
- Redis
- Alembic migrations
- JWT auth
- CORS enabled for local frontend origins

## 1) Prerequisites

Install the following on your machine:

- Git
- Python 3.12+
- pip
- PostgreSQL 16 (or compatible version)
- Redis
- Optional: Postgres client tools (`psql`) for checking the database directly

### macOS install examples

```bash
brew install postgresql@16 redis
```

Then start the services:

```bash
brew services start postgresql@16
brew services start redis
```

---

## 2) Repository structure

From the repo root:

```bash
cd Froinn
cd backend
```

The backend contains:
- `.env.example` for environment settings
- `app/main.py` for the FastAPI app
- `alembic` migration files
- `app/db/bootstrap.py` for initial admin bootstrap

---

## 3) Create the local database

Create a PostgreSQL database called `frontech`.

```bash
createdb frontech
```

If you need to connect manually:

```bash
psql -d frontech
```

The project expects the database URL from [.env.example](.env.example):

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/frontech
```

If your local Postgres user is not `postgres`, update the connection string to match your machine setup.

---

## 4) Copy the environment file

```bash
cp .env.example .env
```

The default `.env` values are:

```env
APP_NAME=Frontech Innovations Logistics Platform
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/frontech
REDIS_URL=redis://localhost:6379/0

JWT_SECRET=change-me-in-a-secure-secret-manager
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

BOOTSTRAP_SUPER_ADMIN_NAME=Frontech Super Admin
BOOTSTRAP_SUPER_ADMIN_EMAIL=admin@example.com
BOOTSTRAP_SUPER_ADMIN_PASSWORD=ChangeThisBootstrapPassword123!

CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
LOG_LEVEL=INFO
```

If your frontend runs on another port, update `CORS_ORIGINS` to include it.

---

## 5) Install backend dependencies

Create and activate a virtual environment:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
pip install -U pip
pip install -e '.[dev]'
```

---

## 6) Run database migrations

Make sure PostgreSQL is running locally, then apply the schema:

```bash
alembic upgrade head
```

This creates the database tables required by the backend.

---

## 7) Bootstrap the first super admin

Create the initial platform administrator using the bootstrap values from `.env`:

```bash
python -m app.db.bootstrap
```

This creates the first admin with:
- `BOOTSTRAP_SUPER_ADMIN_NAME`
- `BOOTSTRAP_SUPER_ADMIN_EMAIL`
- `BOOTSTRAP_SUPER_ADMIN_PASSWORD`

> This is for local development only. Do not commit real secrets to version control.

---

## 8) Start the backend server

Run the API directly from Python:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

```text
http://localhost:8000
```

Swagger docs:

```text
http://localhost:8000/docs
```

OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

---

## 9) Health check

Verify the backend is alive:

```bash
curl http://localhost:8000/api/v1/health/live
```

Expected response:

```json
{"status":"ok"}
```

---

## 10) Login and use the API

The login endpoint is:

```text
POST /api/v1/auth/login
```

Example request:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "ChangeThisBootstrapPassword123!"
  }'
```

Example response:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Use the token in frontend requests:

```http
Authorization: Bearer <access_token>
```

---

## 11) Frontend CORS setup

The backend allows local frontend origins such as:

```text
http://localhost:3000
http://localhost:5173
```

If your frontend runs on another port, add it to `CORS_ORIGINS` inside `.env`.

Example:

```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:4200"]
```

After changing `.env`, restart the backend server.

---

## 12) Typical local frontend workflow

1. Start PostgreSQL locally
2. Start Redis locally
3. Create and activate the Python virtual environment
4. Install dependencies
5. Copy `.env.example` to `.env`
6. Run `alembic upgrade head`
7. Run `python -m app.db.bootstrap`
8. Start `uvicorn app.main:app --reload`
9. Log in through `/api/v1/auth/login`
10. Store the JWT and send it in every authenticated request

---

## 13) Useful commands

### Start PostgreSQL (macOS with Homebrew)

```bash
brew services start postgresql@16
```

### Start Redis (macOS with Homebrew)

```bash
brew services start redis
```

### Check PostgreSQL is running

```bash
pg_isready
```

### Check Redis is running

```bash
redis-cli ping
```

### Run database migrations

```bash
alembic upgrade head
```

### Bootstrap the default admin

```bash
python -m app.db.bootstrap
```

### Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Open API docs

```text
http://localhost:8000/docs
```

---

## 14) Common issues and fixes

### Database connection error

Check:
- PostgreSQL is running
- the database `frontech` exists
- `.env` points to the correct database URL

### Redis connection error

Check:
- Redis is running on `localhost:6379`
- `.env` has the correct `REDIS_URL`

### CORS blocked in browser

Fix:
- Add the frontend origin to `CORS_ORIGINS`
- Restart the backend

### 401 Unauthorized

Fix:
- verify the login email/password
- confirm the bearer token is sent in the `Authorization` header

### App fails to start

Check:
- Python 3.12 is installed
- the virtual environment is activated
- dependencies are installed with `pip install -e '.[dev]'`
- `.env` exists in the backend folder

---

## 15) Recommended local developer flow

This is the simplest route for frontend work:

```bash
cd backend
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e '.[dev]'
alembic upgrade head
python -m app.db.bootstrap
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

After that, open:

```text
http://localhost:8000/docs
```

and test the API before wiring it into the frontend.

---

## 16) Final note

The backend is designed to run on a normal local developer machine without Docker. For frontend development, the critical requirements are:

- PostgreSQL must be running,
- Redis must be running,
- migrations must be applied,
- the bootstrap admin must be created,
- the frontend origin must be allowed in CORS,
- every authenticated request must include the bearer token.

Once those are in place, the frontend can talk to the API normally.

The backend is configured to accept local frontends such as:

```text
http://localhost:3000
http://localhost:5173
```

If your frontend runs on another origin, add it to `CORS_ORIGINS` in `.env`.

Example:

```env
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:4200"]
```

---

## 9) Typical frontend workflow

The project currently expects the following flow:

1. Login through `/api/v1/auth/login`
2. Store bearer token in frontend local storage or secure cookie
3. Call protected endpoints with `Authorization: Bearer <token>`
4. Use the company/admin endpoints to onboard customers and companies

The backend contains the routes under the API v1 router, and Swagger provides the exact contract for the latest endpoints.

---

## 10) Useful commands

### Start everything with Docker

```bash
cd backend
docker compose up --build
```

### Stop everything

```bash
docker compose down
```

### Run migrations

```bash
docker compose exec api alembic upgrade head
```

### Rebuild the API container

```bash
docker compose build api
```

### Inspect the API docs

```text
http://localhost:8000/docs
```

---

## 11) Common problems and fixes

### Problem: database connection error

Check:
- Postgres is running
- `.env` has the correct `DATABASE_URL`
- Docker container is healthy

### Problem: Redis connection error

Check:
- Redis is running on `localhost:6379`
- `.env` has the correct `REDIS_URL`

### Problem: CORS blocked in browser

Fix:
- Add the frontend origin to `CORS_ORIGINS`
- Restart the backend after editing `.env`

### Problem: 401 unauthorized

Fix:
- Check that the login request is using the correct email/password
- Verify the returned token is passed in the `Authorization` header

### Problem: app does not start

Check:
- Python version is 3.12+
- dependencies installed correctly
- `.env` exists in the backend folder

---

## 12) Recommended local developer flow

For frontend development, this is the simplest flow:

```bash
cd backend
cp .env.example .env
docker compose up --build
```

Then in another terminal:

```bash
cd backend
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.bootstrap
```

After that, open:

```text
http://localhost:8000/docs
```

and use the Swagger UI to test endpoints before wiring them into the frontend.

---

## 13) Final note

This backend is intentionally designed for local development and frontend integration testing. For a frontend developer, the most important pieces are:

- database must be running,
- migrations must be applied,
- bootstrap admin must exist,
- the frontend origin must be allowed in CORS,
- every protected request must include the bearer token.

Once those are in place, the frontend can talk to the API normally.
