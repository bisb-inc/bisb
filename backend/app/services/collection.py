import logging
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Analysis, AnalysisCompany, Event
from app.providers import MockNewsProvider, MockXProvider
from app.providers.base import SourceProvider, utc_range
from app.schemas import CollectionResult, ProviderOutcome

logger = logging.getLogger(__name__)


def collect_analysis(
    session: Session,
    analysis_id: int,
    start_date: date,
    end_date: date,
    providers: list[SourceProvider] | None = None,
) -> CollectionResult:
    analysis = session.scalar(
        select(Analysis)
        .options(selectinload(Analysis.companies).selectinload(AnalysisCompany.company))
        .where(Analysis.id == analysis_id)
    )
    if analysis is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Análise não encontrada")

    providers = providers if providers is not None else [MockNewsProvider(), MockXProvider()]
    start, end = utc_range(start_date, end_date)
    outcomes: list[ProviderOutcome] = []
    total_fetched = total_persisted = 0

    for link in analysis.companies:
        company = link.company
        for provider in providers:
            outcome = ProviderOutcome(
                source=provider.source, company_id=company.id, status="success"
            )
            try:
                records = provider.fetch(company, start, end)
                outcome.fetched = len(records)
                for record in records:
                    if record.source != provider.source:
                        raise ValueError("Provider retornou fonte diferente da declarada")
                    if record.published_at.tzinfo is None:
                        raise ValueError("Provider retornou data sem timezone")
                    exists = session.scalar(
                        select(Event.id).where(
                            Event.company_id == company.id,
                            Event.source == record.source,
                            Event.url == record.url,
                        )
                    )
                    if exists is None:
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
                        outcome.persisted += 1
                session.commit()
            except Exception:
                session.rollback()
                logger.exception(
                    "Falha ao coletar fonte %s para empresa %s", provider.source, company.id
                )
                outcome.status = "failure"
                outcome.error = "Não foi possível consultar ou persistir os resultados desta fonte."
                outcome.persisted = 0
            outcomes.append(outcome)
            total_fetched += outcome.fetched
            total_persisted += outcome.persisted

    successes = sum(outcome.status == "success" for outcome in outcomes)
    if not outcomes or successes == 0:
        status = "failure"
    elif successes == len(outcomes):
        status = "success"
    else:
        status = "partial"
    return CollectionResult(
        status=status,
        providers=outcomes,
        fetched=total_fetched,
        persisted=total_persisted,
    )
