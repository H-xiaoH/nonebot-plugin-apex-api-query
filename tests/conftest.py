"""Pytest configuration and fixtures for nonebot_plugin_apex_api_query tests.

This conftest provides the NoneBot test infrastructure required by every test
file in this suite.  It MUST be present and working before any test can run.

--------------------------------------------------------------------------------
IMPORTANT: Do NOT import nonebot_plugin_apex_api_query at module level here.
All plugin imports MUST happen inside test functions — the plugin's __init__.py
has module-level side effects (get_driver(), require(), get_plugin_config())
that require a running NoneBot runtime.
--------------------------------------------------------------------------------

pytest-httpx note:
    pytest-httpx provides the ``httpx_mock`` fixture automatically.  Do NOT add
    an explicit httpx mock in this conftest — simply request ``httpx_mock`` in
    test function signatures when you need to fake HTTP responses.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import nonebot
import pytest
from nonebot.adapters.console import Adapter as ConsoleAdapter
from nonebug import NONEBOT_INIT_KWARGS
from pytest_asyncio import is_async_test

if TYPE_CHECKING:
    from nonebot_plugin_apex_api_query.models import PlayerStats


# --------------------------------------------------------------------------- #
# Section 1: pytest_configure — environment + NoneBot init kwargs
# --------------------------------------------------------------------------- #

def pytest_configure(config: pytest.Config) -> None:
    """Set required env vars and stash NoneBot init kwargs before collection.

    MUST run before any test is collected because:
    - ``APEX_API_KEY`` env var is validated by Config.model at plugin import time
    - ``NONEBOT_INIT_KWARGS`` configures the in-memory SQLite backend used by
      nonebot_plugin_orm during tests
    """
    os.environ["APEX_API_KEY"] = "test-key"
    config.stash[NONEBOT_INIT_KWARGS] = {
        "sqlalchemy_database_url": "sqlite+aiosqlite://",
        "alembic_startup_check": False,
        "driver": "~none",
    }


# --------------------------------------------------------------------------- #
# Section 2: pytest_collection_modifyitems — force session loop scope
# --------------------------------------------------------------------------- #

def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Add ``loop_scope="session"`` marker to every async test.

    Without this, pytest-asyncio may create a new event loop per test function,
    which breaks NoneBot's driver lifecycle (startup / shutdown hooks).
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


# --------------------------------------------------------------------------- #
# Section 3: after_nonebot_init — register adapters, load plugins
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="session", autouse=True)
async def after_nonebot_init() -> None:
    """Override the default nonebug ``after_nonebot_init``.

    Called once per session *after* ``nonebot.init()`` has completed but
    *before* the driver lifespan starts.  We use this window to:

    1. Register the Console adapter so test Matchers can receive events.
    2. Load plugins declared in pyproject.toml (nonebot built-in plugins).
    """
    driver = nonebot.get_driver()
    driver.register_adapter(ConsoleAdapter)
    try:
        nonebot.load_from_toml("pyproject.toml")
    except ValueError:
        pass  # Plugin project — no [tool.nonebot] section in pyproject.toml


# --------------------------------------------------------------------------- #
# Section 4: mock_db_session — configurable 3-layer async mock chain
# --------------------------------------------------------------------------- #

@pytest.fixture
def mock_db_session():
    """Return a factory that builds a complete 3-layer mock DB session chain.

    The real storage module uses this pattern::

        async with get_session() as session:
            result = await session.execute(select(...))
            return result.scalar_one_or_none()

    The mock replicates each layer so tests can control what the "database"
    returns without touching a real SQLite file.

    Usage in a test::

        def test_something(mock_db_session):
            fake_record = PlayerStats(uid="123", platform="PC", ...)
            mock_session, mock_cm = mock_db_session(result=fake_record)
            with patch("nonebot_plugin_apex_api_query.storage.get_session",
                       return_value=mock_cm):
                ...  # call storage.get_latest_record() etc.
    """

    def _create(result: PlayerStats | None = None):
        # Layer 3: the innermost session object (AsyncMock)
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        # Layer 2: the result returned by session.execute()
        mock_result = MagicMock()
        if result is not None:
            mock_result.scalar_one_or_none.return_value = result
        else:
            mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Layer 1: the async context manager wrapping the session
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_session
        mock_cm.__aexit__.return_value = None

        return mock_session, mock_cm

    return _create


# --------------------------------------------------------------------------- #
# Section 5: reset_image_caches — prevent cross-test contamination
# --------------------------------------------------------------------------- #

@pytest.fixture(autouse=True)
def reset_image_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset ``image`` module globals between tests.

    The image module maintains three module-level caches:

    - ``_image_cache``: downloaded map images (dict[str, Image])
    - ``_font_cache``: loaded font objects (dict[tuple, Font])
    - ``_map_cache_dir``: lazily-initialised cache directory (Path | None)

    Without this fixture, tests that populate these caches would leak state
    into subsequent tests, causing hard-to-debug failures.
    """
    monkeypatch.setattr("nonebot_plugin_apex_api_query.image._image_cache", {})
    monkeypatch.setattr("nonebot_plugin_apex_api_query.image._font_cache", {})
    monkeypatch.setattr("nonebot_plugin_apex_api_query.image._map_cache_dir", None)
