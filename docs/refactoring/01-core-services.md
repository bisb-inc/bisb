# Refactoring — Frente Core / Services

Evidências das intervenções da frente Core/Services sobre o baseline registrado em [00-baseline.md](00-baseline.md). Cada seção corresponde a um commit da branch `refactor/felipe-core`.

## 1. Erros de aplicação e mapeamento na fronteira HTTP

- **Problema original:** as regras de aplicação sinalizavam falhas esperadas com `fastapi.HTTPException`, de modo que a camada de serviços escolhia códigos de status HTTP.
- **Evidência:** 5 de 5 módulos de `app/services/` importam FastAPI e há 15 `raise HTTPException` nesses módulos (métricas em [00-baseline.md](00-baseline.md#métricas-de-referência)).
- **Técnica:** Separation of Concerns; Dependency Inversion — os serviços passam a depender de tipos próprios, e a fronteira HTTP traduz esses tipos.
- **Decisão de desenho:** três tipos semânticos sob `ApplicationError`, um por status já usado pelos serviços: `NotFoundError` (404), `ConflictError` (409) e `BusinessRuleError` (422). O nome `ValidationError` foi evitado para não colidir com `pydantic.ValidationError`. Um único registro de handlers em `create_app` atende REST API e Web Routes, reproduzindo o corpo `{"detail": ...}` das respostas de erro do FastAPI.
- **Arquivos:** `app/services/errors.py` (novo), `app/http_errors.py` (novo), `app/main.py`, `tests/test_http_errors.py` (novo).
- **Comportamento preservado:** nenhum serviço usa os novos tipos ainda; as respostas existentes não mudam.
- **Testes:** `uv run --locked pytest -q` → 164 passed, 1 skipped; `ruff check` e `ruff format --check` sem apontamentos.

## 2. Desacoplamento dos serviços em relação ao FastAPI

- **Problema original:** mesmo com os tipos da seção 1, os serviços ainda lançavam `HTTPException`; `collection.py` importava FastAPI dentro da função apenas para o 404.
- **Evidência:** `grep -l fastapi app/services/*.py` → 5 arquivos; `grep -c 'raise HTTPException' app/services/*.py` → 15 ocorrências.
- **Técnica:** Decoupling; Dependency Inversion; substituição direta de cada `HTTPException(status, detail)` pelo tipo semântico equivalente, com a mesma mensagem.
- **Arquivos:** `app/services/analyses.py`, `collection.py`, `companies.py`, `events.py`, `event_analysis.py`; `app/web/routes.py` (ajuste mínimo: a confirmação do wizard captura `ApplicationError` em vez de `HTTPException` para exibir o erro do serviço na etapa de revisão); `.ai/standards.md` (convenção de erros).
- **Comportamento preservado:** status e corpo de todos os erros de serviço pela REST API e pela Web UI (`test_rest_not_found_errors_keep_status_and_detail`, `test_rest_business_rule_errors_keep_status_and_detail`, `test_rest_event_analysis_concurrent_save_conflict_is_409`, `test_web_routes_expose_service_errors_with_same_status_and_detail`); conflito exibido na revisão do wizard (`test_wizard_confirmation_renders_service_conflict_on_review_step`). Os `HTTPException` lançados pela própria camada HTTP (`app/web/routes.py`, `app/api/routes/event_analyses.py`) permanecem, pois pertencem à fronteira.
- **Testes:** `pytest -q` → 164 passed, 1 skipped; teste PostgreSQL opt-in → 1 passed; `ruff check` e `ruff format --check` sem apontamentos.

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Módulos de `app/services/` que importam FastAPI | 5 | 0 |
| `raise HTTPException` em `app/services/` | 15 | 0 |
