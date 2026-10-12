from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.analyses import list_analyses
from app.web.templating import templates

router = APIRouter(tags=["Web UI"])


@router.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/ui/analyses", status_code=303)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@router.get("/ui/analyses", response_class=HTMLResponse, include_in_schema=False)
def analyses_page(request: Request, session: Annotated[Session, Depends(get_session)]):
    return templates.TemplateResponse(
        request=request,
        name="analyses.html",
        context={"analyses": list_analyses(session)},
    )
