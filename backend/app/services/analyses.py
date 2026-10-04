from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Analysis, AnalysisCompany, CompanyRole
from app.schemas import AnalysisCreate, CompanyInput
from app.services.companies import get_or_create_company


def _analysis_query():
    return select(Analysis).options(
        selectinload(Analysis.companies).selectinload(AnalysisCompany.company)
    )


def list_analyses(session: Session) -> list[Analysis]:
    return list(
        session.scalars(
            _analysis_query().order_by(Analysis.created_at.desc(), Analysis.id.desc())
        ).all()
    )


def get_analysis(session: Session, analysis_id: int) -> Analysis:
    analysis = session.scalar(_analysis_query().where(Analysis.id == analysis_id))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada")
    return analysis


def rename_analysis(session: Session, analysis_id: int, name: str) -> Analysis:
    analysis = get_analysis(session, analysis_id)
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="O nome da análise é obrigatório")
    analysis.name = cleaned
    session.commit()
    return get_analysis(session, analysis_id)


def create_analysis(session: Session, data: AnalysisCreate) -> Analysis:
    try:
        target = get_or_create_company(session, data.target)
        analysis = Analysis(name=data.name)
        session.add(analysis)
        analysis.companies.append(AnalysisCompany(company=target, role=CompanyRole.TARGET))
        for competitor_data in data.competitors:
            competitor = get_or_create_company(session, competitor_data)
            if competitor.id == target.id:
                raise HTTPException(
                    status_code=422, detail="TARGET não pode também ser concorrente."
                )
            analysis.companies.append(
                AnalysisCompany(company=competitor, role=CompanyRole.COMPETITOR)
            )
        session.commit()
        return get_analysis(session, analysis.id)
    except Exception:
        session.rollback()
        raise


def add_competitor(session: Session, analysis_id: int, data: CompanyInput) -> Analysis:
    analysis = get_analysis(session, analysis_id)
    company = get_or_create_company(session, data)
    if any(
        link.company_id == company.id and link.role == CompanyRole.TARGET
        for link in analysis.companies
    ):
        raise HTTPException(status_code=422, detail="A empresa-alvo não pode ser concorrente.")
    if not any(link.company_id == company.id for link in analysis.companies):
        analysis.companies.append(AnalysisCompany(company=company, role=CompanyRole.COMPETITOR))
    session.commit()
    return get_analysis(session, analysis.id)


def remove_competitor(session: Session, analysis_id: int, company_id: int) -> None:
    analysis = get_analysis(session, analysis_id)
    link = next((item for item in analysis.companies if item.company_id == company_id), None)
    if link is None:
        raise HTTPException(status_code=404, detail="Empresa não vinculada a esta análise")
    if link.role == CompanyRole.TARGET:
        raise HTTPException(status_code=409, detail="A empresa TARGET não pode ser removida.")
    analysis.companies.remove(link)
    session.commit()
