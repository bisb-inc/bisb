import json
import logging
from calendar import monthrange
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import Event, EventSource
from app.providers.analysis import AnalysisConfigurationError, AnalysisProviderError
from app.schemas import AnalysisCreate, CollectionRequest, CompanyInput
from app.services.analyses import (
    add_competitor,
    create_analysis,
    get_analysis,
    list_analyses,
    remove_competitor,
    rename_analysis,
)
from app.services.collection import collect_analysis
from app.services.companies import update_company
from app.services.event_analysis import analyze_event
from app.services.events import analysis_events

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
router = APIRouter(tags=["Web UI"])


def _context(request: Request, **values: Any) -> dict[str, Any]:
    return {"request": request, **values}


def _month_before(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _range_for_preset(preset: str, today: date | None = None) -> tuple[date, date]:
    end = today or date.today()
    if preset == "week":
        start = end - timedelta(days=6)
    elif preset == "month":
        start = _month_before(end, 1)
    elif preset == "quarter":
        start = _month_before(end, 3)
    else:
        raise ValueError("Selecione um período válido.")
    return start, end


def _parse_range(preset: str, start_value: str | None, end_value: str | None):
    if preset != "custom":
        try:
            return _range_for_preset(preset)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        start = date.fromisoformat(start_value or "")
        end = date.fromisoformat(end_value or "")
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Informe as datas do período personalizado."
        ) from exc
    if start > end:
        raise HTTPException(status_code=422, detail="A data inicial deve ser anterior à final.")
    return start, end


def _parse_timeline_filters(company, source, from_date, to_date):
    try:
        company_id = int(company) if company else None
        event_source = EventSource(source) if source else None
        start = date.fromisoformat(from_date) if from_date else None
        end = date.fromisoformat(to_date) if to_date else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Revise os filtros da timeline") from exc
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="A data inicial deve ser anterior à final.")
    return company_id, event_source, start, end


def _load_events(session, analysis_id, company=None, source=None, start=None, end=None):
    return analysis_events(
        session,
        analysis_id,
        company,
        source.value if source else None,
        start,
        end,
    )


def _timeline_context(request, analysis, events, **values):
    roles = {link.company_id: link.role for link in analysis.companies}
    latest_received = max(events, key=lambda event: event.collected_at, default=None)
    return _context(
        request,
        analysis=analysis,
        events=events,
        roles=roles,
        latest_received=latest_received,
        **values,
    )


def _overview_data(analysis, events):
    counts: dict[int, dict[str, Any]] = {}
    for link in analysis.companies:
        counts[link.company_id] = {"company": link.company, "role": link.role, "count": 0}
    for event in events:
        if event.company_id in counts:
            counts[event.company_id]["count"] += 1
    analyzed = [
        event
        for event in events
        if event.event_analysis is not None and event.event_analysis.provider.value == "GEMINI"
    ]
    highlights = sorted(
        analyzed,
        key=lambda event: (event.event_analysis.relevance_score, event.published_at),
        reverse=True,
    )[:5]
    if not highlights:
        highlights = events[:5]
    return counts, highlights


def _wizard_state(raw: str | None) -> dict[str, Any]:
    if not raw:
        start, end = _range_for_preset("week")
        return {
            "name": "",
            "target_name": "",
            "target_website": "",
            "target_search_term": "",
            "competitors": [],
            "period": "week",
            "from_date": start.isoformat(),
            "to_date": end.isoformat(),
        }
    try:
        state = json.loads(raw)
    except TypeError, json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="O rascunho do wizard é inválido.") from None
    if not isinstance(state, dict):
        raise HTTPException(status_code=400, detail="O rascunho do wizard é inválido.")
    state.setdefault("competitors", [])
    return state


def _sync_step_state(state: dict[str, Any], form, step: int) -> None:
    if step == 1:
        state["name"] = str(form.get("name", state.get("name", ""))).strip()
    elif step == 2:
        for key in ("target_name", "target_website", "target_search_term"):
            state[key] = str(form.get(key, state.get(key, ""))).strip()
    elif step == 3:
        current = list(state.get("competitors", []))
        rebuilt = []
        for index, old in enumerate(current):
            item = {
                "name": str(form.get(f"competitor_name_{index}", old.get("name", ""))).strip(),
                "website": str(
                    form.get(f"competitor_website_{index}", old.get("website", ""))
                ).strip(),
                "search_term": str(
                    form.get(f"competitor_search_{index}", old.get("search_term", ""))
                ).strip(),
            }
            rebuilt.append(item)
        state["competitors"] = rebuilt
    elif step == 4:
        state["period"] = str(form.get("period", state.get("period", "week")))
        state["from_date"] = str(form.get("from_date", state.get("from_date", "")))
        state["to_date"] = str(form.get("to_date", state.get("to_date", "")))


def _validate_wizard_step(state: dict[str, Any], step: int) -> str | None:
    if step == 1 and not state.get("name"):
        return "Informe o nome da análise."
    if step == 2 and (not state.get("target_name") or not state.get("target_website")):
        return "Informe o nome e o site da empresa principal."
    if step == 3:
        competitors = state.get("competitors", [])
        if not competitors:
            return "Adicione ao menos um concorrente para continuar."
        if any(not item.get("name") or not item.get("website") for item in competitors):
            return "Informe nome e site para cada concorrente."
        if state.get("target_website") and any(
            item.get("website", "").rstrip("/").lower()
            == state["target_website"].rstrip("/").lower()
            for item in competitors
        ):
            return "A empresa principal não pode ser adicionada como concorrente."
        sites = [item.get("website", "").rstrip("/").casefold() for item in competitors]
        if len(set(sites)) != len(sites):
            return "Remova empresas repetidas da lista de concorrentes."
    if step == 4:
        try:
            start, end = _parse_range(
                state.get("period", ""), state.get("from_date"), state.get("to_date")
            )
        except HTTPException as exc:
            return str(exc.detail)
        state["from_date"], state["to_date"] = start.isoformat(), end.isoformat()
    return None


def _render_wizard(request, step: int, state: dict, error: str | None = None, partial=False):
    context = _context(request, step=step, state=state, error=error)
    return templates.TemplateResponse(
        request=request,
        name="partials/wizard_panel.html" if partial else "wizard.html",
        context=context,
    )


@router.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui/analyses", status_code=303)


@router.get("/ui/analyses", response_class=HTMLResponse, include_in_schema=False)
def analyses_page(request: Request, session: Annotated[Session, Depends(get_session)]):
    return templates.TemplateResponse(
        request=request,
        name="analyses.html",
        context=_context(request, analyses=list_analyses(session)),
    )


@router.get("/ui/analyses/new", response_class=HTMLResponse, include_in_schema=False)
def new_analysis_page(request: Request, step: int = 1):
    return _render_wizard(request, min(max(step, 1), 5), _wizard_state(None))


@router.post("/ui/analyses/new/step/{step}", response_class=HTMLResponse, include_in_schema=False)
async def wizard_step(request: Request, step: int):
    if step < 1 or step > 5:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    form = await request.form()
    state = _wizard_state(str(form.get("wizard_state", "")))
    _sync_step_state(state, form, step)
    intent = str(form.get("intent", "next"))
    error = None

    if step == 3 and intent in {"add_competitor", "remove_competitor"}:
        if intent == "add_competitor":
            name = str(form.get("new_competitor_name", "")).strip()
            website = str(form.get("new_competitor_website", "")).strip()
            search_term = str(form.get("new_competitor_search_term", "")).strip()
            if not name or not website:
                error = "Informe nome e site antes de adicionar o concorrente."
            else:
                state["competitors"].append(
                    {"name": name, "website": website, "search_term": search_term}
                )
        else:
            try:
                index = int(form.get("remove_index", -1))
                state["competitors"].pop(index)
            except ValueError, IndexError:
                error = "Não foi possível remover esse concorrente."
        return _render_wizard(request, 3, state, error, partial=True)

    if intent == "back":
        return _render_wizard(request, max(step - 1, 1), state)
    error = _validate_wizard_step(state, step)
    if error:
        return _render_wizard(
            request,
            step,
            state,
            error,
            partial=request.headers.get("HX-Request") == "true",
        )
    if step < 5:
        return _render_wizard(
            request,
            step + 1,
            state,
            partial=request.headers.get("HX-Request") == "true",
        )

    return _render_wizard(request, step, state)


@router.post("/ui/analyses", include_in_schema=False)
async def create_analysis_form(request: Request, session: Annotated[Session, Depends(get_session)]):
    form = await request.form()
    state = _wizard_state(str(form.get("wizard_state", "")))
    error = None
    for current_step in range(1, 5):
        error = _validate_wizard_step(state, current_step)
        if error:
            break
    if error:
        return _render_wizard(request, 5, state, error)
    start, end = _parse_range(state["period"], state["from_date"], state["to_date"])
    data = AnalysisCreate(
        name=state["name"],
        target=CompanyInput(
            name=state["target_name"],
            website=state["target_website"],
            search_term=state["target_search_term"] or None,
        ),
        competitors=[
            CompanyInput(
                name=item["name"],
                website=item["website"],
                search_term=item.get("search_term") or None,
            )
            for item in state["competitors"]
        ],
    )
    try:
        analysis = create_analysis(session, data)
    except HTTPException as exc:
        return _render_wizard(request, 5, state, str(exc.detail))
    try:
        result = collect_analysis(
            session,
            analysis.id,
            start,
            end,
            providers=request.app.state.source_providers,
        )
        status = result.status
        persisted = result.persisted
    except Exception:
        session.rollback()
        logger.exception("Falha inesperada na coleta inicial da análise %s", analysis.id)
        status, persisted = "failure", 0
    return RedirectResponse(
        url=(
            f"/ui/analyses/{analysis.id}?view=overview&collection_status={status}"
            f"&persisted={persisted}&from_date={start.isoformat()}&to_date={end.isoformat()}"
        ),
        status_code=303,
    )


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
    company_id, event_source, start, end = _parse_timeline_filters(
        company, source, from_date, to_date
    )
    analysis = get_analysis(session, analysis_id)
    events = _load_events(session, analysis_id, company_id, event_source, start, end)
    context = _timeline_context(
        request,
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
        context["company_counts"], context["highlights"] = _overview_data(analysis, events)
    template = "analysis.html" if view == "timeline" else f"workspace/{view}.html"
    return templates.TemplateResponse(request=request, name=template, context=context)


@router.get(
    "/ui/analyses/{analysis_id}/setup", response_class=HTMLResponse, include_in_schema=False
)
def analysis_setup(
    request: Request, analysis_id: int, session: Annotated[Session, Depends(get_session)]
):
    return templates.TemplateResponse(
        request=request,
        name="workspace/setup.html",
        context=_context(request, analysis=get_analysis(session, analysis_id)),
    )


@router.post("/ui/analyses/{analysis_id}/setup", include_in_schema=False)
def update_analysis_setup(
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
):
    rename_analysis(session, analysis_id, name)
    return RedirectResponse(url=f"/ui/analyses/{analysis_id}/setup?saved=1", status_code=303)


@router.post(
    "/ui/analyses/{analysis_id}/competitors", response_class=HTMLResponse, include_in_schema=False
)
def add_competitor_form(
    request: Request,
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form(min_length=1, max_length=160)],
    website: Annotated[str, Form(min_length=1, max_length=500)],
    search_term: Annotated[str | None, Form()] = None,
):
    add_competitor(
        session,
        analysis_id,
        CompanyInput(name=name, website=website, search_term=search_term or None),
    )
    return RedirectResponse(url=f"/ui/analyses/{analysis_id}/setup#competitors", status_code=303)


@router.post("/ui/analyses/{analysis_id}/competitors/{company_id}/remove", include_in_schema=False)
def remove_competitor_form(
    analysis_id: int,
    company_id: int,
    session: Annotated[Session, Depends(get_session)],
):
    remove_competitor(session, analysis_id, company_id)
    return RedirectResponse(url=f"/ui/analyses/{analysis_id}/setup#competitors", status_code=303)


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
    update_company(
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
    return RedirectResponse(
        url=f"/ui/analyses/{analysis_id}/setup?saved=1#companies", status_code=303
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
    events = _load_events(session, analysis_id, company_id, event_source, start, end)
    response = templates.TemplateResponse(
        request=request,
        name="partials/timeline.html",
        context=_timeline_context(request, analysis, events, selected_company=company_id),
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
    start, end = _parse_range(
        preset,
        str(form.get("from_date", "")),
        str(form.get("to_date", "")),
    )
    data = CollectionRequest(from_date=start, to_date=end)
    result = collect_analysis(
        session,
        analysis_id,
        data.from_date,
        data.to_date,
        providers=request.app.state.source_providers,
    )
    analysis = get_analysis(session, analysis_id)
    all_events = _load_events(session, analysis_id)
    if request.headers.get("HX-Request") != "true":
        return RedirectResponse(
            url=(
                f"/ui/analyses/{analysis_id}?view=overview&collection_status={result.status}"
                f"&persisted={result.persisted}&from_date={start.isoformat()}&to_date={end.isoformat()}"
            ),
            status_code=303,
        )
    company_counts, highlights = _overview_data(analysis, all_events)
    context = _timeline_context(
        request,
        analysis,
        highlights,
        result=result,
        from_date=start,
        to_date=end,
        view="overview",
        company_counts=company_counts,
        event_total=len(all_events),
    )
    context["latest_received"] = max(all_events, key=lambda event: event.collected_at, default=None)
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
    if request.headers.get("HX-Request") != "true":
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
            "request": request,
            "event": event,
            "event_analysis": result or event.event_analysis,
            "error": error,
        },
    )
