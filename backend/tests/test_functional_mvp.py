import json
import re
from datetime import UTC, date, datetime, timedelta
from html import unescape

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Analysis, AnalysisCompany, Company, CompanyRole, Event, EventSource
from app.providers.mock import MockXProvider
from app.services.collection import collect_analysis


def _analysis_payload(name="Concorrência financeira"):
    return {
        "name": name,
        "target": {"name": "Alfa Bank", "website": "https://www.alfa.example/"},
    }


def _wizard_state(page_text):
    value = re.search(r'name="wizard_state" value="([^"]*)"', page_text).group(1)
    return json.loads(unescape(value))


def test_ui_flow_create_add_collect_deduplicate_and_filter(functional_client, functional_db):
    analyses_page = functional_client.get("/ui/analyses")
    assert analyses_page.status_code == 200
    assert "Nova análise" in analyses_page.text
    assert "target_name" not in analyses_page.text
    assert functional_client.get("/ui/analyses/new").status_code == 200
    state = {
        "name": "",
        "target_name": "",
        "target_website": "",
        "target_search_term": "",
        "competitors": [],
        "period": "week",
        "from_date": "",
        "to_date": "",
    }
    step = functional_client.post(
        "/ui/analyses/new/step/1",
        data={"wizard_state": json.dumps(state), "name": "Bancos digitais", "intent": "next"},
    )
    assert "Empresa principal / TARGET" in step.text
    state = _wizard_state(step.text)
    step = functional_client.post(
        "/ui/analyses/new/step/2",
        data={
            "wizard_state": json.dumps(state),
            "target_name": "Alfa Bank",
            "target_website": "https://alfa.example",
            "target_search_term": "",
            "intent": "next",
        },
    )
    state = _wizard_state(step.text)
    added_competitor = functional_client.post(
        "/ui/analyses/new/step/3",
        data={
            "wizard_state": json.dumps(state),
            "new_competitor_name": "Beta Finance",
            "new_competitor_website": "https://beta.example",
            "new_competitor_search_term": "Beta",
            "intent": "add_competitor",
        },
        headers={"HX-Request": "true"},
    )
    assert "Beta Finance" in added_competitor.text
    state = _wizard_state(added_competitor.text)
    step = functional_client.post(
        "/ui/analyses/new/step/3",
        data={"wizard_state": json.dumps(state), "intent": "next"},
    )
    assert "período inicial" in step.text
    state = _wizard_state(step.text)
    step = functional_client.post(
        "/ui/analyses/new/step/4",
        data={"wizard_state": json.dumps(state), "period": "week", "intent": "next"},
    )
    assert "Criar e analisar" in step.text
    state = _wizard_state(step.text)
    response = functional_client.post(
        "/ui/analyses", data={"wizard_state": json.dumps(state)}, follow_redirects=False
    )
    assert response.status_code == 303
    analysis_id = int(re.search(r"/ui/analyses/(\d+)", response.headers["location"]).group(1))
    page = functional_client.get(response.headers["location"])
    assert page.status_code == 200
    assert "Visão geral" in page.text
    assert "Alfa Bank" in page.text
    assert "Coleta inicial concluída" in page.text
    assert "Atualizar monitoramento" in page.text
    assert "Demonstração · mock" in page.text
    assert functional_client.get("/static/js/htmx.min.js").status_code == 200
    assert functional_client.get("/static/js/app.js").status_code == 200
    assert functional_client.get("/static/css/app.css").status_code == 200

    profile = functional_client.get(f"/ui/analyses/{analysis_id}/setup")
    assert profile.status_code == 200
    assert 'name="market"' in profile.text
    assert 'name="search_term"' in profile.text
    renamed = functional_client.post(
        f"/ui/analyses/{analysis_id}/setup",
        data={"name": "Bancos digitais · Brasil"},
        follow_redirects=False,
    )
    assert renamed.status_code == 303
    assert (
        "Bancos digitais · Brasil"
        in functional_client.get(f"/ui/analyses/{analysis_id}/setup").text
    )
    updated = functional_client.put(
        "/ui/companies/1",
        data={
            "analysis_id": analysis_id,
            "name": "Alfa Bank",
            "website": "https://alfa.example",
            "market": "Fintech",
        },
        follow_redirects=False,
    )
    assert updated.status_code == 303
    assert "Fintech" in functional_client.get(f"/ui/analyses/{analysis_id}/setup").text

    today = date.today()
    data = {
        "period": "custom",
        "from_date": (today - timedelta(days=7)).isoformat(),
        "to_date": today.isoformat(),
    }
    collected = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect",
        data=data,
        headers={"HX-Request": "true"},
    )
    assert collected.status_code == 200
    assert "Coleta concluída" in collected.text
    assert "Demonstração · mock" in collected.text
    assert 'hx-swap-oob="outerHTML"' in collected.text
    assert "from_date=" in collected.headers["HX-Push-Url"]
    with functional_db() as session:
        assert session.scalar(select(func.count(Event.id))) == 4
        assert session.scalar(select(func.count(Event.id)).where(Event.is_mock.is_(True))) == 4
        events = list(session.scalars(select(Event)))
        assert all(event.published_at.tzinfo is not None for event in events)
        assert all(event.collected_at.tzinfo is not None for event in events)

    repeated = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect", data=data, headers={"HX-Request": "true"}
    )
    assert "0 evento(s) novo(s) persistido(s)" in repeated.text
    assert (
        functional_client.get(f"/ui/analyses/{analysis_id}?view=timeline&source=X").status_code
        == 200
    )
    filtered = functional_client.get(f"/ui/analyses/{analysis_id}?view=timeline&source=X")
    assert "Publicação demonstrativa" in filtered.text
    assert "Atualização de mercado" not in filtered.text
    htmx_filtered = functional_client.get(
        f"/ui/analyses/{analysis_id}/timeline?source=X",
        headers={"HX-Request": "true"},
    )
    assert htmx_filtered.status_code == 200
    assert (
        htmx_filtered.headers["HX-Push-Url"] == f"/ui/analyses/{analysis_id}?source=X&view=timeline"
    )
    empty_filters = functional_client.get(
        f"/ui/analyses/{analysis_id}?view=timeline&company=&source=&from_date=&to_date="
    )
    assert empty_filters.status_code == 200
    assert "Atualização de mercado" in empty_filters.text

    api_events = functional_client.get(f"/analyses/{analysis_id}/events?source=GNEWS")
    assert api_events.status_code == 200
    assert len(api_events.json()) == 2
    assert all(event["is_mock"] for event in api_events.json())
    analysis_detail = functional_client.get(f"/analyses/{analysis_id}").json()
    competitor_id = next(
        link["company"]["id"]
        for link in analysis_detail["companies"]
        if link["role"] == "COMPETITOR"
    )
    assert functional_client.get(f"/ui/analyses/{analysis_id}?view=companies").status_code == 200
    assert (
        "Beta Finance" in functional_client.get(f"/ui/analyses/{analysis_id}?view=companies").text
    )
    removed = functional_client.post(
        f"/ui/analyses/{analysis_id}/competitors/{competitor_id}/remove",
        follow_redirects=False,
    )
    assert removed.status_code == 303
    assert "Beta Finance" not in functional_client.get(f"/ui/analyses/{analysis_id}/setup").text


def test_wizard_requires_competitor_before_period_step(functional_client):
    state = {
        "name": "Setor de teste",
        "target_name": "Alfa",
        "target_website": "https://alfa.example",
        "target_search_term": "",
        "competitors": [],
        "period": "week",
        "from_date": "",
        "to_date": "",
    }
    response = functional_client.post(
        "/ui/analyses/new/step/3",
        data={"wizard_state": json.dumps(state), "intent": "next"},
    )
    assert "Adicione ao menos um concorrente" in response.text
    assert "Período inicial" not in response.text


def test_wizard_can_remove_competitor_without_losing_target(functional_client):
    state = {
        "name": "Setor de teste",
        "target_name": "Alfa",
        "target_website": "https://alfa.example",
        "target_search_term": "Alfa",
        "competitors": [{"name": "Beta", "website": "https://beta.example", "search_term": "Beta"}],
        "period": "week",
        "from_date": "",
        "to_date": "",
    }
    response = functional_client.post(
        "/ui/analyses/new/step/3",
        data={
            "wizard_state": json.dumps(state),
            "competitor_name_0": "Beta",
            "competitor_website_0": "https://beta.example",
            "competitor_search_0": "Beta",
            "intent": "remove_competitor",
            "remove_index": "0",
        },
        headers={"HX-Request": "true"},
    )
    updated = _wizard_state(response.text)
    assert updated["competitors"] == []
    assert updated["target_name"] == "Alfa"
    assert "Empresa principal / TARGET" not in response.text


def test_failed_initial_collection_keeps_new_analysis(functional_client, monkeypatch):
    from app.web import routes

    def fail_collection(*args, **kwargs):
        raise RuntimeError("provider failure")

    monkeypatch.setattr(routes, "collect_analysis", fail_collection)
    state = {
        "name": "Coleta indisponível",
        "target_name": "Alfa",
        "target_website": "https://alfa.example",
        "target_search_term": "",
        "competitors": [{"name": "Beta", "website": "https://beta.example", "search_term": ""}],
        "period": "week",
        "from_date": date.today().isoformat(),
        "to_date": date.today().isoformat(),
    }
    response = functional_client.post(
        "/ui/analyses", data={"wizard_state": json.dumps(state)}, follow_redirects=False
    )
    assert response.status_code == 303
    workspace = functional_client.get(response.headers["location"])
    assert "coleta inicial" in workspace.text
    assert "Coleta indisponível" in workspace.text
    assert len(functional_client.get("/analyses").json()) == 1


def test_api_can_create_analysis_without_competitors_then_add_one(functional_client):
    response = functional_client.post("/analyses", json=_analysis_payload())
    assert response.status_code == 201
    analysis = response.json()
    assert len(analysis["companies"]) == 1
    assert analysis["companies"][0]["role"] == "TARGET"
    target_id = analysis["companies"][0]["company"]["id"]
    assert analysis["companies"][0]["company"]["effective_search_term"] == "Alfa Bank"
    assert functional_client.get(f"/analyses/{analysis['id']}").status_code == 200
    assert len(functional_client.get("/analyses").json()) == 1

    added = functional_client.post(
        f"/analyses/{analysis['id']}/companies",
        json={"name": "Beta Finance", "website": "https://beta.example"},
    )
    assert added.status_code == 200
    assert {link["role"] for link in added.json()["companies"]} == {"TARGET", "COMPETITOR"}
    today = datetime.now(UTC).date()
    collection = functional_client.post(
        f"/analyses/{analysis['id']}/collect",
        json={
            "from_date": (today - timedelta(days=2)).isoformat(),
            "to_date": today.isoformat(),
        },
    )
    assert collection.status_code == 200
    assert collection.json()["status"] == "success"
    assert collection.json()["persisted"] == 4
    assert len(functional_client.get(f"/analyses/{analysis['id']}/events").json()) == 4
    edited = functional_client.put(
        f"/companies/{target_id}",
        json={
            "name": "Alfa Bank",
            "website": "https://alfa.example",
            "search_term": "Alfa",
            "market": "Fintech",
        },
    )
    assert edited.status_code == 200
    assert edited.json()["effective_search_term"] == "Alfa"
    removal = functional_client.delete(f"/analyses/{analysis['id']}/companies/{target_id}")
    assert removal.status_code == 409
    invalid_target_as_competitor = functional_client.post(
        f"/analyses/{analysis['id']}/companies",
        json={"name": "Alfa Bank", "website": "http://alfa.example"},
    )
    assert invalid_target_as_competitor.status_code == 422
    competitor_id = next(
        link["company"]["id"] for link in added.json()["companies"] if link["role"] == "COMPETITOR"
    )
    removed = functional_client.delete(f"/analyses/{analysis['id']}/companies/{competitor_id}")
    assert removed.status_code == 204


def test_site_comparison_reuses_same_company_across_analyses(functional_client):
    first = functional_client.post("/analyses", json=_analysis_payload("Primeira"))
    second = functional_client.post(
        "/analyses",
        json={"name": "Segunda", "target": {"name": "Alfa Bank", "website": "http://alfa.example"}},
    )
    assert first.status_code == second.status_code == 201
    first_company = first.json()["companies"][0]["company"]["id"]
    second_company = second.json()["companies"][0]["company"]["id"]
    assert first_company == second_company


def test_database_rejects_a_second_target_for_same_analysis(functional_client, functional_db):
    response = functional_client.post("/analyses", json=_analysis_payload())
    analysis_id = response.json()["id"]
    with functional_db() as session:
        other = Company(name="Outra empresa", website="https://outra.example")
        session.add(other)
        session.flush()
        session.add(
            AnalysisCompany(
                analysis_id=analysis_id,
                company_id=other.id,
                role=CompanyRole.TARGET,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_collection_attempts_all_providers_and_keeps_successful_results(functional_db):
    class BrokenNews:
        source = EventSource.GNEWS

        def fetch(self, company, start, end):
            raise RuntimeError("provider indisponível")

    with functional_db() as session:
        target = Company(name="Alfa", website="https://alfa.example")
        competitor = Company(name="Beta", website="https://beta.example")
        analysis = Analysis(name="Teste")
        analysis.companies.extend(
            [
                AnalysisCompany(company=target, role=CompanyRole.TARGET),
                AnalysisCompany(company=competitor, role=CompanyRole.COMPETITOR),
            ]
        )
        session.add(analysis)
        session.commit()
        result = collect_analysis(
            session,
            analysis.id,
            date.today() - timedelta(days=7),
            date.today(),
            providers=[BrokenNews(), MockXProvider()],
        )
        assert result.status == "partial"
        assert len(result.providers) == 4
        assert sum(outcome.status == "failure" for outcome in result.providers) == 2
        assert sum(outcome.status == "success" for outcome in result.providers) == 2
        assert result.persisted == 2
        assert session.scalar(select(func.count(Event.id))) == 2


def test_timeline_orders_by_published_then_collected_and_filters(functional_client, functional_db):
    analysis_response = functional_client.post("/analyses", json=_analysis_payload())
    assert analysis_response.status_code == 201
    analysis = analysis_response.json()
    company_id = analysis["companies"][0]["company"]["id"]
    published = datetime.now(UTC) - timedelta(days=1)
    with functional_db() as session:
        session.add_all(
            [
                Event(
                    company_id=company_id,
                    source=EventSource.X,
                    title="Mais recente na coleta",
                    url="https://example.test/1",
                    published_at=published,
                    collected_at=published + timedelta(hours=1),
                    is_mock=True,
                ),
                Event(
                    company_id=company_id,
                    source=EventSource.GNEWS,
                    title="Mais antiga na coleta",
                    url="https://example.test/2",
                    published_at=published,
                    collected_at=published,
                    is_mock=True,
                ),
            ]
        )
        session.commit()
    response = functional_client.get(f"/analyses/{analysis['id']}/events")
    assert response.status_code == 200
    assert [event["title"] for event in response.json()] == [
        "Mais recente na coleta",
        "Mais antiga na coleta",
    ]
    filtered = functional_client.get(f"/analyses/{analysis['id']}/events?source=GNEWS")
    assert len(filtered.json()) == 1
    from_date = published.date().isoformat()
    selected_period = functional_client.get(
        f"/analyses/{analysis['id']}/events",
        params={"company": company_id, "source": "X", "from": from_date, "to": from_date},
    )
    assert selected_period.status_code == 200
    assert len(selected_period.json()) == 1
    company_events = functional_client.get(f"/companies/{company_id}/events")
    assert company_events.status_code == 200
    assert len(company_events.json()) == 2
    outside = functional_client.get(f"/analyses/{analysis['id']}/events?company=9999")
    assert outside.status_code == 422


def test_collection_reports_total_failure(functional_client, functional_db):
    class BrokenNews:
        source = EventSource.GNEWS

        def fetch(self, company, start, end):
            raise RuntimeError("indisponível")

    class BrokenX:
        source = EventSource.X

        def fetch(self, company, start, end):
            raise RuntimeError("indisponível")

    response = functional_client.post("/analyses", json=_analysis_payload())
    analysis_id = response.json()["id"]
    with functional_db() as session:
        result = collect_analysis(
            session,
            analysis_id,
            date.today() - timedelta(days=7),
            date.today(),
            providers=[BrokenNews(), BrokenX()],
        )
    assert result.status == "failure"
    assert all(outcome.status == "failure" for outcome in result.providers)
