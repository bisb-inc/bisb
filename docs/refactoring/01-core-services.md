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
