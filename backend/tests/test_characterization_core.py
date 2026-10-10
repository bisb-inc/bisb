"""Caracterização do comportamento externo da camada de serviços.

Estes testes fixam o comportamento da Entrega 1 antes do refactoring: contrato de erros
(status HTTP e corpo) na REST API e na Web UI, semântica da coleta e identidade de empresas
por site. Eles devem passar sem alteração antes e depois das refatorações.
"""

import json
from datetime import UTC, date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Analysis, AnalysisCompany, Company, CompanyRole, Event, EventSource
from app.providers.base import NormalizedEvent
from app.services.collection import collect_analysis
from app.services.companies import normalize_website

TARGET = {"name": "Alfa Bank", "website": "https://alfa.example"}
COMPETITOR = {"name": "Beta Finance", "website": "https://beta.example"}
PROVIDER_ERROR = "Não foi possível consultar ou persistir os resultados desta fonte."


def _create_analysis(client, name="Análise", target=TARGET, competitors=(COMPETITOR,)):
    response = client.post(
        "/analyses", json={"name": name, "target": target, "competitors": list(competitors)}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _company_id(analysis, role):
    return next(link["company"]["id"] for link in analysis["companies"] if link["role"] == role)


def _assert_error(response, status_code, detail):
    assert response.status_code == status_code, response.text
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"detail": detail}


def _record(source=EventSource.GNEWS, url="https://news.example/1", published_at=None, **values):
    return NormalizedEvent(
        source=source,
        title=values.get("title", "Acontecimento"),
        description=values.get("description", "Descrição"),
        url=url,
        published_at=published_at or datetime(2026, 9, 1, 12, tzinfo=UTC),
        is_mock=values.get("is_mock", False),
    )


class StubProvider:
    """Provider configurável: registra chamadas e devolve registros por empresa."""

    def __init__(self, source, records=(), error=None, by_company=None):
        self.source = source
        self.records = list(records)
        self.error = error
        self.by_company = by_company or {}
        self.calls = []

    def fetch(self, company, start, end):
        self.calls.append((company.id, start, end))
        if self.error is not None:
            raise self.error
        return list(self.by_company.get(company.name, self.records))


def _seed_analysis(session, *names):
    analysis = Analysis(name="Coleta")
    for index, name in enumerate(names):
        analysis.companies.append(
            AnalysisCompany(
                company=Company(name=name, website=f"https://{name.lower()}.example"),
                role=CompanyRole.TARGET if index == 0 else CompanyRole.COMPETITOR,
            )
        )
    session.add(analysis)
    session.commit()
    return analysis


# Contrato de erros: REST API


@pytest.mark.parametrize(
    ("method", "url", "body", "detail"),
    [
        ("GET", "/analyses/9999", None, "Análise não encontrada"),
        ("POST", "/analyses/9999/companies", COMPETITOR, "Análise não encontrada"),
        ("DELETE", "/analyses/9999/companies/1", None, "Análise não encontrada"),
        (
            "POST",
            "/analyses/9999/collect",
            {"from_date": "2026-09-01", "to_date": "2026-09-02"},
            "Análise não encontrada",
        ),
        ("GET", "/analyses/9999/events", None, "Análise não encontrada"),
        ("PUT", "/companies/9999", COMPETITOR, "Empresa não encontrada"),
        ("GET", "/companies/9999/events", None, "Empresa não encontrada"),
        ("POST", "/events/9999/analysis", None, "Evento não encontrado"),
    ],
)
def test_rest_not_found_errors_keep_status_and_detail(functional_client, method, url, body, detail):
    response = functional_client.request(method, url, json=body)
    _assert_error(response, 404, detail)


def test_rest_business_rule_errors_keep_status_and_detail(functional_client):
    analysis = _create_analysis(functional_client)
    analysis_id = analysis["id"]
    target_id = _company_id(analysis, "TARGET")
    competitor_id = _company_id(analysis, "COMPETITOR")

    same_company_as_competitor = functional_client.post(
        "/analyses",
        json={
            "name": "Conflito",
            "target": TARGET,
            "competitors": [{"name": "Alfa Bank", "website": "http://www.alfa.example/"}],
        },
    )
    _assert_error(same_company_as_competitor, 422, "TARGET não pode também ser concorrente.")
    site_with_other_name = functional_client.post(
        "/analyses",
        json={"name": "Conflito", "target": {"name": "Outra", "website": "alfa.example"}},
    )
    _assert_error(
        site_with_other_name,
        409,
        "O site já está associado a outra empresa; revise o nome antes de mesclar.",
    )
    assert len(functional_client.get("/analyses").json()) == 1

    _assert_error(
        functional_client.post(f"/analyses/{analysis_id}/companies", json=TARGET),
        422,
        "A empresa-alvo não pode ser concorrente.",
    )
    _assert_error(
        functional_client.delete(f"/analyses/{analysis_id}/companies/{target_id}"),
        409,
        "A empresa TARGET não pode ser removida.",
    )
    _assert_error(
        functional_client.delete(f"/analyses/{analysis_id}/companies/9999"),
        404,
        "Empresa não vinculada a esta análise",
    )
    _assert_error(
        functional_client.put(
            f"/companies/{competitor_id}",
            json={"name": "Beta Finance", "website": "www.alfa.example/"},
        ),
        409,
        "O site já identifica outra empresa.",
    )
    _assert_error(
        functional_client.get(f"/analyses/{analysis_id}/events?company=9999"),
        422,
        "A empresa não pertence a esta análise",
    )
    _assert_error(
        functional_client.get(f"/analyses/{analysis_id}/events?from=2026-09-10&to=2026-09-01"),
        422,
        "A data inicial deve ser anterior ou igual à data final",
    )
    invalid_range = functional_client.post(
        f"/analyses/{analysis_id}/collect",
        json={"from_date": "2026-09-10", "to_date": "2026-09-01"},
    )
    assert invalid_range.status_code == 422


def test_rest_competitor_addition_is_idempotent_and_own_site_can_be_kept(functional_client):
    analysis = _create_analysis(functional_client)
    target_id = _company_id(analysis, "TARGET")

    repeated = functional_client.post(
        f"/analyses/{analysis['id']}/companies",
        json={"name": "beta  finance", "website": "http://www.beta.example/"},
    )
    assert repeated.status_code == 200
    assert len(repeated.json()["companies"]) == 2

    kept = functional_client.put(
        f"/companies/{target_id}", json={"name": "Alfa Bank", "website": "http://alfa.example/"}
    )
    assert kept.status_code == 200
    assert kept.json()["website"] == "http://alfa.example/"


def test_rest_event_analysis_concurrent_save_conflict_is_409(
    functional_client, functional_db, monkeypatch
):
    analysis = _create_analysis(functional_client)
    with functional_db() as session:
        event = Event(
            company_id=_company_id(analysis, "TARGET"),
            source=EventSource.GNEWS,
            title="Alfa lança produto",
            url="https://news.example/conflict",
            published_at=datetime.now(UTC),
        )
        session.add(event)
        session.commit()
        event_id = event.id
    assert functional_client.post(f"/events/{event_id}/analysis").status_code == 200

    original_commit = Session.commit

    def conflicting_commit(self):
        monkeypatch.setattr(Session, "commit", original_commit)
        raise IntegrityError("INSERT INTO event_analyses", {}, Exception("concurrent"))

    monkeypatch.setattr(Session, "commit", conflicting_commit)
    response = functional_client.post(f"/events/{event_id}/analysis?force=true")
    _assert_error(response, 409, "Não foi possível salvar a análise concorrente")


# Contrato de erros: Web UI (erros de serviço chegam como JSON com o mesmo status)


def test_web_routes_expose_service_errors_with_same_status_and_detail(functional_client):
    analysis = _create_analysis(functional_client)
    analysis_id = analysis["id"]
    target_id = _company_id(analysis, "TARGET")
    competitor_id = _company_id(analysis, "COMPETITOR")

    _assert_error(functional_client.get("/ui/analyses/9999"), 404, "Análise não encontrada")
    _assert_error(functional_client.get("/ui/analyses/9999/setup"), 404, "Análise não encontrada")
    _assert_error(
        functional_client.post(f"/ui/analyses/{analysis_id}/setup", data={"name": "   "}),
        422,
        "O nome da análise é obrigatório",
    )
    _assert_error(
        functional_client.post(f"/ui/analyses/{analysis_id}/competitors", data=TARGET),
        422,
        "A empresa-alvo não pode ser concorrente.",
    )
    _assert_error(
        functional_client.post(f"/ui/analyses/{analysis_id}/competitors/{target_id}/remove"),
        409,
        "A empresa TARGET não pode ser removida.",
    )
    _assert_error(
        functional_client.post(
            f"/ui/companies/{competitor_id}",
            data={"analysis_id": analysis_id, "name": "Beta Finance", "website": "alfa.example"},
        ),
        409,
        "O site já identifica outra empresa.",
    )
    _assert_error(
        functional_client.post(
            f"/ui/companies/{competitor_id}",
            data={"analysis_id": 9999, "name": "Beta Finance", "website": "beta.example"},
        ),
        404,
        "Análise não encontrada",
    )
    _assert_error(
        functional_client.post("/ui/analyses/9999/collect", data={"period": "week"}),
        404,
        "Análise não encontrada",
    )
    _assert_error(
        functional_client.get(f"/ui/analyses/{analysis_id}/timeline?company=9999"),
        422,
        "A empresa não pertence a esta análise",
    )
    _assert_error(functional_client.post("/ui/events/9999/analysis"), 404, "Evento não encontrado")


def _wizard_state(**overrides):
    today = date.today().isoformat()
    state = {
        "name": "Wizard",
        "target_name": "Alfa Bank",
        "target_website": "https://alfa.example",
        "target_search_term": "",
        "competitors": [{"name": "Beta Finance", "website": "https://beta.example"}],
        "period": "custom",
        "from_date": today,
        "to_date": today,
    }
    state.update(overrides)
    return {"wizard_state": json.dumps(state)}


def test_wizard_confirmation_renders_service_conflict_on_review_step(functional_client):
    _create_analysis(functional_client, competitors=())

    response = functional_client.post(
        "/ui/analyses",
        data=_wizard_state(target_name="Outro nome", target_website="alfa.example"),
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "Revise sua análise" in response.text
    assert "O site já está associado a outra empresa; revise o nome antes de mesclar." in (
        response.text
    )
    assert len(functional_client.get("/analyses").json()) == 1


def test_wizard_site_rule_differs_from_service_identity_rule(functional_client):
    """O wizard compara sites só por barra final e caixa; o serviço normaliza o site.

    Um concorrente com o mesmo site do TARGET escrito sem protocolo passa pela etapa 3
    e é rejeitado pelo serviço na confirmação, sem criar a análise.
    """
    competitor = {"name": "Alfa Bank", "website": "alfa.example"}
    step = functional_client.post(
        "/ui/analyses/new/step/3",
        data={**_wizard_state(competitors=[competitor]), "intent": "next"},
    )
    assert "Defina o período inicial" in step.text

    response = functional_client.post(
        "/ui/analyses", data=_wizard_state(competitors=[competitor]), follow_redirects=False
    )
    assert response.status_code == 200
    assert "TARGET não pode também ser concorrente." in response.text
    assert functional_client.get("/analyses").json() == []


# Semântica da coleta


def test_collection_visits_companies_then_providers_with_utc_end_exclusive_range(functional_db):
    news = StubProvider(EventSource.GNEWS)
    x = StubProvider(EventSource.X)
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa", "Beta")
        company_ids = [link.company_id for link in analysis.companies]
        result = collect_analysis(
            session, analysis.id, date(2026, 9, 1), date(2026, 9, 3), providers=[news, x]
        )

    start = datetime(2026, 9, 1, tzinfo=UTC)
    end = datetime(2026, 9, 4, tzinfo=UTC)
    assert news.calls == [(company_id, start, end) for company_id in company_ids]
    assert x.calls == news.calls
    assert [(outcome.company_id, outcome.source) for outcome in result.providers] == [
        (company_ids[0], EventSource.GNEWS),
        (company_ids[0], EventSource.X),
        (company_ids[1], EventSource.GNEWS),
        (company_ids[1], EventSource.X),
    ]
    assert result.status == "success"
    assert (result.fetched, result.persisted) == (0, 0)


def test_collection_rejects_wrong_source_or_naive_dates_for_the_whole_pair(functional_db):
    wrong_source = StubProvider(
        EventSource.GNEWS,
        records=[_record(url="https://news.example/ok"), _record(source=EventSource.X)],
    )
    naive_date = StubProvider(
        EventSource.X,
        records=[_record(source=EventSource.X, published_at=datetime(2026, 9, 1, 12))],
    )
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa")
        result = collect_analysis(
            session,
            analysis.id,
            date(2026, 9, 1),
            date(2026, 9, 2),
            providers=[wrong_source, naive_date],
        )
        stored = session.scalar(select(func.count(Event.id)))

    assert result.status == "failure"
    assert [(item.status, item.fetched, item.persisted) for item in result.providers] == [
        ("failure", 2, 0),
        ("failure", 1, 0),
    ]
    assert all(item.error == PROVIDER_ERROR for item in result.providers)
    assert (result.fetched, result.persisted) == (3, 0)
    assert stored == 0


def test_collection_failure_rolls_back_only_the_failed_company_provider_pair(functional_db):
    news = StubProvider(
        EventSource.GNEWS,
        by_company={
            "Alfa": [_record(url="https://news.example/alfa")],
            "Beta": [
                _record(url="https://news.example/beta"),
                _record(url="https://news.example/beta-naive", published_at=datetime(2026, 9, 1)),
            ],
        },
    )
    x = StubProvider(
        EventSource.X, records=[_record(source=EventSource.X, url="https://x.example")]
    )
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa", "Beta")
        result = collect_analysis(
            session, analysis.id, date(2026, 9, 1), date(2026, 9, 2), providers=[news, x]
        )
        stored = sorted(
            (event.company.name, event.source.value, event.url)
            for event in session.scalars(select(Event))
        )

    assert result.status == "partial"
    assert [(item.status, item.fetched, item.persisted) for item in result.providers] == [
        ("success", 1, 1),
        ("success", 1, 1),
        ("failure", 2, 0),
        ("success", 1, 1),
    ]
    assert [item.error for item in result.providers] == [None, None, PROVIDER_ERROR, None]
    assert (result.fetched, result.persisted) == (5, 3)
    assert stored == [
        ("Alfa", "GNEWS", "https://news.example/alfa"),
        ("Alfa", "X", "https://x.example"),
        ("Beta", "X", "https://x.example"),
    ]


def test_collection_deduplicates_within_a_batch_and_across_collections(functional_db):
    duplicated = StubProvider(
        EventSource.GNEWS, records=[_record(url="https://news.example/same")] * 2
    )
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa")
        first = collect_analysis(
            session, analysis.id, date(2026, 9, 1), date(2026, 9, 2), providers=[duplicated]
        )
        second = collect_analysis(
            session, analysis.id, date(2026, 9, 1), date(2026, 9, 2), providers=[duplicated]
        )
        stored = session.scalar(select(func.count(Event.id)))

    assert (first.status, first.fetched, first.persisted) == ("success", 2, 1)
    assert (second.status, second.fetched, second.persisted) == ("success", 2, 0)
    assert stored == 1


def test_collection_persists_normalized_fields_in_utc(functional_db):
    local_time = datetime(2026, 9, 1, 9, 30, tzinfo=timezone(timedelta(hours=-3)))
    provider = StubProvider(
        EventSource.X,
        records=[
            _record(
                source=EventSource.X,
                url="https://x.example/post",
                published_at=local_time,
                title="Post",
                description=None,
                is_mock=True,
            )
        ],
    )
    before = datetime.now(UTC)
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa")
        collect_analysis(
            session, analysis.id, date(2026, 9, 1), date(2026, 9, 1), providers=[provider]
        )
        event = session.scalars(select(Event)).one()

    assert event.published_at == datetime(2026, 9, 1, 12, 30, tzinfo=UTC)
    assert event.published_at.utcoffset() == timedelta(0)
    assert before <= event.collected_at <= datetime.now(UTC)
    assert (event.title, event.description, event.url, event.is_mock) == (
        "Post",
        None,
        "https://x.example/post",
        True,
    )


def test_collection_without_companies_or_outcomes_is_failure(functional_db):
    with functional_db() as session:
        analysis = Analysis(name="Sem empresas")
        session.add(analysis)
        session.commit()
        result = collect_analysis(session, analysis.id, date(2026, 9, 1), date(2026, 9, 1))

    assert result.model_dump() == {
        "status": "failure",
        "providers": [],
        "fetched": 0,
        "persisted": 0,
    }


def test_collection_defaults_to_mock_news_and_x_providers(functional_db):
    today = date.today()
    with functional_db() as session:
        analysis = _seed_analysis(session, "Alfa")
        result = collect_analysis(session, analysis.id, today, today)
        sources = {(event.source, event.is_mock) for event in session.scalars(select(Event))}

    assert result.status == "success"
    assert [item.source for item in result.providers] == [EventSource.GNEWS, EventSource.X]
    assert sources == {(EventSource.GNEWS, True), (EventSource.X, True)}


def test_rest_collection_contract_reports_each_pair(functional_client):
    analysis = _create_analysis(functional_client)
    functional_client.app.state.source_providers = [
        StubProvider(EventSource.GNEWS, error=RuntimeError("segredo-do-provider")),
        StubProvider(EventSource.X, records=[_record(source=EventSource.X)]),
    ]

    response = functional_client.post(
        f"/analyses/{analysis['id']}/collect",
        json={"from_date": "2026-09-01", "to_date": "2026-09-02"},
    )

    assert response.status_code == 200
    target_id = _company_id(analysis, "TARGET")
    competitor_id = _company_id(analysis, "COMPETITOR")
    assert response.json() == {
        "status": "partial",
        "providers": [
            {
                "source": "GNEWS",
                "company_id": target_id,
                "status": "failure",
                "fetched": 0,
                "persisted": 0,
                "error": PROVIDER_ERROR,
            },
            {
                "source": "X",
                "company_id": target_id,
                "status": "success",
                "fetched": 1,
                "persisted": 1,
                "error": None,
            },
            {
                "source": "GNEWS",
                "company_id": competitor_id,
                "status": "failure",
                "fetched": 0,
                "persisted": 0,
                "error": PROVIDER_ERROR,
            },
            {
                "source": "X",
                "company_id": competitor_id,
                "status": "success",
                "fetched": 1,
                "persisted": 1,
                "error": None,
            },
        ],
        "fetched": 2,
        "persisted": 2,
    }
    assert "segredo-do-provider" not in response.text


# Identidade de empresas por site


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://www.Alfa.example/", "alfa.example"),
        ("http://alfa.example", "alfa.example"),
        ("ALFA.example", "alfa.example"),
        ("https://WWW.alfa.example", "alfa.example"),
        ("www.alfa.example/produtos/", "alfa.example/produtos"),
        ("https://alfa.example/Path?x=1#top", "alfa.example/Path?x=1#top"),
        ("https://alfa.example:8443/", "alfa.example:8443"),
        ("  alfa.example  ", "alfa.example"),
        ("   ", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_website_ignores_only_trivial_differences(value, expected):
    assert normalize_website(value) == expected


def test_company_identity_reuses_site_variants_with_equivalent_names(functional_client):
    first = _create_analysis(functional_client, name="Primeira", competitors=())
    second = _create_analysis(
        functional_client,
        name="Segunda",
        target={"name": "  alfa   BANK ", "website": "WWW.ALFA.EXAMPLE/"},
        competitors=(),
    )

    assert _company_id(first, "TARGET") == _company_id(second, "TARGET")
    assert second["companies"][0]["company"]["name"] == "Alfa Bank"
