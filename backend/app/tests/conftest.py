from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

# Must be set before app.main is imported so settings (cached) skip startup ingestion in tests.
os.environ["INGEST_ON_STARTUP"] = "false"

import asyncpg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ingestion import IngestRunner  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "transcripts"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


# --- isolated database for ingestion/retrieval tests -------------------------------------
# These tests wipe episodes/chunks, so they must never touch the real application database.
# They use "<database>_test" on the same Postgres server, migrated with the real Alembic files.


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = make_url(get_settings().database_url)
    test_name = f"{url.database}_test"
    test_url = url.set(database=test_name)

    async def ensure_database() -> None:
        admin = url.set(database="postgres")
        conn = await asyncpg.connect(
            host=admin.host,
            port=admin.port or 5432,
            user=admin.username,
            password=admin.password,
            database="postgres",
        )
        try:
            exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", test_name)
            if not exists:
                await conn.execute(f'CREATE DATABASE "{test_name}"')
        finally:
            await conn.close()

    asyncio.run(ensure_database())
    rendered = test_url.render_as_string(hide_password=False)
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": rendered},
        check=True,
        capture_output=True,
    )
    return rendered


@pytest_asyncio.fixture
async def db_factory(test_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE chunks, episodes RESTART IDENTITY CASCADE"))
    yield factory
    await engine.dispose()


@pytest.fixture
def transcripts_dir(tmp_path: Path) -> Path:
    """A writable copy of the small fixture transcripts (tests may edit or delete files)."""
    target = tmp_path / "transcripts"
    shutil.copytree(FIXTURES_DIR, target)
    return target


@pytest.fixture
def make_runner(db_factory: async_sessionmaker[AsyncSession]):  # type: ignore[no-untyped-def]
    def build(directory: Path, **overrides: object) -> IngestRunner:
        settings = Settings(transcripts_dir=str(directory), **overrides)  # type: ignore[arg-type]
        return IngestRunner(db_factory, settings)

    return build


@pytest_asyncio.fixture
async def ingested(make_runner, transcripts_dir: Path):  # type: ignore[no-untyped-def]
    runner = make_runner(transcripts_dir)
    await runner.run("test")
    return runner
