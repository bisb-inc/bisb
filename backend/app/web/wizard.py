"""Pure wizard state logic (no FastAPI, no templates)."""

import json
from typing import Any

from app.web.periods import parse_period, range_for_preset

INVALID_DRAFT_MESSAGE = "O rascunho do wizard é inválido."


def new_state() -> dict[str, Any]:
    start, end = range_for_preset("week")
    return {
        "name": "",
        "target_name": "",
        "target_website": "",
        "target_search_term": "",
        "competitors": [],
        "period": "week",
        "from_date": start.isoformat(),
        "to_date": end.isoformat(),
    }


def load_state(raw: str | None) -> dict[str, Any]:
    if not raw:
        return new_state()
    try:
        state = json.loads(raw)
    except TypeError, json.JSONDecodeError:
        raise ValueError(INVALID_DRAFT_MESSAGE) from None
    if not isinstance(state, dict):
        raise ValueError(INVALID_DRAFT_MESSAGE)
    state.setdefault("competitors", [])
    return state


def sync_step(state: dict[str, Any], form, step: int) -> None:
    if step == 1:
        state["name"] = str(form.get("name", state.get("name", ""))).strip()
    elif step == 2:
        for key in ("target_name", "target_website", "target_search_term"):
            state[key] = str(form.get(key, state.get(key, ""))).strip()
    elif step == 3:
        current = list(state.get("competitors", []))
        rebuilt = []
        for index, old in enumerate(current):
            item = {
                "name": str(form.get(f"competitor_name_{index}", old.get("name", ""))).strip(),
                "website": str(
                    form.get(f"competitor_website_{index}", old.get("website", ""))
                ).strip(),
                "search_term": str(
                    form.get(f"competitor_search_{index}", old.get("search_term", ""))
                ).strip(),
            }
            rebuilt.append(item)
        state["competitors"] = rebuilt
    elif step == 4:
        state["period"] = str(form.get("period", state.get("period", "week")))
        state["from_date"] = str(form.get("from_date", state.get("from_date", "")))
        state["to_date"] = str(form.get("to_date", state.get("to_date", "")))


def validate_step(state: dict[str, Any], step: int) -> str | None:
    if step == 1 and not state.get("name"):
        return "Informe o nome da análise."
    if step == 2 and (not state.get("target_name") or not state.get("target_website")):
        return "Informe o nome e o site da empresa principal."
    if step == 3:
        competitors = state.get("competitors", [])
        if not competitors:
            return "Adicione ao menos um concorrente para continuar."
        if any(not item.get("name") or not item.get("website") for item in competitors):
            return "Informe nome e site para cada concorrente."
        if state.get("target_website") and any(
            item.get("website", "").rstrip("/").lower()
            == state["target_website"].rstrip("/").lower()
            for item in competitors
        ):
            return "A empresa principal não pode ser adicionada como concorrente."
        sites = [item.get("website", "").rstrip("/").casefold() for item in competitors]
        if len(set(sites)) != len(sites):
            return "Remova empresas repetidas da lista de concorrentes."
    if step == 4:
        try:
            start, end = parse_period(
                state.get("period", ""), state.get("from_date"), state.get("to_date")
            )
        except ValueError as exc:
            return str(exc)
        state["from_date"], state["to_date"] = start.isoformat(), end.isoformat()
    return None


def apply_competitor_intent(state: dict[str, Any], form, intent: str) -> str | None:
    error = None
    if intent == "add_competitor":
        name = str(form.get("new_competitor_name", "")).strip()
        website = str(form.get("new_competitor_website", "")).strip()
        search_term = str(form.get("new_competitor_search_term", "")).strip()
        if not name or not website:
            error = "Informe nome e site antes de adicionar o concorrente."
        else:
            state["competitors"].append(
                {"name": name, "website": website, "search_term": search_term}
            )
    elif intent == "remove_competitor":
        try:
            index = int(form.get("remove_index", -1))
            state["competitors"].pop(index)
        except ValueError, IndexError:
            error = "Não foi possível remover esse concorrente."
    return error
