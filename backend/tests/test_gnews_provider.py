from datetime import UTC, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.models import Company
from app.providers import configured_providers
from app.providers.gnews import GNewsProvider
from app.providers.mock import MockNewsProvider, MockXProvider


def test_gnews_provider_normalizes_real_articles_and_date_bounds():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "title": "Notícia real",
                        "description": "Descrição",
                        "url": "https://news.example/article",
                        "publishedAt": "2026-10-02T12:00:00Z",
                    },
                    {
                        "title": "Fora do período",
                        "description": None,
                        "url": "https://news.example/outside",
                        "publishedAt": "2026-10-03T00:00:00Z",
                    },
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GNewsProvider("secret-token", client=client, min_request_interval=0)
    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = datetime(2026, 10, 3, tzinfo=UTC)

    events = provider.fetch(Company(name="Banco Alfa", website="https://alfa.example"), start, end)

    assert len(events) == 1
    assert events[0].title == "Notícia real"
    assert events[0].description == "Descrição"
    assert events[0].url == "https://news.example/article"
    assert events[0].published_at == datetime(2026, 10, 2, 12, tzinfo=UTC)
    assert events[0].is_mock is False
    assert requests[0].headers["X-Api-Key"] == "secret-token"
    assert requests[0].url.params["q"] == "Banco Alfa"
    assert requests[0].url.params["from"] == "2026-10-01T00:00:00.000000Z"
    assert requests[0].url.params["to"] == "2026-10-02T23:59:59.999999Z"
    assert "secret-token" not in str(requests[0].url)
    client.close()


def test_gnews_provider_rejects_non_successful_api_responses():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(401, json={"errors": []}))
    )
    provider = GNewsProvider("invalid-token", client=client, min_request_interval=0)

    with pytest.raises(httpx.HTTPStatusError):
        provider.fetch(
            Company(name="Banco Alfa", website="https://alfa.example"),
            datetime(2026, 10, 1, tzinfo=UTC),
            datetime(2026, 10, 2, tzinfo=UTC),
        )
    client.close()


def test_configured_providers_use_mock_without_key_and_gnews_with_key():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
    )
    assert [type(provider) for provider in configured_providers(settings)] == [
        MockNewsProvider,
        MockXProvider,
    ]

    settings.gnews_api_key = SecretStr(" real-key ")
    providers = configured_providers(settings)
    assert isinstance(providers[0], GNewsProvider)
    assert "real-key" not in repr(providers[0])
    assert isinstance(providers[1], MockXProvider)
