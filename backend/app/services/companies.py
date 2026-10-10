import re
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.schemas import CompanyInput
from app.services.errors import ConflictError, NotFoundError


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


def _find_company_by_website(
    session: Session, website: str | None, *, exclude_id: int | None = None
) -> Company | None:
    """Retorna a empresa identificada pelo mesmo site normalizado, se houver."""
    site_key = normalize_website(website)
    if site_key is None:
        return None
    statement = select(Company).where(Company.website.is_not(None))
    if exclude_id is not None:
        statement = statement.where(Company.id != exclude_id)
    return next(
        (
            company
            for company in session.scalars(statement).all()
            if normalize_website(company.website) == site_key
        ),
        None,
    )


def _name_key(name: str) -> str:
    return re.sub(r"\s+", " ", name).casefold()


def get_or_create_company(session: Session, data: CompanyInput) -> Company:
    matched = _find_company_by_website(session, data.website)
    if matched:
        if _name_key(matched.name) != _name_key(data.name):
            raise ConflictError(
                "O site já está associado a outra empresa; revise o nome antes de mesclar."
            )
        return matched

    company = Company(**data.model_dump())
    session.add(company)
    session.flush()
    return company


def update_company(session: Session, company_id: int, data: CompanyInput) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise NotFoundError("Empresa não encontrada")
    if _find_company_by_website(session, data.website, exclude_id=company_id):
        raise ConflictError("O site já identifica outra empresa.")
    for key, value in data.model_dump().items():
        setattr(company, key, value)
    session.commit()
    session.refresh(company)
    return company
