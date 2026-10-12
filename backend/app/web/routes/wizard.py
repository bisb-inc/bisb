import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas import AnalysisCreate, CompanyInput
from app.services.analyses import create_analysis
from app.services.collection import collect_analysis
from app.web import wizard
from app.web.errors import period_or_422
from app.web.templating import is_htmx, templates
from app.web.workspace import overview_redirect_url

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Web UI"])


def _render_wizard(request, step: int, state: dict, error: str | None = None, partial=False):
    return templates.TemplateResponse(
        request=request,
        name="partials/wizard_panel.html" if partial else "wizard.html",
        context={"step": step, "state": state, "error": error},
    )


def _load_state_or_400(raw: str | None) -> dict:
    try:
        return wizard.load_state(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.get("/ui/analyses/new", response_class=HTMLResponse, include_in_schema=False)
def new_analysis_page(request: Request):
    return _render_wizard(request, 1, wizard.new_state())


@router.post("/ui/analyses/new/step/{step}", response_class=HTMLResponse, include_in_schema=False)
async def wizard_step(request: Request, step: int):
    if step < 1 or step > 5:
        raise HTTPException(status_code=404, detail="Etapa não encontrada")
    form = await request.form()
    state = _load_state_or_400(str(form.get("wizard_state", "")))
    wizard.sync_step(state, form, step)
    intent = str(form.get("intent", "next"))

    if step == 3 and intent in {"add_competitor", "remove_competitor"}:
        error = wizard.apply_competitor_intent(state, form, intent)
        return _render_wizard(request, 3, state, error, partial=True)

    if intent == "back":
        return _render_wizard(request, max(step - 1, 1), state)
    error = wizard.validate_step(state, step)
    if error:
        return _render_wizard(request, step, state, error, partial=is_htmx(request))
    if step < 5:
        return _render_wizard(request, step + 1, state, partial=is_htmx(request))

    return _render_wizard(request, step, state)


@router.post("/ui/analyses", include_in_schema=False)
async def create_analysis_form(request: Request, session: Annotated[Session, Depends(get_session)]):
    form = await request.form()
    state = _load_state_or_400(str(form.get("wizard_state", "")))
    error = None
    for current_step in range(1, 5):
        error = wizard.validate_step(state, current_step)
        if error:
            break
    if error:
        return _render_wizard(request, 5, state, error)
    start, end = period_or_422(state["period"], state["from_date"], state["to_date"])
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
        url=overview_redirect_url(analysis.id, status, persisted, start, end),
        status_code=303,
    )
