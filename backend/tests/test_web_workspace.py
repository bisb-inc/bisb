from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.models import EventSource
from app.web.workspace import (
    overview_data,
    overview_redirect_url,
    parse_timeline_filters,
    timeline_context,
)


def _source_value() -> str:
    return next(iter(EventSource)).value


def test_parse_filters_empty():
    assert parse_timeline_filters(None, None, None, None) == (None, None, None, None)
    assert parse_timeline_filters("", "", "", "") == (None, None, None, None)


def test_parse_filters_valid():
    source = next(iter(EventSource))
    result = parse_timeline_filters("3", source.value, "2026-01-01", "2026-01-31")
    assert result == (3, source, date(2026, 1, 1), date(2026, 1, 31))


@pytest.mark.parametrize(
    "args",
    [
        ("abc", None, None, None),
        (None, "NAO_EXISTE", None, None),
        (None, None, "2026-13-40", None),
        (None, None, None, "ontem"),
    ],
)
def test_parse_filters_invalid(args):
    with pytest.raises(ValueError, match="Revise os filtros da timeline"):
        parse_timeline_filters(*args)


def test_parse_filters_start_after_end():
    with pytest.raises(ValueError, match="A data inicial deve ser anterior à final."):
        parse_timeline_filters(None, None, "2026-02-01", "2026-01-01")


def _analysis(*links):
    return SimpleNamespace(companies=list(links))


def _link(company_id, role="COMPETITOR", company=None):
    return SimpleNamespace(company_id=company_id, role=role, company=company or f"c{company_id}")


def _event(company_id=1, collected=None, published=None, analysis=None):
    return SimpleNamespace(
        company_id=company_id,
        collected_at=collected or datetime(2026, 1, 1),
        published_at=published or datetime(2026, 1, 1),
        event_analysis=analysis,
    )


def _gemini(score, provider="GEMINI"):
    return SimpleNamespace(provider=SimpleNamespace(value=provider), relevance_score=score)


def test_timeline_context_roles_and_latest_from_events():
    old, new = _event(collected=datetime(2026, 1, 1)), _event(collected=datetime(2026, 2, 1))
    analysis = _analysis(_link(1, "TARGET"), _link(2))
    ctx = timeline_context(analysis, [old, new], foo="bar")
    assert ctx == {
        "analysis": analysis,
        "events": [old, new],
        "roles": {1: "TARGET", 2: "COMPETITOR"},
        "latest_received": new,
        "foo": "bar",
    }
    assert "request" not in ctx


def test_timeline_context_latest_from_latest_events():
    shown = _event(collected=datetime(2026, 1, 1))
    latest = _event(collected=datetime(2026, 3, 1))
    ctx = timeline_context(_analysis(), [shown], latest_events=[shown, latest])
    assert ctx["latest_received"] is latest


def test_timeline_context_empty():
    assert timeline_context(_analysis(), [])["latest_received"] is None
    assert timeline_context(_analysis(), [], latest_events=[])["latest_received"] is None


def test_overview_counts_per_company():
    analysis = _analysis(_link(1), _link(2))
    events = [_event(1), _event(1), _event(2), _event(99)]
    counts, _ = overview_data(analysis, events)
    assert counts[1]["count"] == 2
    assert counts[2]["count"] == 1
    assert set(counts) == {1, 2}


def test_overview_highlights_only_gemini_sorted():
    a = _event(analysis=_gemini(5), published=datetime(2026, 1, 1))
    b = _event(analysis=_gemini(9), published=datetime(2026, 1, 1))
    c = _event(analysis=_gemini(9), published=datetime(2026, 2, 1))
    other = _event(analysis=_gemini(10, provider="OUTRO"))
    _, highlights = overview_data(_analysis(_link(1)), [a, other, b, c])
    assert highlights == [c, b, a]


def test_overview_highlights_fallback_and_limit():
    events = [_event() for _ in range(8)]
    _, highlights = overview_data(_analysis(_link(1)), events)
    assert highlights == events[:5]
    analyzed = [_event(analysis=_gemini(i)) for i in range(8)]
    _, highlights = overview_data(_analysis(_link(1)), analyzed)
    assert len(highlights) == 5


def test_overview_redirect_url():
    url = overview_redirect_url(7, "success", 12, date(2026, 1, 1), date(2026, 1, 7))
    assert url == (
        "/ui/analyses/7?view=overview&collection_status=success"
        "&persisted=12&from_date=2026-01-01&to_date=2026-01-07"
    )
