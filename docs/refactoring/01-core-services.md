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

## 3. Simplificação da orquestração da coleta

- **Problema original:** `collect_analysis()` concentrava carregamento da análise (com consulta própria, duplicando `get_analysis`), iteração de empresas e providers, chamada externa, validação do retorno, deduplicação, criação de `Event`, commit/rollback, montagem de `ProviderOutcome`, acumuladores de totais e cálculo do status agregado.
- **Evidência:** complexidade ciclomática 11, a maior de `app/` (`ruff check app --select C901 --config "lint.mccabe.max-complexity=0"`); função de 83 linhas.
- **Técnica:** Extract Method; SRP; KISS. `collect_analysis` passou a só orquestrar: carrega a análise com `get_analysis`, executa `_collect_pair` para cada empresa e provider e agrega o resultado. `_collect_pair` mantém a transação de um par; `_validate_records` concentra as verificações de fonte e timezone; `_add_new_events` faz a deduplicação e cria os eventos; `_collection_status` deriva `success`/`partial`/`failure`. Os totais são somados a partir dos resultados por par.
- **Semântica transacional preservada:** uma transação por par empresa/provider, com `commit` ao final do par e `rollback` em qualquer exceção; todos os providers são tentados; a falha de um par não desfaz pares anteriores; `persisted` volta a 0 no par que falhou; a consulta de existência por `(company_id, source, url)` continua disparando o autoflush, o que detecta duplicatas no mesmo lote; `published_at` é convertido para UTC e `collected_at` é definido por evento; mensagens de erro e de log idênticas.
- **Diferença interna, sem efeito externo:** os registros de um par são validados antes de qualquer escrita, em vez de intercalar validação e escrita. Um par com registro inválido já terminava com `rollback` e `persisted = 0`; agora nenhuma linha chega a ser enviada à sessão nesse caso. O `if not outcomes` redundante do status foi removido, pois `successes == 0` já cobre a lista vazia.
- **Lacuna de blindagem encontrada e tratada:** com a validação antecipada, nenhum teste exercitava mais o `rollback` — remover o `rollback()` ou o reset de `persisted` não quebrava a suíte. Foi adicionado `test_collection_database_failure_discards_pending_events_of_that_pair_only` (falha `NOT NULL` no commit depois de eventos válidos), validado contra a implementação original em commit próprio, antes do refactoring.
- **Arquivos:** `app/services/collection.py`; `tests/test_characterization_core.py` (commits de teste separados).
- **Testes:** `pytest -q` → 165 passed, 1 skipped; teste PostgreSQL opt-in → 1 passed; `ruff check` e `ruff format --check` sem apontamentos.
- **Mutações manuais** (cada uma aplicada e revertida; suítes `test_characterization_core.py` e `test_functional_mvp.py`):

| Mutação | Implementação original | Implementação refatorada |
| --- | --- | --- |
| remover `session.rollback()` | 3 falhas | 1 falha |
| remover o reset `outcome.persisted = 0` | 3 falhas | 1 falha |
| status `failure` apenas sem resultados | — | 2 falhas |
| remover `session.commit()` | — | 5 falhas |

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Complexidade ciclomática de `collect_analysis` | 11 | 3 |
| Maior complexidade entre as funções de `collection.py` | 11 | 4 (`_validate_records`) |
| Linhas de `collect_analysis` (da assinatura ao fim do `return`) | 83 | 23 |
| Consultas próprias de carregamento de `Analysis` em `collection.py` | 1 | 0 (reutiliza `get_analysis`) |
