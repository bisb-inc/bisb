import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.models import Analysis, AnalysisCompany, Company, Event

TEST_POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")


@pytest.mark.skipif(not TEST_POSTGRES_URL, reason="Defina TEST_POSTGRES_URL para integração real")
def test_postgres_migration_persistence_and_web_flow():
    database_url = TEST_POSTGRES_URL
    assert database_url is not None
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    analysis_id: int | None = None
    company_ids: list[int] = []
    try:
        settings = Settings(_env_file=None, database_url=database_url)
        with TestClient(create_app(settings)) as client:
            assert client.get("/health/ready").status_code == 200
            created = client.post(
                "/ui/analyses",
                data={
                    "name": f"PostgreSQL integration {uuid4()}",
                    "target_name": f"Empresa alvo {uuid4()}",
                    "target_website": f"https://target-{uuid4()}.example",
                },
                follow_redirects=False,
            )
            assert created.status_code == 303
            analysis_id = int(created.headers["location"].rsplit("/", 1)[1])
            page = client.get(f"/ui/analyses/{analysis_id}")
            assert page.status_code == 200
            assert "Monitoramento" in page.text
            company_ids = [
                link["company"]["id"]
                for link in client.get(f"/analyses/{analysis_id}").json()["companies"]
            ]
            added = client.post(
                f"/ui/analyses/{analysis_id}/competitors",
                data={
                    "name": f"Concorrente {uuid4()}",
                    "website": f"https://competitor-{uuid4()}.example",
                },
                headers={"HX-Request": "true"},
            )
            assert added.status_code == 200
            assert "Concorrente" in added.text
            company_ids = [
                link["company"]["id"]
                for link in client.get(f"/analyses/{analysis_id}").json()["companies"]
            ]
            end = datetime.now(UTC).date()
            collected = client.post(
                f"/ui/analyses/{analysis_id}/collect",
                data={
                    "from_date": (end - timedelta(days=2)).isoformat(),
                    "to_date": end.isoformat(),
                },
                headers={"HX-Request": "true"},
            )
            assert collected.status_code == 200
            assert "Coleta concluída" in collected.text
            assert "Demonstração · mock" in collected.text
            timeline = client.get(f"/analyses/{analysis_id}/events")
            assert timeline.status_code == 200
            assert len(timeline.json()) == 4
            assert all(item["is_mock"] for item in timeline.json())
            assert client.get("/static/js/htmx.min.js").status_code == 200
            assert client.get("/static/css/app.css").status_code == 200
    finally:
        if analysis_id is not None:
            with factory.begin() as session:
                session.execute(delete(Event).where(Event.company_id.in_(company_ids)))
                session.execute(
                    delete(AnalysisCompany).where(AnalysisCompany.analysis_id == analysis_id)
                )
                session.execute(delete(Analysis).where(Analysis.id == analysis_id))
                if company_ids:
                    session.execute(delete(Company).where(Company.id.in_(company_ids)))
        engine.dispose()
