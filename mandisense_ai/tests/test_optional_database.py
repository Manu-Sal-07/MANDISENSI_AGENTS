"""The database is optional: a service with no (or a dead) Postgres must start, not crash-loop.

Regression for a real incident: a free Render Postgres was suspended, `scripts/init_db.py` exited 1 on the unresolvable host, and the
API restarted forever with every request timing out, although no answer depends on the database.
"""
import asyncio
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_init_db():
    spec = importlib.util.spec_from_file_location("init_db_under_test", ROOT / "scripts" / "init_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def init_db(monkeypatch):
    for name in ("DATABASE_URL", "POSTGRES_HOST", "DB_REQUIRED"):
        monkeypatch.delenv(name, raising=False)
    return _load_init_db()


def test_no_database_configured_is_a_clean_skip(init_db, monkeypatch):
    monkeypatch.setenv("APP__ENVIRONMENT", "production")
    assert init_db.init_database() == 0


def test_unreachable_database_degrades_instead_of_failing(init_db, monkeypatch):
    # The exact hostname failure from the incident: it cannot resolve, so connecting raises immediately.
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@dpg-does-not-exist-a.invalid/db")
    monkeypatch.setenv("APP__ENVIRONMENT", "production")
    assert init_db.init_database() == 0


def test_db_required_restores_the_strict_behaviour(init_db, monkeypatch):
    monkeypatch.setenv("DB_REQUIRED", "1")
    assert init_db.init_database() == 1
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@dpg-does-not-exist-a.invalid/db")
    assert init_db.init_database() == 1


def test_api_startup_check_does_not_exit_without_a_database(monkeypatch):
    import api.main as main

    for name in ("DATABASE_URL", "POSTGRES_HOST", "DB_REQUIRED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP__ENVIRONMENT", "production")
    asyncio.run(main.verify_and_initialize_db())  # would raise SystemExit before the fix


def test_api_startup_check_survives_a_dead_database_unless_required(monkeypatch):
    import api.main as main

    async def dead():
        return False

    monkeypatch.setattr(main, "ping_db_async", dead)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@dpg-does-not-exist-a.invalid/db")
    monkeypatch.setenv("APP__ENVIRONMENT", "production")
    monkeypatch.delenv("DB_REQUIRED", raising=False)
    asyncio.run(main.verify_and_initialize_db())

    monkeypatch.setenv("DB_REQUIRED", "1")
    with pytest.raises(SystemExit):
        asyncio.run(main.verify_and_initialize_db())


def test_forecast_scheduler_can_be_switched_off(monkeypatch):
    from mandisense_ai.forecasting.scheduler import forecast_scheduler_enabled

    monkeypatch.delenv("FORECAST_SCHEDULER", raising=False)
    assert forecast_scheduler_enabled() is True
    for value in ("off", "OFF", "0", "false"):
        monkeypatch.setenv("FORECAST_SCHEDULER", value)
        assert forecast_scheduler_enabled() is False
