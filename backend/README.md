# Frontech backend

The backend is a FastAPI modular monolith. The first deliverable is the Super Admin Companies module: secure sign-in, company provisioning, AMC plans/contracts, tenant module entitlements, default company roles, primary admin setup, email outbox records, and audit events. Logistics domain APIs and tables are intentionally not yet implemented.

## Run locally

```bash
cp .env.example .env
alembic upgrade head
python -m app.db.bootstrap
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; Swagger/OpenAPI is at `/docs` and the OpenAPI JSON is at `/openapi.json`.

For a host-based setup, create a virtual environment, install `pip install -e '.[dev]'`, copy `.env.example` to `.env`, start PostgreSQL/PostGIS and Redis, then run the commands above. `DATABASE_URL` must point at the running PostgreSQL instance.

## Migrations

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

New tenant-owned models must use the tenant-scoped repository/dependency conventions described in `app/modules/README.md`. The client must never determine the active tenant by posting a tenant ID.

## Frontend handoff sequence

1. `POST /api/v1/auth/login` to receive a bearer token.
2. Add `Authorization: Bearer <token>` to every Super Admin request.
3. Read `GET /api/v1/admin/catalog/plans` and `GET /api/v1/admin/catalog/modules` for the wizard screens.
4. Submit all wizard data once to `POST /api/v1/admin/companies`.
5. Use the company endpoints to list, edit profile, replace enabled modules, renew AMC, suspend and restore.

The authoritative request/response contracts and examples are generated in Swagger. Never display or persist `generated_password` after the initial provisioning response.
