from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        pool_pre_ping=True,
        pool_timeout=3,
        hide_parameters=True,
    )


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session
