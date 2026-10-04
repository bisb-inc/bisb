from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Company, Event
from app.services.analyses import get_analysis


def analysis_events(
    session: Session,
    analysis_id: int,
    company_id: int | None = None,
    source: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Event]:
    analysis = get_analysis(session, analysis_id)
    linked_ids = [link.company_id for link in analysis.companies]
    if company_id is not None and company_id not in linked_ids:
        raise HTTPException(status_code=422, detail="A empresa não pertence a esta análise")
    statement = (
        select(Event)
        .options(joinedload(Event.company), joinedload(Event.event_analysis))
        .where(Event.company_id.in_(linked_ids))
    )
    if company_id is not None:
        statement = statement.where(Event.company_id == company_id)
    if source is not None:
        statement = statement.where(Event.source == source.upper())
    if from_date is not None:
        statement = statement.where(
            Event.published_at >= datetime.combine(from_date, time.min, tzinfo=UTC)
        )
    if to_date is not None:
        statement = statement.where(
            Event.published_at < datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=UTC)
        )
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=422, detail="A data inicial deve ser anterior ou igual à data final"
        )
    return list(
        session.scalars(
            statement.order_by(Event.published_at.desc(), Event.collected_at.desc())
        ).all()
    )


def company_events(session: Session, company_id: int) -> list[Event]:
    if session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return list(
        session.scalars(
            select(Event)
            .where(Event.company_id == company_id)
            .order_by(Event.published_at.desc(), Event.collected_at.desc())
        ).all()
    )
