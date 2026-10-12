from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Event
from app.providers.analysis import AnalysisConfigurationError, AnalysisProviderError
from app.services.event_analysis import analyze_event
from app.web.templating import is_htmx, templates

router = APIRouter(tags=["Web UI"])


@router.post("/ui/events/{event_id}/analysis", response_class=HTMLResponse, include_in_schema=False)
def analyze_event_form(
    request: Request,
    event_id: int,
    session: Annotated[Session, Depends(get_session)],
    force: bool = False,
):
    error = None
    try:
        result = analyze_event(session, event_id, request.app.state.analysis_provider, force=force)
    except (AnalysisConfigurationError, AnalysisProviderError) as exc:
        result = None
        error = (
            str(exc)
            if isinstance(exc, AnalysisConfigurationError)
            else "O provider de análise não conseguiu gerar um resultado válido."
        )
    event = session.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if not is_htmx(request):
        analysis_link = next(iter(event.company.analyses), None)
        if analysis_link is None:
            return RedirectResponse(url="/ui/analyses", status_code=303)
        return RedirectResponse(
            url=f"/ui/analyses/{analysis_link.analysis_id}?view=timeline", status_code=303
        )
    return templates.TemplateResponse(
        request=request,
        name="partials/event_analysis.html",
        context={
            "event": event,
            "event_analysis": result or event.event_analysis,
            "error": error,
        },
    )
