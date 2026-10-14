"""Caracterização do comportamento externo da Web UI.

Estes testes fixam URLs, redirecionamentos, cabeçalhos HTMX, fragmentos e mensagens do
wizard e do workspace da Entrega 1. Eles exercitam a aplicação somente por HTTP para que
continuem válidos quando a organização interna da camada Web mudar.
"""

import json
import re
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from html import unescape

import pytest

from app.models import Company, Event, EventSource
from app.providers.analysis import AnalysisConfigurationError, AnalysisProviderError
from app.providers.mock import MockXProvider

TARGET = {"name": "Alfa Bank", "website": "https://alfa.example"}
COMPETITOR = {"name": "Beta Finance", "website": "https://beta.example"}

WEB_ROUTES = {
    ("/", "GET"),
    ("/login", "GET"),
    ("/ui/analyses", "GET"),
    ("/ui/analyses", "POST"),
    ("/ui/analyses/new", "GET"),
    ("/ui/analyses/new/step/{step}", "POST"),
    ("/ui/analyses/{analysis_id}", "GET"),
    ("/ui/analyses/{analysis_id}/setup", "GET"),
    ("/ui/analyses/{analysis_id}/setup", "POST"),
    ("/ui/analyses/{analysis_id}/competitors", "POST"),
    ("/ui/analyses/{analysis_id}/competitors/{company_id}/remove", "POST"),
    ("/ui/companies/{company_id}", "POST"),
    ("/ui/companies/{company_id}", "PUT"),
    ("/ui/analyses/{analysis_id}/timeline", "GET"),
    ("/ui/analyses/{analysis_id}/collect", "POST"),
    ("/ui/events/{event_id}/analysis", "POST"),
}
REST_ROUTES = {
    ("/health", "GET"),
    ("/health/ready", "GET"),
    ("/analyses", "POST"),
    ("/analyses", "GET"),
    ("/analyses/{analysis_id}", "GET"),
    ("/analyses/{analysis_id}/companies", "POST"),
    ("/analyses/{analysis_id}/companies/{company_id}", "DELETE"),
    ("/companies/{company_id}", "PUT"),
    ("/analyses/{analysis_id}/collect", "POST"),
    ("/analyses/{analysis_id}/events", "GET"),
    ("/companies/{company_id}/events", "GET"),
    ("/events/{event_id}/analysis", "POST"),
    ("/events/{event_id}/analysis", "GET"),
}


def _state_from(page_text):
    value = re.search(r'name="wizard_state" value="([^"]*)"', page_text).group(1)
    return json.loads(unescape(value))


def _state(**overrides):
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
    return state


def _post_step(client, step, state, htmx=False, **form):
    headers = {"HX-Request": "true"} if htmx else {}
    return client.post(
        f"/ui/analyses/new/step/{step}",
        data={"wizard_state": json.dumps(state), **form},
        headers=headers,
    )


def _title(page_text):
    return re.search(r"<title>(.*?)</title>", page_text, re.S).group(1).strip()


def _create_analysis(client):
    response = client.post(
        "/analyses", json={"name": "Workspace", "target": TARGET, "competitors": [COMPETITOR]}
    )
    assert response.status_code == 201
    analysis = response.json()
    ids = {link["role"]: link["company"]["id"] for link in analysis["companies"]}
    return analysis["id"], ids["TARGET"], ids["COMPETITOR"]


def _months_before(value, months):
    year, month = value.year, value.month - months
    while month < 1:
        year, month = year - 1, month + 12
    return date(year, month, min(value.day, monthrange(year, month)[1]))


class BrokenNews:
    source = EventSource.GNEWS

    def fetch(self, company, start, end):
        raise RuntimeError("indisponível")


def test_rest_contract_inventory_is_preserved(functional_client):
    paths = functional_client.get("/openapi.json").json()["paths"]
    published = {(path, method.upper()) for path, item in paths.items() for method in item}
    assert published == REST_ROUTES


@pytest.mark.parametrize(("path", "method"), sorted(WEB_ROUTES))
def test_web_url_is_still_served(functional_client, path, method):
    url = path.format(analysis_id=9999, company_id=9999, event_id=9999, step=1)
    response = functional_client.request(method, url, follow_redirects=False)
    assert response.status_code != 405
    if response.status_code == 404:
        assert response.json() != {"detail": "Not Found"}
    assert path not in functional_client.get("/openapi.json").json()["paths"]


def test_root_redirects_to_analyses_list(functional_client):
    response = functional_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/ui/analyses"


def test_wizard_entry_starts_at_week_preset_and_clamps_step(functional_client):
    first = functional_client.get("/ui/analyses/new")
    state = _state_from(first.text)
    today = date.today()
    assert state == {
        "name": "",
        "target_name": "",
        "target_website": "",
        "target_search_term": "",
        "competitors": [],
        "period": "week",
        "from_date": (today - timedelta(days=6)).isoformat(),
        "to_date": today.isoformat(),
    }
    assert "Dê um nome à análise" in first.text
    assert "<html" in first.text
    assert "Dê um nome à análise" in functional_client.get("/ui/analyses/new?step=0").text
    assert "Etapa 5 de 5" in functional_client.get("/ui/analyses/new?step=9").text


@pytest.mark.parametrize("step", [0, 6])
def test_wizard_step_outside_range_is_404(functional_client, step):
    response = _post_step(functional_client, step, _state())
    assert response.status_code == 404
    assert response.json() == {"detail": "Etapa não encontrada"}


@pytest.mark.parametrize("raw", ["not-json", "[]", '"texto"'])
@pytest.mark.parametrize("url", ["/ui/analyses/new/step/1", "/ui/analyses"])
def test_invalid_wizard_draft_is_400(functional_client, url, raw):
    response = functional_client.post(url, data={"wizard_state": raw, "name": "Nome"})
    assert response.status_code == 400
    assert response.json() == {"detail": "O rascunho do wizard é inválido."}


def test_missing_wizard_draft_starts_a_new_one(functional_client):
    response = functional_client.post("/ui/analyses/new/step/1", data={"name": "Sem rascunho"})
    assert response.status_code == 200
    assert "Empresa principal / TARGET" in response.text
    assert _state_from(response.text)["name"] == "Sem rascunho"


@pytest.mark.parametrize(
    ("step", "state", "form", "message", "heading"),
    [
        (1, {"name": ""}, {"name": "  "}, "Informe o nome da análise.", "Dê um nome à análise"),
        (
            2,
            {},
            {"target_name": "Alfa", "target_website": ""},
            "Informe o nome e o site da empresa principal.",
            "Empresa principal / TARGET",
        ),
        (
            3,
            {"competitors": [{"name": "Beta", "website": ""}]},
            {},
            "Informe nome e site para cada concorrente.",
            "Quais empresas quer comparar?",
        ),
        (
            3,
            {"competitors": [{"name": "Alfa", "website": "HTTPS://ALFA.EXAMPLE/"}]},
            {},
            "A empresa principal não pode ser adicionada como concorrente.",
            "Quais empresas quer comparar?",
        ),
        (
            3,
            {
                "competitors": [
                    {"name": "Beta", "website": "https://beta.example"},
                    {"name": "Beta 2", "website": "https://Beta.example/"},
                ]
            },
            {},
            "Remova empresas repetidas da lista de concorrentes.",
            "Quais empresas quer comparar?",
        ),
        (
            4,
            {},
            {"period": "custom", "from_date": "", "to_date": ""},
            "Informe as datas do período personalizado.",
            "Defina o período inicial",
        ),
        (
            4,
            {},
            {"period": "custom", "from_date": "2026-09-10", "to_date": "2026-09-01"},
            "A data inicial deve ser anterior à final.",
            "Defina o período inicial",
        ),
        (
            4,
            {},
            {"period": "year"},
            "Selecione um período válido.",
            "Defina o período inicial",
        ),
    ],
)
@pytest.mark.parametrize("htmx", [False, True])
def test_wizard_step_validation_keeps_user_on_step(
    functional_client, step, state, form, message, heading, htmx
):
    response = _post_step(
        functional_client, step, _state(**state), htmx=htmx, intent="next", **form
    )
    assert response.status_code == 200
    assert message in response.text
    assert heading in response.text
    assert ("<html" in response.text) is not htmx


def test_wizard_htmx_navigation_returns_partial_and_full_page_otherwise(functional_client):
    partial = _post_step(functional_client, 1, _state(), htmx=True, name="Nova", intent="next")
    full = _post_step(functional_client, 1, _state(), name="Nova", intent="next")
    for response in (partial, full):
        assert "Empresa principal / TARGET" in response.text
        assert _state_from(response.text)["name"] == "Nova"
    assert partial.text.lstrip().startswith('<div id="wizard-step-content"')
    assert "<html" in full.text


def test_wizard_back_returns_previous_step_and_keeps_draft(functional_client):
    response = _post_step(
        functional_client,
        3,
        _state(),
        intent="back",
        competitor_name_0="Beta editada",
        competitor_website_0="https://beta.example",
    )
    assert "Empresa principal / TARGET" in response.text
    assert "<html" in response.text
    assert _state_from(response.text)["competitors"] == [
        {"name": "Beta editada", "website": "https://beta.example", "search_term": ""}
    ]
    first = _post_step(functional_client, 1, _state(), intent="back", name="X")
    assert "Dê um nome à análise" in first.text


@pytest.mark.parametrize(
    ("period", "months", "days"),
    [("week", None, 6), ("month", 1, None), ("quarter", 3, None)],
)
def test_wizard_period_presets_become_concrete_dates(functional_client, period, months, days):
    response = _post_step(functional_client, 4, _state(), period=period, intent="next")
    today = date.today()
    expected_start = today - timedelta(days=days) if days else _months_before(today, months)
    state = _state_from(response.text)
    assert "Revise sua análise" in response.text
    assert (state["period"], state["from_date"], state["to_date"]) == (
        period,
        expected_start.isoformat(),
        today.isoformat(),
    )


def test_wizard_custom_period_keeps_informed_dates(functional_client):
    response = _post_step(
        functional_client,
        4,
        _state(),
        period="custom",
        from_date="2026-08-01",
        to_date="2026-08-31",
        intent="next",
    )
    state = _state_from(response.text)
    assert (state["from_date"], state["to_date"]) == ("2026-08-01", "2026-08-31")
    assert "01/08/2026 a 31/08/2026" in response.text


def test_wizard_competitor_list_actions_always_return_step_three_partial(functional_client):
    added = _post_step(
        functional_client,
        3,
        _state(),
        intent="add_competitor",
        new_competitor_name=" Gama ",
        new_competitor_website=" https://gama.example ",
        new_competitor_search_term="",
    )
    assert added.text.lstrip().startswith('<div id="wizard-step-content"')
    assert _state_from(added.text)["competitors"][-1] == {
        "name": "Gama",
        "website": "https://gama.example",
        "search_term": "",
    }

    incomplete = _post_step(
        functional_client, 3, _state(), intent="add_competitor", new_competitor_name="Gama"
    )
    assert "Informe nome e site antes de adicionar o concorrente." in incomplete.text
    assert len(_state_from(incomplete.text)["competitors"]) == 1

    for index in ("x", "5"):
        invalid = _post_step(
            functional_client, 3, _state(), intent="remove_competitor", remove_index=index
        )
        assert "Não foi possível remover esse concorrente." in invalid.text

    two = _state(
        competitors=[
            {"name": "Beta", "website": "https://beta.example", "search_term": ""},
            {"name": "Gama", "website": "https://gama.example", "search_term": ""},
        ]
    )
    without_index = _post_step(functional_client, 3, two, intent="remove_competitor")
    assert [item["name"] for item in _state_from(without_index.text)["competitors"]] == ["Beta"]


def test_wizard_review_step_next_renders_review_page(functional_client):
    response = _post_step(functional_client, 5, _state(), htmx=True, intent="next")
    assert "Revise sua análise" in response.text
    assert "<html" in response.text


def test_wizard_confirmation_revalidates_every_step(functional_client):
    response = functional_client.post(
        "/ui/analyses",
        data={"wizard_state": json.dumps(_state(target_website=""))},
        follow_redirects=False,
    )
    assert response.status_code == 200
    assert "Informe o nome e o site da empresa principal." in response.text
    assert "Revise sua análise" in response.text
    assert functional_client.get("/analyses").json() == []


def test_wizard_confirmation_redirect_carries_initial_collection_summary(functional_client):
    functional_client.app.state.source_providers = [BrokenNews(), MockXProvider()]
    state = _state(period="week")
    response = functional_client.post(
        "/ui/analyses", data={"wizard_state": json.dumps(state)}, follow_redirects=False
    )
    assert response.status_code == 303
    analysis_id = functional_client.get("/analyses").json()[0]["id"]
    today = date.today()
    assert response.headers["location"] == (
        f"/ui/analyses/{analysis_id}?view=overview&collection_status=partial&persisted=2"
        f"&from_date={(today - timedelta(days=6)).isoformat()}&to_date={today.isoformat()}"
    )
    page = functional_client.get(response.headers["location"])
    assert "Coleta inicial parcial" in page.text
    assert "2 evento(s) novo(s) persistido(s)" in page.text


def test_workspace_views_and_legacy_tabs(functional_client):
    analysis_id, _, _ = _create_analysis(functional_client)
    base = f"/ui/analyses/{analysis_id}"

    assert _title(functional_client.get(base).text) == "Workspace · Visão geral"
    assert _title(functional_client.get(f"{base}?view=timeline").text) == "Workspace · Timeline"
    assert _title(functional_client.get(f"{base}?view=companies").text) == "Workspace · Empresas"
    assert _title(functional_client.get(f"{base}?view=other").text) == "Workspace · Visão geral"
    assert _title(functional_client.get(f"{base}?tab=monitoring").text) == "Workspace · Timeline"
    assert (
        _title(functional_client.get(f"{base}?tab=monitoring&view=companies").text)
        == "Workspace · Empresas"
    )
    legacy_profile = functional_client.get(f"{base}?tab=profile", follow_redirects=False)
    assert legacy_profile.status_code == 303
    assert legacy_profile.headers["location"] == f"{base}/setup"


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("company=abc", "Revise os filtros da timeline"),
        ("source=FOO", "Revise os filtros da timeline"),
        ("from_date=31-12-2026", "Revise os filtros da timeline"),
        ("from_date=2026-09-10&to_date=2026-09-01", "A data inicial deve ser anterior à final."),
    ],
)
@pytest.mark.parametrize("suffix", ["?view=timeline&", "/timeline?"])
def test_invalid_timeline_filters_are_422(functional_client, query, detail, suffix):
    analysis_id, _, _ = _create_analysis(functional_client)
    response = functional_client.get(f"/ui/analyses/{analysis_id}{suffix}{query}")
    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_overview_status_banner_comes_from_query(functional_client):
    analysis_id, _, _ = _create_analysis(functional_client)
    page = functional_client.get(
        f"/ui/analyses/{analysis_id}?view=overview&collection_status=failure&persisted=0"
    )
    assert "A coleta inicial não foi concluída" in page.text
    assert "0 evento(s) novo(s) persistido(s)" in page.text
    assert "A coleta inicial" not in functional_client.get(f"/ui/analyses/{analysis_id}").text


def test_timeline_fragment_pushes_navigable_workspace_url(functional_client):
    analysis_id, target_id, _ = _create_analysis(functional_client)

    plain = functional_client.get(f"/ui/analyses/{analysis_id}/timeline")
    assert plain.status_code == 200
    assert plain.headers["HX-Push-Url"] == f"/ui/analyses/{analysis_id}?view=timeline"
    assert plain.text.lstrip().startswith('<div id="event-list"')

    filtered = functional_client.get(
        f"/ui/analyses/{analysis_id}/timeline?company={target_id}&source=&from_date=2026-09-01"
    )
    assert filtered.headers["HX-Push-Url"] == (
        f"/ui/analyses/{analysis_id}?company={target_id}&from_date=2026-09-01&view=timeline"
    )


def test_collect_form_without_htmx_redirects_to_overview(functional_client):
    analysis_id, _, _ = _create_analysis(functional_client)
    today = date.today()
    form = {"period": "custom", "from_date": today.isoformat(), "to_date": today.isoformat()}
    response = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect", data=form, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == (
        f"/ui/analyses/{analysis_id}?view=overview&collection_status=success&persisted=4"
        f"&from_date={today.isoformat()}&to_date={today.isoformat()}"
    )


@pytest.mark.parametrize(
    ("form", "detail"),
    [
        ({}, "Informe as datas do período personalizado."),
        ({"period": "year"}, "Selecione um período válido."),
        (
            {"period": "custom", "from_date": "2026-09-10", "to_date": "2026-09-01"},
            "A data inicial deve ser anterior à final.",
        ),
    ],
)
def test_collect_form_period_errors_are_422(functional_client, form, detail):
    analysis_id, _, _ = _create_analysis(functional_client)
    response = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect", data=form, headers={"HX-Request": "true"}
    )
    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_collect_form_htmx_fragment_reports_pairs_and_counts_all_events(
    functional_client, functional_db
):
    analysis_id, target_id, competitor_id = _create_analysis(functional_client)
    with functional_db() as session:
        session.add(
            Event(
                company_id=target_id,
                source=EventSource.GNEWS,
                title="Acontecimento antigo",
                url="https://news.example/old",
                published_at=datetime(2020, 1, 1, tzinfo=UTC),
            )
        )
        session.commit()
    functional_client.app.state.source_providers = [BrokenNews(), MockXProvider()]
    today = date.today()

    response = functional_client.post(
        f"/ui/analyses/{analysis_id}/collect",
        data={"period": "week"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"] == (
        f"/ui/analyses/{analysis_id}?view=overview"
        f"&from_date={(today - timedelta(days=6)).isoformat()}&to_date={today.isoformat()}"
    )
    text = response.text
    assert "Coleta parcial" in text
    assert "2 evento(s) novo(s) persistido(s) de 2 recebido(s)." in text
    for company_id in (target_id, competitor_id):
        assert (
            f"GNEWS · empresa {company_id}: "
            "Não foi possível consultar ou persistir os resultados desta fonte."
        ) in text
    # Limitação conhecida: o contador da resposta HTMX usa todos os eventos da análise.
    total = re.search(r'<dd id="event-total" hx-swap-oob="outerHTML"[^>]*>(\d+)</dd>', text)
    assert total.group(1) == "3"
    assert 'id="workspace-period" hx-swap-oob="outerHTML"' in text
    assert 'id="latest-received" hx-swap-oob="outerHTML"' in text


def test_setup_actions_redirect_to_setup_sections(functional_client):
    analysis_id, target_id, competitor_id = _create_analysis(functional_client)
    setup = f"/ui/analyses/{analysis_id}/setup"

    renamed = functional_client.post(setup, data={"name": "Novo nome"}, follow_redirects=False)
    assert (renamed.status_code, renamed.headers["location"]) == (303, f"{setup}?saved=1")
    assert "Alterações salvas." in functional_client.get(f"{setup}?saved=1").text

    added = functional_client.post(
        f"/ui/analyses/{analysis_id}/competitors",
        data={"name": "Gama", "website": "https://gama.example", "search_term": ""},
        follow_redirects=False,
    )
    assert (added.status_code, added.headers["location"]) == (303, f"{setup}#competitors")

    for method in ("post", "put"):
        updated = getattr(functional_client, method)(
            f"/ui/companies/{target_id}",
            data={
                "analysis_id": analysis_id,
                "name": "Alfa Bank",
                "website": "https://alfa.example",
                "market": "",
                "audience": "PJ",
            },
            follow_redirects=False,
        )
        assert (updated.status_code, updated.headers["location"]) == (
            303,
            f"{setup}?saved=1#companies",
        )
    company = functional_client.get(f"/analyses/{analysis_id}").json()["companies"][0]["company"]
    assert (company["market"], company["audience"]) == (None, "PJ")

    removed = functional_client.post(
        f"/ui/analyses/{analysis_id}/competitors/{competitor_id}/remove", follow_redirects=False
    )
    assert (removed.status_code, removed.headers["location"]) == (303, f"{setup}#competitors")

    other = functional_client.post(
        "/analyses", json={"name": "Outra", "target": {"name": "Delta", "website": "delta.example"}}
    ).json()
    unlinked = functional_client.post(
        f"/ui/companies/{other['companies'][0]['company']['id']}",
        data={"analysis_id": analysis_id, "name": "Delta", "website": "delta.example"},
    )
    assert unlinked.status_code == 404
    assert unlinked.json() == {"detail": "Empresa não vinculada à análise informada"}
    assert (
        functional_client.post(setup, data={"name": ""}, follow_redirects=False).status_code == 422
    )


def _add_event(functional_db, company_id):
    with functional_db() as session:
        event = Event(
            company_id=company_id,
            source=EventSource.GNEWS,
            title="Evento",
            url=f"https://news.example/{company_id}",
            published_at=datetime.now(UTC),
        )
        session.add(event)
        session.commit()
        return event.id


def test_event_analysis_form_without_htmx_redirects(functional_client, functional_db):
    analysis_id, target_id, _ = _create_analysis(functional_client)
    linked = functional_client.post(
        f"/ui/events/{_add_event(functional_db, target_id)}/analysis", follow_redirects=False
    )
    assert (linked.status_code, linked.headers["location"]) == (
        303,
        f"/ui/analyses/{analysis_id}?view=timeline",
    )

    with functional_db() as session:
        orphan = Company(name="Sem análise", website="https://orphan.example")
        session.add(orphan)
        session.commit()
        orphan_id = orphan.id
    unlinked = functional_client.post(
        f"/ui/events/{_add_event(functional_db, orphan_id)}/analysis", follow_redirects=False
    )
    assert (unlinked.status_code, unlinked.headers["location"]) == (303, "/ui/analyses")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            AnalysisConfigurationError("GEMINI_API_KEY não está configurada."),
            "GEMINI_API_KEY não está configurada.",
        ),
        (
            AnalysisProviderError("detalhe interno"),
            "O provider de análise não conseguiu gerar um resultado válido.",
        ),
    ],
)
def test_event_analysis_fragment_renders_controlled_errors(
    functional_client, functional_db, error, message
):
    _, target_id, _ = _create_analysis(functional_client)
    event_id = _add_event(functional_db, target_id)

    class FailingProvider:
        provider = None
        model = "unused"

        def analyze(self, event):
            raise error

    functional_client.app.state.analysis_provider = FailingProvider()
    response = functional_client.post(
        f"/ui/events/{event_id}/analysis", headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert f"Não foi possível analisar este acontecimento: {message}" in response.text
    assert "Tentar novamente" in response.text
    assert "detalhe interno" not in response.text
