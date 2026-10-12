"""Lógica pura da área de trabalho web: filtros, contexto da timeline e visão geral."""

from datetime import date
from typing import Any

from app.models import EventSource


def parse_timeline_filters(
    company: str | None,
    source: str | None,
    from_date: str | None,
    to_date: str | None,
) -> tuple[int | None, EventSource | None, date | None, date | None]:
    try:
        company_id = int(company) if company else None
        event_source = EventSource(source) if source else None
        start = date.fromisoformat(from_date) if from_date else None
        end = date.fromisoformat(to_date) if to_date else None
    except ValueError as exc:
        raise ValueError("Revise os filtros da timeline") from exc
    if start and end and start > end:
        raise ValueError("A data inicial deve ser anterior à final.")
    return company_id, event_source, start, end


def timeline_context(
    analysis: Any, events: list, latest_events: list | None = None, **values: Any
) -> dict[str, Any]:
    roles = {link.company_id: link.role for link in analysis.companies}
    source = events if latest_events is None else latest_events
    latest_received = max(source, key=lambda event: event.collected_at, default=None)
    return {
        "analysis": analysis,
        "events": events,
        "roles": roles,
        "latest_received": latest_received,
        **values,
    }


def overview_data(analysis: Any, events: list) -> tuple[dict[int, dict[str, Any]], list]:
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


def overview_redirect_url(
    analysis_id: int, status: str, persisted: int, start: date, end: date
) -> str:
    return (
        f"/ui/analyses/{analysis_id}?view=overview&collection_status={status}"
        f"&persisted={persisted}&from_date={start.isoformat()}&to_date={end.isoformat()}"
    )
