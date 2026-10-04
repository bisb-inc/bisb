import logging
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
    assert requests[0].url.params["q"] == '"Banco Alfa"'
    assert requests[0].url.params["in"] == "title,description"
    assert requests[0].url.params["sortby"] == "publishedAt"
    assert requests[0].url.params["from"] == "2026-10-01T00:00:00.000000Z"
    assert requests[0].url.params["to"] == "2026-10-02T23:59:59.999999Z"
    assert "secret-token" not in str(requests[0].url)
    client.close()


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_gnews_provider_rejects_non_successful_api_responses(status_code, caplog):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status_code, json={"errors": ["invalid-token"]})
        )
    )
    provider = GNewsProvider("invalid-token", client=client, min_request_interval=0)

    with caplog.at_level(logging.DEBUG), pytest.raises(httpx.HTTPStatusError) as error:
        provider.fetch(
            Company(name="Banco Alfa", website="https://alfa.example"),
            datetime(2026, 10, 1, tzinfo=UTC),
            datetime(2026, 10, 2, tzinfo=UTC),
        )
    assert error.value.response.status_code == status_code
    assert "invalid-token" not in str(error.value)
    assert "invalid-token" not in caplog.text
    client.close()


@pytest.mark.parametrize(
    ("name", "search_term", "expected_query"),
    [
        ("Empresa cadastrada", "Mercado Pago", '"Mercado Pago"'),
        ("Empresa cadastrada", "Banco Inter", '"Banco Inter"'),
        ("Empresa cadastrada", "Nubank", '"Nubank"'),
        ("Mercado Pago", None, '"Mercado Pago"'),
        ("Banco Inter", "", '"Banco Inter"'),
        ("Empresa cadastrada", "  Mercado Pago  ", '"Mercado Pago"'),
        ("Empresa cadastrada", 'Banco "Inter"', r'"Banco \"Inter\""'),
        ("Empresa cadastrada", r"Banco\Inter", r'"Banco\\Inter"'),
        ("Empresa cadastrada", "São João & Cia + Banco", '"São João & Cia + Banco"'),
        ("Empresa cadastrada", "Banco OR Mercado", '"Banco OR Mercado"'),
    ],
)
def test_gnews_searches_one_exact_phrase(name, search_term, expected_query, caplog):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"articles": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GNewsProvider("secret-token", client=client, min_request_interval=0)
        with caplog.at_level(logging.DEBUG):
            assert (
                provider.fetch(
                    Company(name=name, website="https://company.example", search_term=search_term),
                    datetime(2026, 10, 1, tzinfo=UTC),
                    datetime(2026, 10, 3, tzinfo=UTC),
                )
                == []
            )

    assert len(requests) == 1
    assert dict(requests[0].url.params) == {
        "q": expected_query,
        "in": "title,description",
        "sortby": "publishedAt",
        "from": "2026-10-01T00:00:00.000000Z",
        "to": "2026-10-02T23:59:59.999999Z",
        "max": "10",
    }
    assert requests[0].headers["X-Api-Key"] == "secret-token"
    assert "secret-token" not in str(requests[0].url)
    assert "secret-token" not in caplog.text


@pytest.mark.parametrize("exception_type", [httpx.ReadTimeout, httpx.ConnectError])
def test_gnews_preserves_transport_errors_without_exposing_key(exception_type, caplog):
    def handler(request):
        raise exception_type("Falha ao consultar GNews", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GNewsProvider("secret-token", client=client, min_request_interval=0)
        with caplog.at_level(logging.DEBUG), pytest.raises(exception_type) as error:
            provider.fetch(
                Company(name="Mercado Pago", website="https://company.example"),
                datetime(2026, 10, 1, tzinfo=UTC),
                datetime(2026, 10, 3, tzinfo=UTC),
            )
    assert "secret-token" not in str(error.value)
    assert "secret-token" not in caplog.text


def test_gnews_query_length_includes_phrase_delimiters_and_escaping():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"articles": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = GNewsProvider("secret-token", client=client, min_request_interval=0)
        start = datetime(2026, 10, 1, tzinfo=UTC)
        end = datetime(2026, 10, 3, tzinfo=UTC)
        provider.fetch(Company(name="A" * 198), start, end)
        for term in ("A" * 199, '"' * 100):
            with pytest.raises(ValueError, match="200 caracteres"):
                provider.fetch(Company(name=term), start, end)

    assert len(requests) == 1
    assert len(requests[0].url.params["q"]) == 200


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
