import json

import pytest

from app.web import wizard

COMP = {"name": "Acme", "website": "https://acme.com", "search_term": ""}


def test_new_state_defaults():
    state = wizard.new_state()
    assert state["period"] == "week"
    assert state["name"] == "" and state["competitors"] == []
    assert state["from_date"] <= state["to_date"]


def test_load_state_empty_returns_default():
    assert wizard.load_state(None) == wizard.load_state("") == wizard.new_state()


@pytest.mark.parametrize("raw", ["{not json", "[1, 2]", '"x"'])
def test_load_state_invalid(raw):
    with pytest.raises(ValueError, match="O rascunho do wizard é inválido."):
        wizard.load_state(raw)


def test_load_state_sets_competitors_default():
    assert wizard.load_state(json.dumps({"name": "x"})) == {"name": "x", "competitors": []}


def test_sync_step_1_and_2():
    state = wizard.new_state()
    wizard.sync_step(state, {"name": "  Análise "}, 1)
    assert state["name"] == "Análise"
    wizard.sync_step(state, {"target_name": " A ", "target_website": " https://a.com "}, 2)
    assert state["target_name"] == "A"
    assert state["target_website"] == "https://a.com"
    assert state["target_search_term"] == ""


def test_sync_step_3_rebuilds_indexed_competitors():
    state = {"competitors": [dict(COMP), {"name": "B", "website": "b.com", "search_term": "s"}]}
    form = {"competitor_name_0": " Novo ", "competitor_search_1": " termo "}
    wizard.sync_step(state, form, 3)
    assert state["competitors"] == [
        {"name": "Novo", "website": "https://acme.com", "search_term": ""},
        {"name": "B", "website": "b.com", "search_term": "termo"},
    ]


def test_sync_step_4():
    state = {"period": "week", "from_date": "a", "to_date": "b"}
    wizard.sync_step(state, {"period": "custom", "from_date": "2026-01-01"}, 4)
    assert state == {"period": "custom", "from_date": "2026-01-01", "to_date": "b"}


def test_validate_step_1_and_2():
    assert wizard.validate_step({"name": ""}, 1) == "Informe o nome da análise."
    assert wizard.validate_step({"name": "x"}, 1) is None
    msg = "Informe o nome e o site da empresa principal."
    assert wizard.validate_step({"target_name": "A", "target_website": ""}, 2) == msg
    assert wizard.validate_step({"target_name": "", "target_website": "a"}, 2) == msg
    assert wizard.validate_step({"target_name": "A", "target_website": "a"}, 2) is None


def test_validate_step_3_rules():
    v = wizard.validate_step
    assert v({"competitors": []}, 3) == "Adicione ao menos um concorrente para continuar."
    both = "Informe nome e site para cada concorrente."
    assert v({"competitors": [{"name": "", "website": "x"}]}, 3) == both
    assert v({"competitors": [{"name": "x", "website": ""}]}, 3) == both
    same = "A empresa principal não pode ser adicionada como concorrente."
    state = {
        "target_website": "https://T.com/",
        "competitors": [COMP | {"website": "https://t.com"}],
    }
    assert v(state, 3) == same
    dup = {"competitors": [COMP, COMP | {"name": "Outro", "website": "HTTPS://ACME.com/"}]}
    assert v(dup, 3) == "Remova empresas repetidas da lista de concorrentes."
    assert v({"target_website": "https://t.com", "competitors": [COMP]}, 3) is None


def test_validate_step_4_invalid_period():
    state = {"period": "custom", "from_date": "2026-02-01", "to_date": "2026-01-01"}
    error = wizard.validate_step(state, 4)
    assert isinstance(error, str) and error
    assert state["from_date"] == "2026-02-01"


def test_validate_step_4_normalizes_dates():
    state = {"period": "custom", "from_date": "2026-01-01", "to_date": "2026-01-10"}
    assert wizard.validate_step(state, 4) is None
    assert (state["from_date"], state["to_date"]) == ("2026-01-01", "2026-01-10")


def test_add_competitor():
    state = {"competitors": []}
    form = {
        "new_competitor_name": " Acme ",
        "new_competitor_website": " https://acme.com ",
        "new_competitor_search_term": " t ",
    }
    assert wizard.apply_competitor_intent(state, form, "add_competitor") is None
    assert state["competitors"] == [
        {"name": "Acme", "website": "https://acme.com", "search_term": "t"}
    ]


def test_add_competitor_missing_fields():
    state = {"competitors": []}
    error = wizard.apply_competitor_intent(state, {"new_competitor_name": "A"}, "add_competitor")
    assert error == "Informe nome e site antes de adicionar o concorrente."
    assert state["competitors"] == []


def test_remove_competitor():
    state = {"competitors": [dict(COMP), {"name": "B", "website": "b"}]}
    assert wizard.apply_competitor_intent(state, {"remove_index": "0"}, "remove_competitor") is None
    assert state["competitors"] == [{"name": "B", "website": "b"}]


@pytest.mark.parametrize("value", ["5", "abc"])
def test_remove_competitor_invalid(value):
    state = {"competitors": [dict(COMP)]}
    error = wizard.apply_competitor_intent(state, {"remove_index": value}, "remove_competitor")
    assert error == "Não foi possível remover esse concorrente."
    assert len(state["competitors"]) == 1


def test_remove_competitor_without_index_removes_last():
    state = {"competitors": [dict(COMP), {"name": "B", "website": "b"}]}
    assert wizard.apply_competitor_intent(state, {}, "remove_competitor") is None
    assert state["competitors"] == [COMP]
