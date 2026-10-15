import pytest
from pathlib import Path
from uuid import uuid4


@pytest.fixture(autouse=True)
def offline_provider(monkeypatch):
    # Unit tests never use developer credentials or incur API charges.
    monkeypatch.setenv("CATNANNY_EXTRACTION_PROVIDER", "rules")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_TIMEOUT_SECONDS", raising=False)


@pytest.fixture
def isolated_db(monkeypatch):
    from catnanny.storage import database
    # Keep each run in the workspace; no automatic recursive directory cleanup.
    tmp_path = Path(__file__).resolve().parents[1] / "data" / "test-runs" / uuid4().hex
    tmp_path.mkdir(parents=True)
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "catnanny.sqlite3")
    database.init_db()
    return database
