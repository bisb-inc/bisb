from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Event, EventAnalysis
from app.providers.analysis import AnalysisProvider, AnalysisProviderError


def analyze_event(
    session: Session,
    event_id: int,
    provider: AnalysisProvider,
    *,
    force: bool = False,
) -> EventAnalysis:
    event = session.scalar(
        select(Event)
        .options(joinedload(Event.company), joinedload(Event.event_analysis))
        .where(Event.id == event_id)
        .with_for_update(of=Event)
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if event.event_analysis is not None and not force:
        return event.event_analysis

    # Obter e validar a resposta antes de alterar o resultado já persistido.
    content = provider.analyze(event)
    now = datetime.now(UTC)
    current = event.event_analysis
    if current is None:
        current = EventAnalysis(event_id=event.id)
        session.add(current)
    current.summary = content.summary
    current.category = content.category
    current.competitive_impact = content.competitive_impact
    current.sentiment = content.sentiment
    current.relevance_score = content.relevance_score
    current.justification = content.justification
    current.provider = provider.provider
    current.model = provider.model
    current.is_mock = provider.provider.value == "MOCK"
    if current.created_at is None:
        current.created_at = now
    current.updated_at = now

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Uma solicitação concorrente pode ter criado o resultado primeiro.
        winner = session.get(EventAnalysis, event_id)
        if winner is not None and not force:
            return winner
        raise HTTPException(
            status_code=409, detail="Não foi possível salvar a análise concorrente"
        ) from None
    session.refresh(current)
    return current


__all__ = ["AnalysisProviderError", "analyze_event"]
