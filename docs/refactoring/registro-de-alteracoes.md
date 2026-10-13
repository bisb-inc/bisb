# Registro de alterações — Refatoração (Entrega 2)

Registro curto, por tarefa, do que foi alterado: como era e como ficou. Plano de origem: [web-layer-plan.md](web-layer-plan.md). Prompt: [03-web-layer-refactoring.md](../../prompts/refactoring/03-web-layer-refactoring.md).

---

## Frente A — Web Layer (Luca)

### Resumo
`backend/app/web/routes.py` (620 linhas, 27 funções, 16 rotas) foi dividido em módulos de lógica pura e módulos de rotas HTTP, sem alterar URLs, templates, services, models ou contratos REST. Os contratos de compatibilidade sem uso nos templates foram preservados por decisão de paridade (seção "Contratos de compatibilidade").

### Métricas (reproduzíveis)
| Métrica | Antes | Depois |
|---|---:|---:|
| Linhas em `app/web/routes.py` | 620 | arquivo removido |
| Maior módulo Web | 620 (`routes.py`) | 149 (`routes/workspace.py`) |
| Funções por módulo Web | 27 em um só | no máximo 5 |
| Decoradores de rota Web | 16 | 16 |
| Combinações caminho/método Web | 16 | 16 |
| Caminhos Web distintos | 13 | 13 |
| Módulos de lógica pura (sem FastAPI) | 0 | 3 (`periods`, `wizard`, `workspace`) |
| Testes (branch da Web, antes da integração) | 53 passed, 1 skipped | 121 passed, 1 skipped |
| ruff check / format | limpo | limpo |

Linhas por módulo, na branch integrada: `periods` 35, `wizard` 114, `workspace` 70, `errors` 23, `templating` 27 (inclui `safe_href`), `router` 11, `routes/pages` 34, `routes/wizard` 115, `routes/workspace` 149, `routes/setup` 105, `routes/event_analysis` 51. Na branch da Web, antes da integração, o teste PostgreSQL opt-in era pulado (é da Frente B).

### Contratos de compatibilidade
Preservados por decisão de paridade com a Entrega 1, embora os templates não os usem:
- `PUT /ui/companies/{id}`, com a mesma função e comportamento do POST.
- `?tab=profile` em `GET /ui/analyses/{id}` → 303 para `/ui/analyses/{id}/setup`; `?tab=monitoring` seleciona a Timeline quando `view` não é informado.
- `?step=` em `GET /ui/analyses/new` (`step: int = 1`, limitado a 1..5; valor não inteiro → 422 do FastAPI).

Removido: o uso de `CollectionRequest` na rota collect (validação redundante; `parse_period` já rejeita início posterior ao fim com o mesmo 422).

### Tarefas

### T0 — Rede de segurança: testes de caracterização da Web Layer
- **Arquivos:** criado `backend/tests/test_web_characterization.py` (nenhum outro alterado; `app/` intacto).
- **Como era:** `routes.py` tinha pouca cobertura dos ramos não-HTMX de `collect_form`/`analyze_event_form`, dos 422 de filtros/período, do wizard (`back`, 404, JSON inválido) e nenhum snapshot de rotas.
- **Como ficou:** 19 casos fixam o comportamento ATUAL: collect e analyze sem HX-Request → 303 (URLs esperadas); filtros inválidos da timeline → 422; período custom/preset inválido → 422; wizard back/404/400; `?tab=profile` → 303 e `?tab=monitoring` = timeline; `/ui/analyses/new?step=3` → 200; snapshot literal de (path, métodos) com o PUT incluído.
- **Testes:** só o novo arquivo; PUT, `?tab=` e `?step=` são fixados como contratos de compatibilidade (ver T10).
- **Verificação:** com DATABASE_URL de exemplo, `pytest` do arquivo novo: 19 passed; ruff check e ruff format --check limpos (a suíte completa foi executada nas tarefas seguintes).
- **Técnica:** testes de caracterização (golden master); snapshot de rotas percorre `_IncludedRouter.original_router` recursivamente, então continua válido quando a Web for dividida em sub-routers (FastAPI recente não expõe as rotas em `app.routes` diretamente).

### T1 — Extrair lógica de períodos para módulo puro
- **Arquivos**: criados `app/web/periods.py` e `tests/test_web_periods.py`; nenhum outro alterado (routes.py intocado, módulo ainda não importado).
- **Como era**: `_month_before`, `_range_for_preset`, `_parse_range` em `app/web/routes.py` linhas 40–75, misturadas com FastAPI e levantando HTTPException(422).
- **Como ficou**: `month_before`, `range_for_preset`, `parse_period` puras, sem FastAPI; só `ValueError` com as mesmas mensagens pt-BR e `raise ... from exc` preservado. A rota converterá para 422 depois.
- **Testes**: 12 casos sem TestClient/banco: presets week/month/quarter com `today` fixo, fim de mês (28/29 fev, 30 abr), virada de ano, custom válido, datas ausentes/inválidas (parametrizado), start>end, preset inválido; mensagens e `__cause__` checados.
- **Verificação**: pytest 69 passed, 1 skipped; ruff check OK; ruff format --check OK (41 arquivos).
- **Técnica**: Extract Module / Extract Function; separar regra de domínio da camada HTTP (ValueError no lugar de HTTPException).

### T2 — Lógica do wizard extraída para módulo puro
- **Arquivos**: criados `app/web/wizard.py` e `tests/test_web_wizard.py`; `routes.py` intocado (ainda não importa o módulo).
- **Como era**: `_wizard_state` (~137-157), `_sync_step_state` (~160-184), `_validate_wizard_step` (~187-215) e o bloco de intent add/remove_competitor do passo 3 em `wizard_step` (~265-282), todos em routes.py, acoplados a HTTPException.
- **Como ficou**: `new_state`, `load_state` (ValueError em vez de HTTP 400), `sync_step`, `validate_step` (usa `parse_period`, captura ValueError), `apply_competitor_intent` (retorna erro ou None, muta o state). Sem FastAPI/templates. Mensagens, regra de website (rstrip("/").lower()/casefold) e `except ValueError, IndexError:` preservados.
- **Testes**: 20 testes sem TestClient/banco (form como dict): estado padrão, load_state, sync por passo 1–4, cada regra de validate_step, add/remove (índice inválido, não numérico, e ausente remove o último, como no original).
- **Verificação**: pytest 102 passed/1 skipped; ruff check e format --check limpos.
- **Técnica**: extract function/module, separando lógica de domínio do transporte HTTP. Erros viram ValueError, e a rota os converterá em HTTPException depois.

### T3 — Módulo puro app/web/workspace.py
- **Arquivos**: app/web/workspace.py (novo), tests/test_web_workspace.py (novo); routes.py intocado.
- **Como era**: `_parse_timeline_filters` (~78-88), `_timeline_context` (~102-112), `_overview_data` (~115-134) em routes.py; URL de redirect duplicada em `create_analysis_form` (~352-357) e `collect_form` (~552-557).
- **Como ficou**: `parse_timeline_filters`, `timeline_context`, `overview_data`, `overview_redirect_url`, sem FastAPI/I/O. Filtros lançam ValueError (rota converte em 422); contexto sem "request" e com `latest_events` opcional (elimina recálculo de latest_received).
- **Testes**: 15 casos com SimpleNamespace (filtros, contexto, destaques GEMINI/fallback/limite 5, URL literal).
- **Verificação**: pytest 83 passed/1 skipped; ruff check e format --check limpos.
- **Técnica**: extração de lógica pura (functional core) + troca de HTTPException por ValueError para desacoplar do framework.

### T4 — Atualização da documentação da Web Layer
- **Arquivos**: `.ai/standards.md`, `.ai/architecture.md`, `backend/README.md` (`docs/arquitetura.md` e `README.md` não citavam `routes.py`/`?tab=`; inalterados).
- **Como era**: docs apontavam Web Routes em `app/web/routes.py` e citavam o redirecionamento dos parâmetros `?tab=profile`/`?tab=monitoring`.
- **Como ficou**: árvore e tabela descrevem `router.py`, `templating.py`, `periods.py`, `wizard.py`, `workspace.py` e `routes/` (pages, wizard, workspace, setup, event_analysis); link do README aponta para `app/web/routes/`; texto mantém só que as abas antigas não existem mais.
- **Testes**: n/a.
- **Verificação**: grep por `routes.py`, `?tab=`, `PUT /ui`; os únicos `PUT /companies/{id}` são da REST API (corretos), então não foram alterados.
- **Técnica**: edição textual pontual, preservando tom e formato.

### T5 — `templating.py`, `errors.py`, `router.py` (sessão principal)
- **Arquivos:** criados `app/web/templating.py`, `app/web/errors.py`, `app/web/router.py`, `app/web/routes/__init__.py`; `app/web/routes.py` renomeado para `legacy_routes.py` (transição); `app/main.py` importa `app.web.router`.
- **Como era:** `Jinja2Templates` criado dentro do `routes.py`; `HX-Request` comparado em 5 pontos; conversão de erro de período/filtro em `HTTPException` misturada à lógica.
- **Como ficou:** `templates` e `is_htmx` em um único lugar; `period_or_422` e `filters_or_422` concentram a tradução `ValueError` → 422 na borda HTTP.
- **Testes:** `test_functional_mvp.py` passou a apontar o monkeypatch para o módulo novo (feito na T9).
- **Verificação:** pytest 121 passed, 1 skipped; ruff limpo.
- **Técnica:** Extract Module, DRY (is_htmx).

### T6 — Extrair rotas pages, setup e event_analysis
**Arquivos**: criados app/web/routes/pages.py, setup.py, event_analysis.py (nada mais editado).
**Como era**: tudo em legacy_routes.py: home/login_page/analyses_page (~L215-240), analysis_setup/update_analysis_setup/add_competitor_form/remove_competitor_form/update_company_form (~L340-430), analyze_event_form (~L570-620); usavam `_context`, Jinja2Templates local e `request.headers.get("HX-Request")`.
**Como ficou**: três módulos, cada um com `router = APIRouter(tags=["Web UI"])`; usam `templates`/`is_htmx` de app.web.templating; contexto é dict simples sem "request"; update_company_form mantém POST e PUT. URLs, status, redirects, templates e mensagens idênticos; contratos de compatibilidade mantidos (T10). Ainda não incluídos (T9).
**Testes**: n/a (suíte segue exercitando o legacy).
**Verificação**: import dos módulos OK; comparação programática das 10 rotas (path, métodos, nome) com as do legacy, sem diferença; pytest 121 passed/1 skipped; ruff check e format --check limpos.
**Técnica**: cópia literal + substituição mecânica (extract module, replace helper por is_htmx/contexto simples).

### T7 — Rotas do wizard em app/web/routes/wizard.py
**Arquivos**: criado `app/web/routes/wizard.py` (nenhum outro editado; router ainda não incluído, integração na T9).
**Como era**: `new_analysis_page`, `wizard_step`, `create_analysis_form`, `_render_wizard`, `_wizard_state`, `_sync_step_state`, `_validate_wizard_step`, `_parse_range`, `_context` em `legacy_routes.py` (≈l.137-225, 250-358).
**Como ficou**: `router = APIRouter(tags=["Web UI"])` com as 3 rotas + `_render_wizard` (sem `_context`/"request" no contexto) + helper `_load_state_or_400` (ValueError de `wizard.load_state` -> HTTPException 400 com a mesma mensagem). Usa `wizard.new_state/sync_step/validate_step/apply_competitor_intent`, `period_or_422`, `overview_redirect_url`, `templates`/`is_htmx`. `collect_analysis` importado no nível do módulo. Parâmetro `step` mantido (ver T10).
**Testes**: nenhum novo; suíte completa: 121 passed, 1 skipped.
**Verificação**: ruff check/format OK; (path, métodos) idênticos aos do legacy; em uma aplicação de teste com as rotas do wizard do legacy substituídas pelas novas, na mesma ordem, test_functional_mvp + test_web_characterization: 31 passed.
**Técnica**: extração de módulo por cópia fiel + delegação à lógica pura já extraída; tradução de exceção na borda HTTP.

### T8 — Rotas de workspace (routes/workspace.py)
**Arquivos**: criado `app/web/routes/workspace.py` (nenhum outro editado; router ainda não incluído).
**Como era**: `analysis_page`, `timeline_fragment`, `collect_form` em `legacy_routes.py` (~linhas 318-350, 441-465, 468-508) usando `_parse_timeline_filters`, `_parse_range`, `_load_events`, `_timeline_context`, `_overview_data`, `_context` (chave "request").
**Como ficou**: mesmas 3 rotas em `APIRouter(tags=["Web UI"])`; usa `filters_or_422`/`period_or_422`, `workspace.timeline_context/overview_data/overview_redirect_url`, `analysis_events` inline, `templates`/`is_htmx`; `collect_analysis` importado no topo; `latest_received` via `latest_events=all_events`. Chaves de contexto, HX-Push-Url e redirect idênticos; `CollectionRequest` ainda presente nesta etapa (o uso na rota collect foi removido na T10).
**Testes**: nenhum novo; reaproveitados test_functional_mvp e test_web_characterization.
**Verificação**: (path, métodos) do novo router ⊂ legacy; em uma aplicação de teste com as 3 rotas do legacy substituídas pelas novas, na mesma ordem, os 31 testes de functional_mvp + characterization passam; suíte completa 121 passed/1 skipped; ruff check e format OK.
**Técnica**: extract module + replace inline helpers by pure functions; paridade provada por substituição de rotas em app temporário.

### T9 — Integração dos sub-routers (sessão principal)
- **Arquivos:** `app/web/router.py` (inclui pages, wizard, workspace, setup, event_analysis); `legacy_routes.py` removido; `tests/test_functional_mvp.py` (monkeypatch → `app.web.routes.wizard.collect_analysis`).
- **Como era:** um único `routes.py` de 620 linhas com 27 funções e 16 decoradores.
- **Como ficou:** 5 módulos de rotas HTTP + 3 módulos de lógica pura; `wizard` é incluído antes de `workspace` para `/ui/analyses/new` não cair em `/ui/analyses/{id}`.
- **Testes:** snapshot de rotas da T0 passou sem alteração (mesmas 16 rotas nesta etapa).
- **Verificação:** pytest 121 passed, 1 skipped; ruff check/format limpos.
- **Técnica:** Extract Module, SRP.

### T10 — Itens sem uso nos templates e contratos de compatibilidade (sessão principal)
- **Arquivos:** `routes/setup.py` (PUT), `routes/workspace.py` (`?tab=`, `CollectionRequest`), `routes/wizard.py` (`?step=`); testes `test_functional_mvp.py` e `test_web_characterization.py`.
- **Como era:** `PUT /ui/companies/{id}` usado só por 1 teste (o template usa POST); redirects `?tab=profile|monitoring` sem referência em templates ou JS; `?step=` sem referência; `CollectionRequest` reconstruído na rota apesar de `parse_period` já validar `start <= end`.
- **Como ficou:** PUT, `?tab=` e `?step=` permanecem como contratos de compatibilidade da Entrega 1, por decisão de paridade (retirados na branch da Web e restaurados na integração). A rota collect passa `start`/`end` direto ao serviço, sem `CollectionRequest` (schema mantido na REST API).
- **Testes:** `test_functional_mvp.py` usa PUT, como na Entrega 1; o snapshot de rotas inclui o PUT; testes de PUT igual ao POST, `?tab=profile` → 303 para o Setup, `?tab=monitoring` → Timeline sem `view` explícito, `?step=` limitado a 1..5 e `?step=abc` → 422.
- **Verificação:** ver "Integração e validação final".
- **Técnica:** remoção de validação redundante; preservação de contrato externo.

### T11 — Revisão independente da refatoração da Web Layer
- **Arquivos:** revisados `backend/app/web/{router,templating,errors,periods,wizard,workspace}.py`, `backend/app/web/routes/*.py`, `main.py`, testes `test_web_*` e docs (`.ai/*`, `backend/README.md`). Nenhum arquivo do repo foi editado.
- **Como era:** `routes.py` com 620 linhas (rotas, wizard, períodos, filtros e view-data misturados).
- **Como ficou:** comparação função a função com `git show HEAD:backend/app/web/routes.py`. Status, mensagens, redirects, ordem de validação, chaves de contexto, HX-Push-Url e rollback/log da coleta inicial estão preservados. Na branch da Web, só mudavam as remoções deliberadas (PUT, `?tab=`, `?step=`, `CollectionRequest` na Web); na integração, PUT, `?tab=` e `?step=` foram restaurados como contratos de compatibilidade.
- **Contexto de template:** a chave `request` saiu dos contextos. O único uso em template é `request.query_params` em `workspace/setup.html:7`, e o Starlette injeta `request` via `TemplateResponse(request=...)`. `url_for` também é coberto.
- **Testes:** 121 passed, 1 skipped, na branch da Web. Sem cobertura direta nessa branch: HX-Push-Url exato do fragmento com filtros múltiplos, ramo 404 de `update_company_form` (empresa não vinculada) e `?step=abc`. Na branch integrada, os três são cobertos: `test_timeline_fragment_pushes_navigable_workspace_url` e `test_setup_actions_redirect_to_setup_sections` (baseline) e `test_new_analysis_non_integer_step_returns_422`.
- **Verificação:** `pytest -q`, `ruff check` e `ruff format --check` passam. Templates e services sem alteração (`git status`).
- **Técnica:** leitura diff a diff, grep de dependências (`request`, `hx-put`, `tab=`, `routes.py`) e execução da suíte.
- **Achados menores:** `errors.py` é um adaptador fino, aceitável. `_load_state_or_400` fica em `routes/wizard.py`, enquanto os outros adaptadores 422 ficam em `errors.py`. As rotas `add_competitor_form` e `update_company_form` mantêm `request` sem uso, como no original.

### Achados menores da revisão (não corrigidos)
- `_load_state_or_400` (`routes/wizard.py`) repete o padrão de `errors.py`, mas ficou local.
- `analysis_events(...)` é chamado em 2 pontos de `routes/workspace.py` (duplicação pequena).
- O 404 de `update_company_form` para empresa não vinculada e o `HX-Push-Url` da timeline com vários filtros não tinham teste na branch da Web; na branch integrada, são cobertos pelos testes de caracterização do baseline (ver T11).

---

## Frente B — Core / Services / Segurança (Felipe)

### Resumo
A frente Core partiu do baseline da branch `refactoring`: testes de caracterização da REST API, da Web UI e da coleta, e o teste PostgreSQL opt-in reescrito para o fluxo do wizard ([00-baseline.md](00-baseline.md)). Sobre esse baseline, a branch `refactor/felipe-core` aplicou quatro intervenções, cada uma em commit próprio e validada pela suíte completa ([01-core-services.md](01-core-services.md)):

- **Erros de aplicação:** `NotFoundError`, `ConflictError` e `BusinessRuleError` sob `ApplicationError`, traduzidos para 404, 409 e 422 por handlers globais em `app/http_errors.py`, registrados em `create_app()`. Os serviços deixaram de depender de FastAPI, com os mesmos status e corpos de erro.
- **Coleta:** `collect_analysis()` passou a só orquestrar (Extract Method). A transação por par empresa/provider e as mensagens foram preservadas, e mutações manuais confirmaram a cobertura do `rollback` e do `commit`.
- **Identidade por website:** a busca de empresa por site normalizado em `companies.py` foi unificada (DRY). A regra divergente do wizard foi mantida, porque unificá-la mudaria o comportamento observável.
- **Segurança:** auditoria de segredos, `.env`, `SecretStr`, logs, providers, SQL, templates, dependências, Docker e exceções. Houve um achado corrigido, o filtro `safe_href` contra esquemas executáveis em links, e uma dívida documentada sobre requisições cross-site e validação de Host ([02-security-audit.md](02-security-audit.md)).

### Métricas finais
| Métrica | Baseline | Depois |
|---|---:|---:|
| Módulos de `app/services/` que importam FastAPI | 5 | 0 |
| `raise HTTPException` em `app/services/` | 15 | 0 |
| Complexidade ciclomática de `collect_analysis` | 11 | 3 |
| Implementações da busca de empresa por website em `companies.py` | 2 | 1 |

Os comandos de medição estão em [00-baseline.md](00-baseline.md#métricas-de-referência), e os resultados por intervenção em [01-core-services.md](01-core-services.md).

### Pontos levantados pela Frente A
- `services/collection.py`, default `providers=None`: mantido, pois é usado pelos testes de caracterização da coleta; o import interno de FastAPI foi removido.
- `__all__` de `services/event_analysis.py` e `providers/__init__.py`: mantidos, pois não afetam o comportamento.
- Regra de site do wizard × `normalize_website`: divergência confirmada e mantida como dívida ([01-core-services.md](01-core-services.md#4-identidade-de-empresa-por-site)).
- Tradução de erros na Web: concentrada nos handlers globais; a única captura explícita é a de `create_analysis_form`, que exibe `ApplicationError.message` na etapa de revisão do wizard.

---

## Integração e validação final

Branch `refactor/integration`: `refactor/felipe-core` com merge de `review/luca-web` (cópia de `refactor/web-layer`, HEAD `f82d959`, derivada de `v1.0-mvp`). Os commits da Frente A entram sem alteração.

### Resolução de conflitos
- `backend/app/web/routes.py`: removido pela Frente A e alterado pela Frente B. As alterações da Frente B passam para os módulos novos: o filtro `safe_href` e seu registro em `app/web/templating.py`; a captura de `ApplicationError` (exibindo `exc.message` na etapa de revisão) em `create_analysis_form`, `app/web/routes/wizard.py`.
- `backend/README.md`: mantido o texto da Frente B (limitação do teste PostgreSQL resolvida) com o link da Frente A para `app/web/routes/`.
- Contratos de compatibilidade (PUT, `?tab=`, `?step=`) restaurados em commit próprio, com os testes da Frente A ajustados ao contrato original. Os testes de caracterização comuns não foram alterados.

### Validação
| Verificação | Resultado |
|---|---|
| `uv run --locked pytest -q` | 246 passed, 1 skipped (teste PostgreSQL opt-in sem `TEST_POSTGRES_URL`) |
| `uv run --locked pytest -q` com `TEST_POSTGRES_URL` | 247 passed |
| `ruff check .` / `ruff format --check .` | limpo |
| `alembic check` | sem novas operações |
| `npm run build` | concluído; CSS gerado idêntico ao versionado |
| OpenAPI completo `v1.0-mvp` × integrado — evidência auxiliar não reproduzível a partir do repositório (comparação por script não versionado) | idêntico |
| Rotas REST (caminho/método) | 13, idênticas |
| Rotas Web | 16 combinações caminho/método em 13 caminhos distintos, idênticas a `v1.0-mvp` |
| Golden master da Web UI (117 requisições, HTML normalizado) — **evidência auxiliar não reproduzível a partir do repositório** (o executor não foi versionado) | idêntico a `v1.0-mvp` e a `refactor/felipe-core`; a branch da Frente A isolada diverge em 6 (`?step=3`, `?step=9`, `?tab=profile`, `?tab=monitoring`, PUT e a página de Setup seguinte ao PUT) |
| Contratos pontuais | PUT = POST (303 para `setup?saved=1#companies`); `?tab=profile` → 303 para `/setup`; `?tab=monitoring` → Timeline; `?tab=monitoring&view=companies` → Empresas; `?step=3` → etapa 3; `?step=abc` → 422 |
| Mutação: `safe_href` devolvendo a URL sem filtrar | 8 testes de `test_security_links.py` falham |
| Mutação: captura de `HTTPException` no lugar de `ApplicationError` | 2 testes de `test_characterization_core.py` falham |
| `app/services/` importando FastAPI | 0 |

O inventário de rotas REST (pelo OpenAPI) e Web e os contratos pontuais são reproduzíveis pelos testes versionados (`test_rest_contract_inventory_is_preserved`, `test_web_routes_snapshot`, `test_web_url_is_still_served` e os testes de contratos de compatibilidade em `test_web_characterization.py`). As mutações foram aplicadas manualmente e revertidas.

A auditoria de dependências (`npm audit` e `pip-audit`) foi executada na frente Core e está registrada em [02-security-audit.md](02-security-audit.md); `uv.lock`, `pyproject.toml`, `package.json` e `package-lock.json` não mudaram desde então.

Não houve smoke test manual da UI na branch integrada; wizard, coleta, Timeline, Setup, análise de evento e respostas HTMX são exercitados pelos testes HTTP.
