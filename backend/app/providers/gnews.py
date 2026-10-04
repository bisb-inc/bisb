import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from pydantic import SecretStr

from app.models import Company, EventSource
from app.providers.base import NormalizedEvent

GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"
GNEWS_MAX_QUERY_LENGTH = 200
GNEWS_MAX_RESULTS = 10
GNEWS_MIN_REQUEST_INTERVAL_SECONDS = 1.05


class GNewsProvider:
    source = EventSource.GNEWS

    def __init__(
        self,
        api_key: SecretStr | str,
        *,
        client: httpx.Client | None = None,
        min_request_interval: float = GNEWS_MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        secret = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        self._api_key = SecretStr(secret.strip())
        self._client = client
        self._min_request_interval = min_request_interval
        self._last_request_at: float | None = None
        self._request_lock = threading.Lock()

    def fetch(self, company: Company, start: datetime, end: datetime) -> list[NormalizedEvent]:
        query = company.effective_search_term.strip()
        if len(query) > GNEWS_MAX_QUERY_LENGTH:
            raise ValueError(
                f"O termo de busca do GNews deve ter até {GNEWS_MAX_QUERY_LENGTH} caracteres"
            )

        params = {
            "q": query,
            "from": self._format_datetime(start),
            # GNews treats `to` as inclusive; the domain interval is end-exclusive.
            "to": self._format_datetime(end - timedelta(microseconds=1)),
            "max": GNEWS_MAX_RESULTS,
            "sortby": "publishedAt",
        }
        headers = {"X-Api-Key": self._api_key.get_secret_value()}

        with self._request_lock:
            self._wait_for_rate_limit()
            if self._client is not None:
                response = self._client.get(GNEWS_SEARCH_URL, params=params, headers=headers)
            else:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(GNEWS_SEARCH_URL, params=params, headers=headers)
            self._last_request_at = time.monotonic()

        response.raise_for_status()
        payload: Any = response.json()
        articles = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(articles, list):
            raise ValueError("A resposta do GNews não contém a lista esperada de artigos")

        events = []
        for article in articles:
            if not isinstance(article, dict):
                raise ValueError("A resposta do GNews contém um artigo inválido")
            title = article.get("title")
            url = article.get("url")
            published_at = article.get("publishedAt")
            if not isinstance(title, str) or not isinstance(url, str):
                raise ValueError("A resposta do GNews não contém título e URL válidos")
            if not isinstance(published_at, str):
                raise ValueError("A resposta do GNews não contém publishedAt válido")

            published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            if published.tzinfo is None:
                raise ValueError("A data publicada pelo GNews não contém timezone")
            if not start <= published.astimezone(UTC) < end:
                continue

            description = article.get("description")
            events.append(
                NormalizedEvent(
                    source=self.source,
                    title=title,
                    description=description if isinstance(description, str) else None,
                    url=url,
                    published_at=published.astimezone(UTC),
                    is_mock=False,
                )
            )
        return events

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is None:
            return
        delay = self._min_request_interval - (time.monotonic() - self._last_request_at)
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        if value.tzinfo is None:
            raise ValueError("O intervalo de coleta deve conter timezone")
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
