from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import EventSource
from app.schemas import AnalysisCreate, CollectionRequest, CompanyInput
from app.services.analyses import (
    add_competitor,
    create_analysis,
    get_analysis,
    list_analyses,
    remove_competitor,
)
from app.services.collection import collect_analysis
from app.services.companies import update_company
from app.services.events import analysis_events

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
router = APIRouter(tags=["Web UI"])


def _templates(request: Request):
    return {"request": request, "active_tab": "monitoring"}


def _parse_timeline_filters(
    company: str | None,
    source: str | None,
    from_date: str | None,
    to_date: str | None,
):
    try:
        company_id = int(company) if company else None
        event_source = EventSource(source) if source else None
        start = date.fromisoformat(from_date) if from_date else None
        end = date.fromisoformat(to_date) if to_date else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Revise os filtros da timeline") from exc
    return company_id, event_source, start, end


@router.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui/analyses", status_code=303)


@router.get("/ui/analyses", response_class=HTMLResponse, include_in_schema=False)
def analyses_page(request: Request, session: Annotated[Session, Depends(get_session)]):
    return templates.TemplateResponse(
        request=request,
        name="analyses.html",
        context={**_templates(request), "analyses": list_analyses(session)},
    )


@router.post("/ui/analyses", include_in_schema=False)
def create_analysis_form(
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
    target_name: Annotated[str, Form(min_length=1, max_length=160)],
    target_website: Annotated[str, Form(min_length=1, max_length=500)],
):
    data = AnalysisCreate(
        name=name,
        target=CompanyInput(name=target_name, website=target_website),
    )
    analysis = create_analysis(session, data)
    return RedirectResponse(url=f"/ui/analyses/{analysis.id}", status_code=303)


@router.get("/ui/analyses/{analysis_id}", response_class=HTMLResponse, include_in_schema=False)
def analysis_page(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    tab: str = "monitoring",
    company: str | None = None,
    source: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    if tab not in {"monitoring", "profile"}:
        tab = "monitoring"
    company_id, event_source, start, end = _parse_timeline_filters(
        company, source, from_date, to_date
    )
    analysis = get_analysis(session, analysis_id)
    events = analysis_events(
        session,
        analysis_id,
        company_id,
        event_source.value if event_source else None,
        start,
        end,
    )
    sources = list(EventSource)
    return templates.TemplateResponse(
        request=request,
        name="analysis.html",
        context={
            **_templates(request),
            "analysis": analysis,
            "events": events,
            "sources": sources,
            "tab": tab,
            "selected_company": company_id,
            "selected_source": event_source,
            "from_date": start,
            "to_date": end,
        },
    )


@router.post(
    "/ui/analyses/{analysis_id}/competitors", response_class=HTMLResponse, include_in_schema=False
)
def add_competitor_form(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
    website: Annotated[str, Form(min_length=1, max_length=500)],
):
    analysis = add_competitor(session, analysis_id, CompanyInput(name=name, website=website))
    if request.headers.get("HX-Request") != "true":
        return RedirectResponse(url=f"/ui/analyses/{analysis_id}", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="partials/competitors.html",
        context={"request": request, "analysis": analysis},
    )


@router.post(
    "/ui/analyses/{analysis_id}/competitors/{company_id}/remove",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def remove_competitor_form(
    request: Request,
    analysis_id: int,
    company_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    remove_competitor(session, analysis_id, company_id)
    analysis = get_analysis(session, analysis_id)
    if request.headers.get("HX-Request") != "true":
        return RedirectResponse(url=f"/ui/analyses/{analysis_id}", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="partials/competitors.html",
        context={"request": request, "analysis": analysis},
    )


@router.post("/ui/companies/{company_id}", response_class=HTMLResponse, include_in_schema=False)
@router.put("/ui/companies/{company_id}", response_class=HTMLResponse, include_in_schema=False)
def update_company_form(
    request: Request,
    company_id: int,
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
    website: Annotated[str, Form(min_length=1, max_length=500)],
    search_term: Annotated[str | None, Form()] = None,
    market: Annotated[str | None, Form()] = None,
    products: Annotated[str | None, Form()] = None,
    audience: Annotated[str | None, Form()] = None,
    analysis_id: Annotated[int, Form()] = 0,
):
    analysis = get_analysis(session, analysis_id)
    link = next((item for item in analysis.companies if item.company_id == company_id), None)
    if link is None:
        raise HTTPException(status_code=404, detail="Empresa não vinculada à análise informada")
    company = update_company(
        session,
        company_id,
        CompanyInput(
            name=name,
            website=website,
            search_term=search_term or None,
            market=market or None,
            products=products or None,
            audience=audience or None,
        ),
    )
    if request.headers.get("HX-Request") != "true":
        return RedirectResponse(url=f"/ui/analyses/{analysis_id}?tab=profile", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="partials/company_profile.html",
        context={
            "request": request,
            "analysis": analysis,
            "profile_company": company,
            "profile_role": link.role,
        },
    )


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
    company_id, event_source, start, end = _parse_timeline_filters(
        company, source, from_date, to_date
    )
    analysis = get_analysis(session, analysis_id)
    events = analysis_events(
        session,
        analysis_id,
        company_id,
        event_source.value if event_source else None,
        start,
        end,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/timeline.html",
        context={"request": request, "analysis": analysis, "events": events},
    )


@router.post(
    "/ui/analyses/{analysis_id}/collect", response_class=HTMLResponse, include_in_schema=False
)
def collect_form(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    from_date: Annotated[date, Form()],
    to_date: Annotated[date, Form()],
):
    if from_date > to_date:
        raise HTTPException(
            status_code=422,
            detail="A data inicial deve ser anterior ou igual à data final",
        )
    data = CollectionRequest(from_date=from_date, to_date=to_date)
    result = collect_analysis(
        session,
        analysis_id,
        data.from_date,
        data.to_date,
        providers=request.app.state.source_providers,
    )
    analysis = get_analysis(session, analysis_id)
    events = analysis_events(session, analysis_id)
    template = "partials/collection_response.html"
    if request.headers.get("HX-Request") != "true":
        return RedirectResponse(url=f"/ui/analyses/{analysis_id}", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"request": request, "analysis": analysis, "result": result, "events": events},
    )
