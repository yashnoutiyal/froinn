import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough")
os.environ.setdefault("CORS_ORIGINS", "[]")

from fastapi.testclient import TestClient

from app.main import app


def test_liveness() -> None:
    response = TestClient(app).get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_exposes_frontend_contract() -> None:
    schema = TestClient(app).get("/openapi.json").json()
    assert schema["info"]["title"] == "Frontech Innovations Logistics Platform"
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/admin/companies" in schema["paths"]
    assert "/api/v1/admin/companies/{company_id}/modules" in schema["paths"]
    assert "/api/v1/admin/companies/{company_id}/amc/renewals" in schema["paths"]
