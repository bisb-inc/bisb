import pytest
from pydantic import ValidationError

from app.core.config import Settings

TEST_URL = "postgresql+psycopg://test:test@localhost:5433/test"


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_environment_overrides_dotenv(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(f"APP_NAME=From file\nDATABASE_URL={TEST_URL}\n", encoding="utf-8")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("APP_NAME", "From environment")
    settings = Settings(_env_file=env_file)
    assert settings.app_name == "From environment"
    assert settings.database_url.get_secret_value() == TEST_URL
    assert "test:test" not in repr(settings)


@pytest.mark.parametrize("url", ["", "sqlite:///test.db", "postgresql://test:test@localhost/test"])
def test_invalid_database_url_is_rejected(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url=url)
