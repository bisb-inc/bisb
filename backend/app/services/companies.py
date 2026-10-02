import re
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.schemas import CompanyInput


def normalize_website(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    candidate = value.strip()
    parsed = urlsplit(candidate if "://" in candidate else f"https://{candidate}")
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    suffix = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{netloc}{path}{suffix}{fragment}" or None


def get_or_create_company(session: Session, data: CompanyInput) -> Company:
    site_key = normalize_website(data.website)
    if site_key:
        matches = session.scalars(select(Company).where(Company.website.is_not(None))).all()
        matched = next(
            (company for company in matches if normalize_website(company.website) == site_key), None
        )
        if matched:
            if (
                re.sub(r"\s+", " ", matched.name).casefold()
                != re.sub(r"\s+", " ", data.name).casefold()
            ):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "O site já está associado a outra empresa; revise o nome antes de mesclar."
                    ),
                )
            return matched

    company = Company(**data.model_dump())
    session.add(company)
    session.flush()
    return company


def update_company(session: Session, company_id: int, data: CompanyInput) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    site_key = normalize_website(data.website)
    if site_key:
        matches = session.scalars(
            select(Company).where(Company.id != company_id, Company.website.is_not(None))
        ).all()
        for other in matches:
            if normalize_website(other.website) == site_key:
                raise HTTPException(status_code=409, detail="O site já identifica outra empresa.")
    for key, value in data.model_dump().items():
        setattr(company, key, value)
    session.commit()
    session.refresh(company)
    return company
