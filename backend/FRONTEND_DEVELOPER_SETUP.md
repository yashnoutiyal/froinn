# Frontend Developer Setup Guide for Froinn Backend

This guide explains how to run the backend locally so a frontend developer can connect to it and start building against real APIs.

The project is a FastAPI backend with:
- PostgreSQL + PostGIS
- Redis
- Alembic migrations
- JWT auth
- CORS enabled for local frontend origins

## 1) Prerequisites

Install the following on your machine:

- Git
- Docker Desktop (recommended for the fastest setup)
- Python 3.12+
- pip
- Optional: Postgres client tools if you want to inspect the database directly

### Recommended versions
- Python: 3.12
- Docker: recent stable version

---

## 2) Repository structure

From the repo root:

```bash
cd Froinn
```

The backend lives in:

```bash
cd backend
```

The repo already contains:
- `docker-compose.yml` for Postgres and Redis
- `.env.example` for env values
- `app/main.py` for the API app
- `alembic` migrations

---

## 3) Recommended setup: Docker Compose

This is the easiest path for frontend developers.

### Step 1: Copy environment settings

```bash
cd backend
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

### Step 2: Start the database and Redis

```bash
docker compose up -d postgres redis
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

### Step 3: Start the backend API

```bash
docker compose up --build
```

This will start the API container automatically. The app is served on:

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

## 4) Run database migrations

After the Postgres container is healthy, run:

```bash
docker compose exec api alembic upgrade head
```

This applies all migration files to your local Postgres database.

### Create the initial platform admin

```bash
docker compose exec api python -m app.db.bootstrap
```

This creates the first super-admin account using values from `.env`:
- `BOOTSTRAP_SUPER_ADMIN_NAME`
- `BOOTSTRAP_SUPER_ADMIN_EMAIL`
- `BOOTSTRAP_SUPER_ADMIN_PASSWORD`

> After bootstrap completes, you can leave these values in `.env` for local dev, but in real environments do not commit secrets.

---

## 5) Local Python setup (without Docker)

Use this if you want to run the backend directly on your machine instead of in containers.

### Step 1: Create a virtual environment

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install dependencies

```bash
pip install -U pip
pip install -e '.[dev]'
```

### Step 3: Copy env file

```bash
cp .env.example .env
```

### Step 4: Make sure Postgres and Redis are running

If you are not using Docker Compose, make sure you have a local PostgreSQL instance and Redis running on:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/frontech
redis://localhost:6379/0
```

### Step 5: Run migrations and bootstrap

```bash
alembic upgrade head
python -m app.db.bootstrap
```

### Step 6: Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at:

```text
http://localhost:8000
```

---

## 6) Health check

After the server is running, verify that it responds:

```bash
curl http://localhost:8000/api/v1/health/live
```

Expected response:

```json
{"status":"ok"}
```

---

## 7) Login and use the API

The backend exposes auth under:

```text
POST /api/v1/auth/login
```

### Example request

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "ChangeThisBootstrapPassword123!"
  }'
```

### Example response

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Use the returned token

Add the token to your frontend requests:

```http
Authorization: Bearer <access_token>
```

This token must be used for Super Admin actions and company-related APIs.

---

## 8) Frontend CORS setup

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
