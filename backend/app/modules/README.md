# Module convention

Each future module follows this structure:

```text
modules/<name>/
  router.py       # HTTP endpoints only
  schemas.py      # request/response contracts
  models.py       # SQLAlchemy models
  repository.py   # persistence and tenant-scoped query construction
  service.py      # use cases and transaction orchestration
  permissions.py  # module-specific permission names/dependencies
  exceptions.py   # module-specific domain errors
  tests/
```

Module routers are mounted explicitly from `app/api/v1/router.py`. Tenant-owned repositories must receive tenant context from `core.tenancy`, rather than accepting a client-provided tenant ID.
