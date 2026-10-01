from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_session

TEST_URL = "postgresql+psycopg://test:test@127.0.0.1:1/test"


@pytest.fixture
def session():
    return MagicMock(spec=Session)


@pytest.fixture
def client(monkeypatch, session):
    # O módulo ASGI também cria a aplicação padrão; usar apenas configuração de teste.
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    from app.main import create_app

    app = create_app(Settings(_env_file=None, database_url=TEST_URL))

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
