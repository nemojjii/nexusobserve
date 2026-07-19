"""Shared pytest fixtures.

Sets NEXUS_DB_PATH=:memory: before any collector import so tests never write
real files, and resets per-process singletons between tests.
"""

import os

# Must be set before nexus_collector.db is first imported so DB_PATH picks it up.
os.environ.setdefault("NEXUS_DB_PATH", ":memory:")

import pytest


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module-level singletons so every test starts clean."""
    # Collector: :memory: singleton connection
    import nexus_collector.db as db_mod
    db_mod._memory_conn = None

    # SDK: local-mode flag
    import nexusobserve.tracer as tracer_mod
    tracer_mod._local_mode = False

    yield

    # Teardown
    if db_mod._memory_conn is not None:
        try:
            db_mod._memory_conn.close()
        except Exception:
            pass
        db_mod._memory_conn = None

    tracer_mod._local_mode = False
