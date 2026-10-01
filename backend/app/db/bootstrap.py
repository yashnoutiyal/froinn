"""One-time platform bootstrap after `alembic upgrade head`.

Usage: python -m app.db.bootstrap
"""

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.companies.models import User
from app.modules.companies.service import seed_catalogs


async def bootstrap() -> None:
    settings = get_settings()
    required = (
        settings.bootstrap_super_admin_name,
        settings.bootstrap_super_admin_email,
        settings.bootstrap_super_admin_password,
    )
    if not all(required):
        raise RuntimeError(
            "Set BOOTSTRAP_SUPER_ADMIN_NAME, EMAIL and PASSWORD in .env before bootstrapping."
        )
    async with SessionLocal() as session:
        await seed_catalogs(session)
        existing = await session.scalar(
            select(User).where(User.email == settings.bootstrap_super_admin_email)
        )
        if existing is None:
            session.add(
                User(
                    full_name=settings.bootstrap_super_admin_name,
                    email=settings.bootstrap_super_admin_email,
                    password_hash=hash_password(settings.bootstrap_super_admin_password),
                    is_super_admin=True,
                )
            )
        await session.commit()


if __name__ == "__main__":
    asyncio.run(bootstrap())
