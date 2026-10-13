from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import EventSource
from app.services.analyses import get_analysis
from app.services.collection import collect_analysis
from app.services.events import analysis_events
from app.web import workspace
from app.web.errors import filters_or_422, period_or_422
from app.web.templating import is_htmx, templates

router = APIRouter(tags=["Web UI"])


@router.get("/ui/analyses/{analysis_id}", response_class=HTMLResponse, include_in_schema=False)
def analysis_page(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    view: str = "overview",
    tab: str | None = None,
    company: str | None = None,
    source: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    collection_status: str | None = None,
    persisted: int | None = None,
):
    if tab == "profile":
        return RedirectResponse(url=f"/ui/analyses/{analysis_id}/setup", status_code=303)
    if tab == "monitoring" and view == "overview":
        view = "timeline"
    if view not in {"overview", "timeline", "companies"}:
        view = "overview"
    company_id, event_source, start, end = filters_or_422(company, source, from_date, to_date)
    analysis = get_analysis(session, analysis_id)
    events = analysis_events(
        session, analysis_id, company_id, event_source.value if event_source else None, start, end
    )
    context = workspace.timeline_context(
        analysis,
        events,
        view=view,
        sources=list(EventSource),
        selected_company=company_id,
        selected_source=event_source,
        from_date=start,
        to_date=end,
        collection_status=collection_status,
        persisted=persisted,
        company_counts=None,
        highlights=None,
    )
    if view == "overview":
        context["company_counts"], context["highlights"] = workspace.overview_data(analysis, events)
    template = "analysis.html" if view == "timeline" else f"workspace/{view}.html"
    return templates.TemplateResponse(request=request, name=template, context=context)


@router.get(
    "/ui/analyses/{analysis_id}/timeline", response_class=HTMLResponse, include_in_schema=False
)
def timeline_fragment(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    company: str | None = None,
    source: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    company_id, event_source, start, end = filters_or_422(company, source, from_date, to_date)
    analysis = get_analysis(session, analysis_id)
    events = analysis_events(
        session, analysis_id, company_id, event_source.value if event_source else None, start, end
    )
    response = templates.TemplateResponse(
        request=request,
        name="partials/timeline.html",
        context=workspace.timeline_context(analysis, events, selected_company=company_id),
    )
    query = {key: value for key, value in request.query_params.items() if value}
    query["view"] = "timeline"
    response.headers["HX-Push-Url"] = (
        f"/ui/analyses/{analysis_id}?{urlencode(query)}"
        if query
        else f"/ui/analyses/{analysis_id}?view=timeline"
    )
    return response


@router.post(
    "/ui/analyses/{analysis_id}/collect", response_class=HTMLResponse, include_in_schema=False
)
async def collect_form(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    form = await request.form()
    preset = str(form.get("period", "custom"))
    start, end = period_or_422(
        preset,
        str(form.get("from_date", "")),
        str(form.get("to_date", "")),
    )
    result = collect_analysis(
        session,
        analysis_id,
        start,
        end,
        providers=request.app.state.source_providers,
    )
    analysis = get_analysis(session, analysis_id)
    all_events = analysis_events(session, analysis_id, None, None, None, None)
    if not is_htmx(request):
        return RedirectResponse(
            url=workspace.overview_redirect_url(
                analysis_id, result.status, result.persisted, start, end
            ),
            status_code=303,
        )
    company_counts, highlights = workspace.overview_data(analysis, all_events)
    context = workspace.timeline_context(
        analysis,
        highlights,
        latest_events=all_events,
        result=result,
        from_date=start,
        to_date=end,
        view="overview",
        company_counts=company_counts,
        event_total=len(all_events),
    )
    response = templates.TemplateResponse(
        request=request,
        name="partials/collection_response.html",
        context=context,
    )
    response.headers["HX-Push-Url"] = (
        f"/ui/analyses/{analysis_id}?view=overview&from_date={start.isoformat()}"
        f"&to_date={end.isoformat()}"
    )
    return response
