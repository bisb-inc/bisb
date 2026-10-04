from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models import EventSource
from app.schemas import (
    AnalysisCreate,
    AnalysisRead,
    CollectionRequest,
    CollectionResult,
    CompanyInput,
    CompanyRead,
    EventRead,
)
from app.services.analyses import (
    add_competitor,
    create_analysis,
    get_analysis,
    list_analyses,
    remove_competitor,
)
from app.services.collection import collect_analysis
from app.services.companies import update_company
from app.services.events import analysis_events, company_events

router = APIRouter(tags=["Análises"])


@router.post("/analyses", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
def create(data: AnalysisCreate, session: Annotated[Session, Depends(get_session)]):
    return create_analysis(session, data)


@router.get("/analyses", response_model=list[AnalysisRead])
def list_all(session: Annotated[Session, Depends(get_session)]):
    return list_analyses(session)


@router.get("/analyses/{analysis_id}", response_model=AnalysisRead)
def get_one(analysis_id: int, session: Annotated[Session, Depends(get_session)]):
    return get_analysis(session, analysis_id)


@router.post("/analyses/{analysis_id}/companies", response_model=AnalysisRead)
def add_company(
    analysis_id: int, data: CompanyInput, session: Annotated[Session, Depends(get_session)]
):
    return add_competitor(session, analysis_id, data)


@router.delete(
    "/analyses/{analysis_id}/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_company(
    analysis_id: int, company_id: int, session: Annotated[Session, Depends(get_session)]
):
    remove_competitor(session, analysis_id, company_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/companies/{company_id}", response_model=CompanyRead)
def edit_company(
    company_id: int, data: CompanyInput, session: Annotated[Session, Depends(get_session)]
):
    return CompanyRead.model_validate(update_company(session, company_id, data))


@router.post("/analyses/{analysis_id}/collect", response_model=CollectionResult)
def collect(
    request: Request,
    analysis_id: int,
    data: CollectionRequest,
    session: Annotated[Session, Depends(get_session)],
):
    return collect_analysis(
        session,
        analysis_id,
        data.from_date,
        data.to_date,
        providers=request.app.state.source_providers,
    )


@router.get("/analyses/{analysis_id}/events", response_model=list[EventRead])
def list_events(
    analysis_id: int,
    session: Annotated[Session, Depends(get_session)],
    company: int | None = None,
    source: EventSource | None = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
):
    return analysis_events(
        session, analysis_id, company, source.value if source else None, from_date, to_date
    )


@router.get("/companies/{company_id}/events", response_model=list[EventRead])
def events_for_company(company_id: int, session: Annotated[Session, Depends(get_session)]):
    return company_events(session, company_id)
