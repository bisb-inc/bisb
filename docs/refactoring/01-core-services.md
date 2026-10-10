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

## 4. Identidade de empresa por site

- **Investigação:** a regra de identificação por site aparece em três pontos. Em `app/services/companies.py`, `get_or_create_company` e `update_company` repetiam a mesma busca — carregar empresas com site e procurar a primeira cujo `normalize_website` coincide — diferindo apenas na exclusão da própria empresa na edição. Em `app/web/routes.py`, `_validate_wizard_step` compara sites dos concorrentes com `rstrip("/").lower()`/`casefold()`, uma regra diferente de `normalize_website`. Não há outra regra de site nas rotas REST, nos schemas ou nas migrações.
- **Confirmado e tratado (serviços):** duplicação real dentro de `companies.py`. **Técnica:** DRY; Single Source of Truth; Extract Method. A busca passou a existir apenas em `_find_company_by_website(session, website, exclude_id=None)`, reutilizada pelas duas funções; a comparação de nomes ganhou o nome `_name_key`. A consulta SQL, a ordem de avaliação (404 antes do conflito na edição) e as mensagens são as mesmas.
- **Confirmado e não alterado (wizard):** a regra do wizard diverge da regra do serviço, mas unificá-la mudaria o comportamento observável — um concorrente igual ao TARGET escrito sem protocolo (`alfa.example` × `https://alfa.example`) passaria a ser recusado na etapa 3 com a mensagem do wizard, em vez de na confirmação com a mensagem do serviço. O resultado final já é seguro: o serviço recusa o cadastro e nenhuma análise é criada (`test_wizard_site_rule_differs_from_service_identity_rule`). A mudança também pertence à Web Layer. Fica registrada como dívida para decisão do grupo.
- **Arquivos:** `app/services/companies.py`.
- **Comportamento preservado:** `test_normalize_website_ignores_only_trivial_differences`, `test_company_identity_reuses_site_variants_with_equivalent_names`, `test_rest_competitor_addition_is_idempotent_and_own_site_can_be_kept`, conflitos 409 de criação e edição em `test_rest_business_rule_errors_keep_status_and_detail` e pela Web em `test_web_routes_expose_service_errors_with_same_status_and_detail`.
- **Testes:** `pytest -q` → 165 passed, 1 skipped; teste PostgreSQL opt-in → 1 passed; `ruff check` e `ruff format --check` sem apontamentos.

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Implementações da busca de empresa por site normalizado em `companies.py` | 2 | 1 |
| Complexidade ciclomática de `update_company` | 6 | 4 |
| Complexidade ciclomática de `get_or_create_company` | 4 | 3 |
| Regras distintas de comparação de site na aplicação | 2 | 2 (wizard mantido, ver acima) |

## Diagnóstico da frente Core

| Item do plano | Situação | Tratamento |
| --- | --- | --- |
| P1 — Services dependem de FastAPI | Confirmado (5 de 5 módulos, 15 `raise HTTPException`) | Seções 1 e 2 |
| P2 — Coleta concentra responsabilidades | Confirmado (complexidade 11, 83 linhas) | Seção 3 |
| P3 — Identidade de Company por site não reutilizada | Confirmado nos serviços; divergência confirmada no wizard | Seção 4 (serviços); wizard mantido como dívida |
| Auditoria de segurança | Executada | [02-security-audit.md](02-security-audit.md) |

### Alterações avaliadas e rejeitadas

- **Hierarquia maior de exceções ou exceções por entidade** (`AnalysisNotFoundError`, `CompanyNotFoundError`…): os serviços só usam três status distintos; tipos adicionais não mudariam nenhum tratamento (KISS/YAGNI).
- **Repository Pattern ou camada de acesso a dados separada:** os serviços usam a `Session` do SQLAlchemy diretamente, sem duplicação de consultas que justifique outra camada.
- **Tipar `status` de `CollectionResult`/`ProviderOutcome` como `Literal`:** alteraria o schema OpenAPI publicado (`string` → `enum`), ou seja, o contrato REST.
- **Reordenar a validação de período em `analysis_events`** (hoje verificada depois de montar a consulta): sem efeito observável nem ganho de legibilidade relevante.
- **Unificar a regra de site do wizard com `normalize_website`:** muda quando e com qual mensagem o erro aparece e pertence à Web Layer (seção 4).
- **Remover os providers mockados padrão de `collect_analysis(providers=None)`:** usados pelos testes de serviço; as rotas sempre passam `app.state.source_providers`.

## Validação final da branch `refactor/felipe-core`

| Comando | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 176 passed, 1 skipped |
| `uv run --locked pytest -q` com `TEST_POSTGRES_URL` | 177 passed |
| `uv run --locked ruff check .` | sem erros |
| `uv run --locked ruff format --check .` | 45 arquivos formatados |
| `uv run --locked alembic check` | `No new upgrade operations detected.` |
| `npm run build` | concluído; `app.css` e `htmx.min.js` idênticos aos versionados |

| Métrica | Baseline | `refactor/felipe-core` |
| --- | ---: | ---: |
| Módulos de `app/services/` que importam FastAPI | 5 | 0 |
| `raise HTTPException` em `app/services/` | 15 | 0 |
| Complexidade ciclomática de `collect_analysis` | 11 | 3 |
| Maior complexidade ciclomática em `app/services/` | 11 | 7 (`analyze_event`, `analysis_events`) |
| Implementações da busca de empresa por site em `companies.py` | 2 | 1 |
| Linhas em `app/web/routes.py` | 620 | 637 (+17: `safe_href` e captura de `ApplicationError`) |
| Testes automatizados coletados | 162 | 177 |
| Rotas REST no OpenAPI / URLs Web | 13 / 16 | 13 / 16 |

## Dívidas remanescentes da frente Core

- Regra de comparação de sites do wizard diferente de `normalize_website` (seção 4).
- Contagens da resposta HTMX da coleta calculadas sobre todos os eventos da análise (limitação registrada no `backend/README.md` e fixada por teste).
- Formato de `website` não validado na entrada; a proteção contra esquemas executáveis está na saída ([02-security-audit.md](02-security-audit.md)).
- Busca de empresa por site carrega todas as empresas com site e normaliza em Python; adequado ao volume do MVP, mas linear no número de empresas.
