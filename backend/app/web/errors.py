from datetime import date

from fastapi import HTTPException

from app.models import EventSource
from app.web.periods import parse_period
from app.web.workspace import parse_timeline_filters


def period_or_422(preset: str, from_value: str | None, to_value: str | None) -> tuple[date, date]:
    try:
        return parse_period(preset, from_value, to_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def filters_or_422(
    company: str | None, source: str | None, from_date: str | None, to_date: str | None
) -> tuple[int | None, EventSource | None, date | None, date | None]:
    try:
        return parse_timeline_filters(company, source, from_date, to_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
