import json
import os
import re
from datetime import date
from html import unescape
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models import Analysis, AnalysisCompany, Company, Event, EventAnalysis

TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")


def _wizard_state(page_text):
    value = re.search(r'name="wizard_state" value="([^"]*)"', page_text).group(1)
    return json.loads(unescape(value))


def _wizard_step(client, step, state, **form):
    response = client.post(
        f"/ui/analyses/new/step/{step}",
        data={"wizard_state": json.dumps(state), "intent": "next", **form},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert 'role="alert"' not in response.text
    return _wizard_state(response.text)


@pytest.mark.skipif(not TEST_POSTGRES_URL, reason="Defina TEST_POSTGRES_URL para integração real")
def test_postgres_wizard_collection_timeline_and_event_analysis_flow():
    database_url = TEST_POSTGRES_URL
    assert database_url is not None
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    analysis_id: int | None = None
    company_ids: list[int] = []
    suffix = uuid4().hex
    try:
        # Settings sem .env: providers mockados de notícias, X e análise de evento.
        settings = Settings(_env_file=None, database_url=database_url)
        with TestClient(create_app(settings)) as client:
            assert client.get("/health/ready").status_code == 200

            state = _wizard_state(client.get("/ui/analyses/new").text)
            state = _wizard_step(client, 1, state, name=f"PostgreSQL integration {suffix}")
            state = _wizard_step(
                client,
                2,
                state,
                target_name=f"Empresa alvo {suffix}",
                target_website=f"https://target-{suffix}.example",
                target_search_term="",
            )
            added = client.post(
                "/ui/analyses/new/step/3",
                data={
                    "wizard_state": json.dumps(state),
                    "intent": "add_competitor",
                    "new_competitor_name": f"Concorrente {suffix}",
                    "new_competitor_website": f"https://competitor-{suffix}.example",
                    "new_competitor_search_term": "",
                },
                headers={"HX-Request": "true"},
            )
            state = _wizard_step(client, 3, _wizard_state(added.text))
            state = _wizard_step(client, 4, state, period="week")
            created = client.post(
                "/ui/analyses", data={"wizard_state": json.dumps(state)}, follow_redirects=False
            )
            assert created.status_code == 303
            location = created.headers["location"]
            analysis_id = int(re.search(r"/ui/analyses/(\d+)\?", location).group(1))
            assert "collection_status=success&persisted=4" in location

            detail = client.get(f"/analyses/{analysis_id}").json()
            company_ids = [link["company"]["id"] for link in detail["companies"]]
            assert sorted(link["role"] for link in detail["companies"]) == [
                "COMPETITOR",
                "TARGET",
            ]
            overview = client.get(location)
            assert overview.status_code == 200
            assert "Coleta inicial concluída" in overview.text
            assert "Demonstração · mock" in overview.text

            setup_added = client.post(
                f"/ui/analyses/{analysis_id}/competitors",
                data={
                    "name": f"Segundo concorrente {suffix}",
                    "website": f"https://second-{suffix}.example",
                },
                follow_redirects=False,
            )
            assert setup_added.status_code == 303
            company_ids = [
                link["company"]["id"]
                for link in client.get(f"/analyses/{analysis_id}").json()["companies"]
            ]
            assert len(company_ids) == 3

            today = date.today().isoformat()
            collected = client.post(
                f"/ui/analyses/{analysis_id}/collect",
                data={"period": "week"},
                headers={"HX-Request": "true"},
            )
            assert collected.status_code == 200
            assert "Coleta concluída" in collected.text
            # Os dois eventos já coletados de cada empresa inicial não são duplicados.
            assert "2 evento(s) novo(s) persistido(s) de 6 recebido(s)." in collected.text
            assert f"to_date={today}" in collected.headers["HX-Push-Url"]

            events = client.get(f"/analyses/{analysis_id}/events")
            assert events.status_code == 200
            assert len(events.json()) == 6
            assert all(item["is_mock"] for item in events.json())
            filtered = client.get(
                f"/ui/analyses/{analysis_id}/timeline?source=X", headers={"HX-Request": "true"}
            )
            assert filtered.status_code == 200
            assert filtered.text.count('id="event-title-') == 3
            assert "Publicação demonstrativa" in filtered.text
            assert "Atualização de mercado" not in filtered.text

            event_id = events.json()[0]["id"]
            analyzed = client.post(f"/events/{event_id}/analysis")
            assert analyzed.status_code == 200
            assert analyzed.json()["provider"] == "MOCK"
            fragment = client.post(
                f"/ui/events/{event_id}/analysis?force=true", headers={"HX-Request": "true"}
            )
            assert fragment.status_code == 200
            assert "Análise simulada" in fragment.text

            assert client.get("/static/js/htmx.min.js").status_code == 200
            assert client.get("/static/css/app.css").status_code == 200

        with factory() as session:
            stored = session.scalar(
                select(func.count(Event.id)).where(Event.company_id.in_(company_ids))
            )
            assert stored == 6
    finally:
        if company_ids:
            with factory.begin() as session:
                event_ids = select(Event.id).where(Event.company_id.in_(company_ids))
                session.execute(delete(EventAnalysis).where(EventAnalysis.event_id.in_(event_ids)))
                session.execute(delete(Event).where(Event.company_id.in_(company_ids)))
        if analysis_id is not None:
            with factory.begin() as session:
                session.execute(
                    delete(AnalysisCompany).where(AnalysisCompany.analysis_id == analysis_id)
                )
                session.execute(delete(Analysis).where(Analysis.id == analysis_id))
        if company_ids:
            with factory.begin() as session:
                session.execute(delete(Company).where(Company.id.in_(company_ids)))
        engine.dispose()
