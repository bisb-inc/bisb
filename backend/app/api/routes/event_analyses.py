from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import EventAnalysis
from app.providers.analysis import AnalysisConfigurationError, AnalysisProviderError
from app.schemas import EventAnalysisRead
from app.services.event_analysis import analyze_event

router = APIRouter(tags=["Análise de eventos"])


@router.post("/events/{event_id}/analysis", response_model=EventAnalysisRead)
def analyze(
    request: Request,
    event_id: int,
    session: Annotated[Session, Depends(get_session)],
    force: Annotated[bool, Query()] = False,
):
    try:
        return analyze_event(session, event_id, request.app.state.analysis_provider, force=force)
    except AnalysisConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except AnalysisProviderError:
        raise HTTPException(
            status_code=502, detail="O provider de análise não conseguiu gerar um resultado válido."
        ) from None


@router.get("/events/{event_id}/analysis", response_model=EventAnalysisRead)
def get_analysis(event_id: int, session: Annotated[Session, Depends(get_session)]) -> EventAnalysis:
    result = session.get(EventAnalysis, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Análise do evento não encontrada")
    return result
