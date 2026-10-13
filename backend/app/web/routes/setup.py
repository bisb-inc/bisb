from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas import CompanyInput
from app.services.analyses import (
    add_competitor,
    get_analysis,
    remove_competitor,
    rename_analysis,
)
from app.services.companies import update_company
from app.web.templating import templates

router = APIRouter(tags=["Web UI"])


@router.get(
    "/ui/analyses/{analysis_id}/setup", response_class=HTMLResponse, include_in_schema=False
)
def analysis_setup(
    request: Request, analysis_id: int, session: Annotated[Session, Depends(get_session)]
):
    return templates.TemplateResponse(
        request=request,
        name="workspace/setup.html",
        context={"analysis": get_analysis(session, analysis_id)},
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
