from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
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


@pytest.fixture
def functional_db():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def functional_client(functional_db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    from app.main import create_app

    app = create_app(Settings(_env_file=None, database_url=TEST_URL))

    def override_session():
        with functional_db() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
