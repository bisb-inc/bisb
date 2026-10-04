from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.models import (
    Analysis,
    AnalysisCompany,
    AnalysisEngine,
    Company,
    CompanyRole,
    CompetitiveImpact,
    Event,
    EventAnalysis,
    EventAnalysisCategory,
    EventSentiment,
    EventSource,
)
from app.providers.analysis import (
    AnalysisProviderError,
    EventAnalysisContent,
    GeminiAnalysisProvider,
    MockAnalysisProvider,
    configured_analysis_provider,
)
from app.services.event_analysis import analyze_event


def _add_event(functional_db):
    with functional_db() as session:
        company = Company(name="Alfa", website="https://alfa.example")
        session.add(company)
        session.flush()
        event = Event(
            company_id=company.id,
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


def test_analysis_schema_enforces_vocabulary_and_score():
    valid = EventAnalysisContent(
        summary="Resumo curto",
        category=EventAnalysisCategory.PRODUCT,
        competitive_impact=CompetitiveImpact.HIGH,
        sentiment=EventSentiment.POSITIVE,
        relevance_score=100,
        justification="Lançamento relevante.",
    )
    assert valid.relevance_score == 100
    with pytest.raises(ValidationError):
        EventAnalysisContent(
            summary="Resumo",
            category="UNKNOWN",
            competitive_impact="HIGH",
            sentiment="NEUTRAL",
            relevance_score=101,
            justification="Motivo",
        )


def test_database_rejects_relevance_score_outside_range(functional_db):
    event_id = _add_event(functional_db)
    with functional_db() as session, pytest.raises(IntegrityError):
        session.add(
            EventAnalysis(
                event_id=event_id,
                summary="Resumo",
                category=EventAnalysisCategory.OTHER,
                competitive_impact=CompetitiveImpact.LOW,
                sentiment=EventSentiment.NEUTRAL,
                relevance_score=101,
                justification="Justificativa",
                provider=AnalysisEngine.MOCK,
                model="mock-v1",
                is_mock=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.commit()


def test_provider_selection_is_explicit_and_mock_is_deterministic():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
        analysis_provider="mock",
    )
    provider = configured_analysis_provider(settings)
    assert isinstance(provider, MockAnalysisProvider)
    event = Event(title="Notícia", source=EventSource.X)
    event.company = Company(name="Beta")
    assert provider.analyze(event) == provider.analyze(event)
    assert provider.provider is AnalysisEngine.MOCK
    settings.analysis_provider = "gemini"
    assert isinstance(configured_analysis_provider(settings), GeminiAnalysisProvider)


def test_gemini_missing_key_raises_controlled_error():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
        analysis_provider="gemini",
    )
    event = Event(title="Notícia", source=EventSource.GNEWS)
    event.company = Company(name="Alfa")
    with pytest.raises(AnalysisProviderError, match="GEMINI_API_KEY"):
        GeminiAnalysisProvider(settings).analyze(event)


def test_gemini_uses_structured_schema_with_mock_client():
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
        analysis_provider="gemini",
        gemini_api_key="unit-test-secret",
    )
    expected = EventAnalysisContent(
        summary="Lançou um produto.",
        category=EventAnalysisCategory.PRODUCT,
        competitive_impact=CompetitiveImpact.MEDIUM,
        sentiment=EventSentiment.POSITIVE,
        relevance_score=75,
        justification="A notícia relata lançamento de produto.",
    )

    class Models:
        call = None

        def generate_content(self, **kwargs):
            self.call = kwargs
            return type("Response", (), {"parsed": expected})()

    models = Models()
    client = type("Client", (), {"models": models})()
    event = Event(title="Lançamento", source=EventSource.GNEWS)
    event.company = Company(name="Alfa")
    result = GeminiAnalysisProvider(settings, client=client).analyze(event)
    assert result == expected
    assert models.call["model"] == "gemini-3.8-flash"
    assert models.call["config"].response_mime_type == "application/json"
    assert "Alfa" in models.call["contents"]
    assert "unit-test-secret" not in models.call["contents"]


def test_mock_analysis_is_separate_and_existing_result_skips_provider(functional_db):
    event_id = _add_event(functional_db)
    provider = MockAnalysisProvider()
    with functional_db() as session:
        first = analyze_event(session, event_id, provider)
        event = session.get(Event, event_id)
        assert event is not None
        assert event.title == "Alfa lança novo produto"
        assert first.is_mock is True
        assert first.provider is AnalysisEngine.MOCK
        assert first.category is EventAnalysisCategory.OTHER
        assert session.scalar(select(EventAnalysis).where(EventAnalysis.event_id == event_id))

    class MustNotRun:
        provider = AnalysisEngine.GEMINI
        model = "unused"

        def analyze(self, event):
            raise AssertionError("existing analysis should be reused")

    with functional_db() as session:
        existing = analyze_event(session, event_id, MustNotRun())
        assert existing.event_id == event_id


def test_rest_reanalysis_requires_explicit_force(functional_client, functional_db):
    event_id = _add_event(functional_db)

    class CountingProvider:
        provider = AnalysisEngine.MOCK
        model = "mock-counting"
        calls = 0

        def analyze(self, event):
            self.calls += 1
            return MockAnalysisProvider().analyze(event)

    provider = CountingProvider()
    functional_client.app.state.analysis_provider = provider
    assert functional_client.post(f"/events/{event_id}/analysis").status_code == 200
    assert functional_client.post(f"/events/{event_id}/analysis").status_code == 200
    assert provider.calls == 1
    forced = functional_client.post(f"/events/{event_id}/analysis?force=true")
    assert forced.status_code == 200
    assert provider.calls == 2


def test_reanalysis_failure_preserves_previous_result_and_event(functional_db):
    event_id = _add_event(functional_db)
    with functional_db() as session:
        previous = analyze_event(session, event_id, MockAnalysisProvider())
        previous_summary = previous.summary

    class FailedProvider:
        provider = AnalysisEngine.GEMINI
        model = "gemini-test"

        def analyze(self, event):
            raise AnalysisProviderError("controlled failure")

    with functional_db() as session, pytest.raises(AnalysisProviderError):
        analyze_event(session, event_id, FailedProvider(), force=True)

    with functional_db() as session:
        saved = session.get(EventAnalysis, event_id)
        event = session.get(Event, event_id)
        assert saved is not None and saved.summary == previous_summary
        assert event is not None and event.title == "Alfa lança novo produto"


def test_rest_analysis_api_get_post_and_missing_event(functional_client, functional_db):
    event_id = _add_event(functional_db)
    response = functional_client.post(f"/events/{event_id}/analysis")
    assert response.status_code == 200
    assert response.json()["provider"] == "MOCK"
    assert response.json()["is_mock"] is True
    assert response.json()["relevance_score"] == 50
    assert "GEMINI_API_KEY" not in response.text
    assert functional_client.get(f"/events/{event_id}/analysis").json() == response.json()
    assert functional_client.post("/events/9999/analysis").status_code == 404
    assert functional_client.get("/events/9999/analysis").status_code == 404


def test_gemini_missing_key_is_503(functional_db, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
    from app.db.session import get_session
    from app.main import create_app

    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
        analysis_provider="gemini",
        gemini_api_key=None,
    )
    app = create_app(settings)

    def override_session():
        with functional_db() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    from fastapi.testclient import TestClient

    event_id = _add_event(functional_db)
    with TestClient(app) as test_client:
        response = test_client.post(f"/events/{event_id}/analysis")
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.text
    assert "test" not in response.text


def test_gemini_provider_error_does_not_expose_key(functional_client, functional_db, caplog):
    event_id = _add_event(functional_db)
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://test:test@localhost/test",
        analysis_provider="gemini",
        gemini_api_key="unit-test-secret",
    )

    class FailingModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("unit-test-secret")

    client = type("Client", (), {"models": FailingModels()})()
    functional_client.app.state.analysis_provider = GeminiAnalysisProvider(settings, client=client)
    response = functional_client.post(f"/events/{event_id}/analysis")
    assert response.status_code == 502
    assert "unit-test-secret" not in response.text
    assert "unit-test-secret" not in caplog.text


def test_htmx_analysis_renders_mock_and_reanalysis_action(functional_client, functional_db):
    event_id = _add_event(functional_db)
    response = functional_client.post(
        f"/ui/events/{event_id}/analysis", headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "Análise simulada" in response.text
    assert "Reanalisar" in response.text
    assert "50/100" in response.text


def test_existing_analysis_is_rendered_in_timeline_without_provider_call(
    functional_client, functional_db
):
    with functional_db() as session:
        company = Company(name="Alfa", website="https://alfa.example")
        analysis = Analysis(name="Teste IA")
        session.add_all([company, analysis])
        session.flush()
        session.add(
            AnalysisCompany(analysis_id=analysis.id, company_id=company.id, role=CompanyRole.TARGET)
        )
        event = Event(
            company_id=company.id,
            source=EventSource.GNEWS,
            title="Notícia avaliada",
            description="Descrição",
            url="https://news.example/evaluated",
            is_mock=False,
            published_at=datetime.now(UTC),
            collected_at=datetime.now(UTC),
        )
        session.add(event)
        session.commit()
        analysis_id, event_id = analysis.id, event.id

    class CountingProvider:
        provider = AnalysisEngine.MOCK
        model = "mock-counting"
        calls = 0

        def analyze(self, event):
            self.calls += 1
            return MockAnalysisProvider().analyze(event)

    provider = CountingProvider()
    functional_client.app.state.analysis_provider = provider
    assert functional_client.post(f"/events/{event_id}/analysis").status_code == 200
    page = functional_client.get(f"/ui/analyses/{analysis_id}")
    assert page.status_code == 200
    assert "Análise simulada" in page.text
    assert "Acontecimento demonstrativo" in page.text
    assert provider.calls == 1
