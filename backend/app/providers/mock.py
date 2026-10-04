from datetime import datetime, timedelta

from app.models import Company, EventSource
from app.providers.base import NormalizedEvent


class MockNewsProvider:
    source = EventSource.GNEWS

    def fetch(self, company: Company, start: datetime, end: datetime) -> list[NormalizedEvent]:
        published = end - timedelta(hours=12)
        if not start <= published < end:
            return []
        return [
            NormalizedEvent(
                source=self.source,
                title=f"Atualização de mercado envolvendo {company.name}",
                description=f"Notícia demonstrativa simulada para {company.effective_search_term}.",
                url=f"https://example.invalid/mock/news/{company.id}",
                published_at=published,
                is_mock=True,
            )
        ]


class MockXProvider:
    source = EventSource.X

    def fetch(self, company: Company, start: datetime, end: datetime) -> list[NormalizedEvent]:
        published = end - timedelta(hours=6)
        if not start <= published < end:
            return []
        return [
            NormalizedEvent(
                source=self.source,
                title=f"Publicação demonstrativa sobre {company.name}",
                description=f"Publicação simulada no X sobre {company.effective_search_term}.",
                url=f"https://example.invalid/mock/x/{company.id}",
                published_at=published,
                is_mock=True,
            )
        ]
