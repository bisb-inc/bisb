from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol

from app.models import Company, EventSource


@dataclass(frozen=True)
class NormalizedEvent:
    source: EventSource
    title: str
    description: str
    url: str
    published_at: datetime
    is_mock: bool


class SourceProvider(Protocol):
    source: EventSource

    def fetch(self, company: Company, start: datetime, end: datetime) -> list[NormalizedEvent]: ...


def utc_range(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min, tzinfo=UTC), datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=UTC
    )
