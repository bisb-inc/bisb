"""Testes de caracterização da Web Layer (rede de segurança da refatoração).

Fixam o comportamento ATUAL de ``app/web`` para que a refatoração prove paridade.
"""

import json
from datetime import UTC, datetime

import pytest

from app.models import Event, EventSource
from app.providers.analysis import MockAnalysisProvider

EMPTY_WIZARD_STATE = {
    "name": "",
    "target_name": "",
    "target_website": "",
    "target_search_term": "",
    "competitors": [],
    "period": "week",
    "from_date": "",
    "to_date": "",
}

# Snapshot literal de (path, métodos ordenados) das rotas Web.
EXPECTED_WEB_ROUTES = [
    ("/", ["GET"]),
    ("/login", ["GET"]),
    ("/ui/analyses", ["GET"]),
    ("/ui/analyses", ["POST"]),
    ("/ui/analyses/new", ["GET"]),
    ("/ui/analyses/new/step/{step}", ["POST"]),
    ("/ui/analyses/{analysis_id}", ["GET"]),
    ("/ui/analyses/{analysis_id}/collect", ["POST"]),
    ("/ui/analyses/{analysis_id}/competitors", ["POST"]),
    ("/ui/analyses/{analysis_id}/competitors/{company_id}/remove", ["POST"]),
    ("/ui/analyses/{analysis_id}/setup", ["GET"]),
    ("/ui/analyses/{analysis_id}/setup", ["POST"]),
    ("/ui/analyses/{analysis_id}/timeline", ["GET"]),
    ("/ui/companies/{company_id}", ["POST"]),
    ("/ui/events/{event_id}/analysis", ["POST"]),
]


def _create_analysis(client) -> dict:
    response = client.post(
        "/analyses",
        json={
            "name": "Concorrência financeira",
            "target": {"name": "Alfa Bank", "website": "https://www.alfa.example/"},
        },
    )
    assert response.status_code == 201
    return response.json()


def _add_event(functional_db, company_id: int) -> int:
    with functional_db() as session:
        event = Event(
            company_id=company_id,
            source=EventSource.GNEWS,
            title="Alfa lança novo produto",
            description="Descrição do acontecimento.",
            url="https://news.example/alfa",
            is_mock=False,
            published_at=datetime.now(UTC),
            collected_at=datetime.now(UTC),
        )
        session.add(event)
        session.commit()
        return event.id


def _target_company_id(client, analysis_id: int) -> int:
    body = client.get(f"/analyses/{analysis_id}").json()
    return body["companies"][0]["company"]["id"]


def _flatten_routes(routes):
    # FastAPI recente agrupa include_router em _IncludedRouter (sem path/methods).
    # Percorremos recursivamente para obter as rotas reais, mesmo que a Web seja
    # dividida em sub-routers durante a refatoração.
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            yield from _flatten_routes(inner.routes)
        elif hasattr(route, "methods") and hasattr(route, "path"):
            yield route


def test_web_routes_snapshot(functional_client):
    web_routes = sorted(
        (route.path, sorted(route.methods - {"HEAD"}))
        for route in _flatten_routes(functional_client.app.routes)
        if route.path.startswith("/ui") or route.path in {"/", "/login"}
    )
    assert web_routes == sorted(EXPECTED_WEB_ROUTES)


def test_collect_without_htmx_redirects_to_overview(functional_client):
    analysis_id = _create_analysis(functional_client)["id"]
    response = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect",
        data={"period": "week"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith(f"/ui/analyses/{analysis_id}?")
    assert "view=overview&collection_status=" in location
    assert "from_date=" in location
    assert "to_date=" in location


def test_event_analysis_without_htmx_redirects_to_timeline(functional_client, functional_db):
    analysis_id = _create_analysis(functional_client)["id"]
    company_id = _target_company_id(functional_client, analysis_id)
    event_id = _add_event(functional_db, company_id)
    functional_client.app.state.analysis_provider = MockAnalysisProvider()
    response = functional_client.post(f"/ui/events/{event_id}/analysis", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/ui/analyses/{analysis_id}?view=timeline"


@pytest.mark.parametrize(
    "query",
    [
        "company=abc",
        "source=INVALIDA",
        "from_date=nao-e-data",
        "from_date=2026-02-01&to_date=2026-01-01",
    ],
)
def test_timeline_invalid_filters_return_422(functional_client, query):
    analysis_id = _create_analysis(functional_client)["id"]
    response = functional_client.get(f"/ui/analyses/{analysis_id}?view=timeline&{query}")
    assert response.status_code == 422


@pytest.mark.parametrize(
    "data",
    [
        {"period": "custom", "from_date": "nao-e-data", "to_date": "2026-01-01"},
        {"period": "custom", "from_date": "2026-01-01"},
        {"period": "custom"},
        {"period": "custom", "from_date": "2026-02-01", "to_date": "2026-01-01"},
        {"period": "invalido"},
    ],
)
def test_collect_invalid_period_returns_422(functional_client, data):
    analysis_id = _create_analysis(functional_client)["id"]
    response = functional_client.post(f"/ui/analyses/{analysis_id}/collect", data=data)
    assert response.status_code == 422


def test_wizard_back_returns_to_previous_step(functional_client):
    response = functional_client.post(
        "/ui/analyses/new/step/2",
        data={"wizard_state": json.dumps(EMPTY_WIZARD_STATE), "intent": "back"},
    )
    assert response.status_code == 200
    assert "Nome da análise" in response.text or 'name="name"' in response.text


@pytest.mark.parametrize("step", [0, 6])
def test_wizard_unknown_step_returns_404(functional_client, step):
    response = functional_client.post(
        f"/ui/analyses/new/step/{step}",
        data={"wizard_state": json.dumps(EMPTY_WIZARD_STATE)},
    )
    assert response.status_code == 404


def test_wizard_invalid_state_json_returns_400(functional_client):
    response = functional_client.post(
        "/ui/analyses/new/step/1", data={"wizard_state": "{nao-e-json", "intent": "next"}
    )
    assert response.status_code == 400


def test_legacy_tab_param_is_ignored(functional_client):
    analysis_id = _create_analysis(functional_client)["id"]
    overview = functional_client.get(f"/ui/analyses/{analysis_id}?view=overview")
    for tab in ("profile", "monitoring"):
        response = functional_client.get(
            f"/ui/analyses/{analysis_id}?tab={tab}", follow_redirects=False
        )
        assert response.status_code == 200
        assert response.text == overview.text


def test_new_analysis_ignores_step_param(functional_client):
    default = functional_client.get("/ui/analyses/new")
    assert functional_client.get("/ui/analyses/new?step=3").text == default.text


def test_web_company_update_rejects_put(functional_client):
    response = functional_client.put("/ui/companies/1", data={"name": "A", "website": "a.example"})
    assert response.status_code == 405
