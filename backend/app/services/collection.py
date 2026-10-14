import logging
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Event
from app.providers import MockNewsProvider, MockXProvider
from app.providers.base import NormalizedEvent, SourceProvider, utc_range
from app.schemas import CollectionResult, ProviderOutcome
from app.services.analyses import get_analysis

logger = logging.getLogger(__name__)

PROVIDER_FAILURE_MESSAGE = "Não foi possível consultar ou persistir os resultados desta fonte."


def collect_analysis(
    session: Session,
    analysis_id: int,
    start_date: date,
    end_date: date,
    providers: list[SourceProvider] | None = None,
) -> CollectionResult:
    analysis = get_analysis(session, analysis_id)
    providers = providers if providers is not None else [MockNewsProvider(), MockXProvider()]
    start, end = utc_range(start_date, end_date)

    outcomes: list[ProviderOutcome] = []
    for link in analysis.companies:
        company = link.company
        for provider in providers:
            outcomes.append(_collect_pair(session, company, provider, start, end))

    return CollectionResult(
        status=_collection_status(outcomes),
        providers=outcomes,
        fetched=sum(outcome.fetched for outcome in outcomes),
        persisted=sum(outcome.persisted for outcome in outcomes),
    )


def _collect_pair(
    session: Session,
    company: Company,
    provider: SourceProvider,
    start: datetime,
    end: datetime,
) -> ProviderOutcome:
    """Coleta um par empresa/provider em transação própria; uma falha descarta só este par."""
    outcome = ProviderOutcome(source=provider.source, company_id=company.id, status="success")
    try:
        records = provider.fetch(company, start, end)
        outcome.fetched = len(records)
        _validate_records(records, provider)
        outcome.persisted = _add_new_events(session, company, records)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Falha ao coletar fonte %s para empresa %s", provider.source, company.id)
        outcome.status = "failure"
        outcome.error = PROVIDER_FAILURE_MESSAGE
        outcome.persisted = 0
    return outcome


def _validate_records(records: list[NormalizedEvent], provider: SourceProvider) -> None:
    for record in records:
        if record.source != provider.source:
            raise ValueError("Provider retornou fonte diferente da declarada")
        if record.published_at.tzinfo is None:
            raise ValueError("Provider retornou data sem timezone")


def _add_new_events(session: Session, company: Company, records: list[NormalizedEvent]) -> int:
    added = 0
    for record in records:
        # A consulta dispara o autoflush, então duplicatas do mesmo lote também são detectadas.
        exists = session.scalar(
            select(Event.id).where(
                Event.company_id == company.id,
                Event.source == record.source,
                Event.url == record.url,
            )
        )
        if exists is not None:
            continue
        session.add(
            Event(
                company_id=company.id,
                source=record.source,
                title=record.title,
                description=record.description,
                url=record.url,
                is_mock=record.is_mock,
                published_at=record.published_at.astimezone(UTC),
                collected_at=datetime.now(UTC),
            )
        )
        added += 1
    return added


def _collection_status(outcomes: list[ProviderOutcome]) -> str:
    successes = sum(outcome.status == "success" for outcome in outcomes)
    if successes == 0:
        return "failure"
    if successes == len(outcomes):
        return "success"
    return "partial"
