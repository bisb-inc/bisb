# Registro de alterações — Refatoração (Entrega 2)

Registro curto, por tarefa, do que foi alterado: como era e como ficou. Plano de origem: [web-layer-plan.md](web-layer-plan.md). Prompt: [03-web-layer-refactoring.md](../../prompts/refactoring/03-web-layer-refactoring.md).

---

## Frente A — Web Layer (Luca)

### Resumo
`backend/app/web/routes.py` (620 linhas, 27 funções, 16 rotas) foi dividido em módulos de lógica pura e módulos de rotas HTTP, sem alterar URLs, templates, services, models ou contratos REST. Foram removidos 4 itens sem uso real (seção "Código removido").

### Métricas (reproduzíveis)
| Métrica | Antes | Depois |
|---|---:|---:|
| Linhas em `app/web/routes.py` | 620 | arquivo removido |
| Maior módulo Web | 620 (`routes.py`) | 144 (`routes/workspace.py`) |
| Funções por módulo Web | 27 em um só | no máximo 5 |
| Decoradores de rota Web | 16 | 15 |
| URLs Web distintas | 15 | 15 |
| Módulos de lógica pura (sem FastAPI) | 0 | 3 (`periods`, `wizard`, `workspace`) |
| Testes | 53 passed, 1 skipped | 121 passed, 1 skipped |
| ruff check / format | limpo | limpo |

Linhas por módulo: `periods` 35, `wizard` 114, `workspace` 70, `errors` 23, `templating` 10, `router` 11, `routes/pages` 34, `routes/wizard` 114, `routes/workspace` 144, `routes/setup` 104, `routes/event_analysis` 51. O teste PostgreSQL opt-in continua pulado (é da Frente B).

### Código removido
- `PUT /ui/companies/{id}` (só um teste usava; o template usa POST).
- Redirects `?tab=profile` e `?tab=monitoring` (sem referências).
- Parâmetro `?step=` de `GET /ui/analyses/new` (sem referências).
- Uso de `CollectionRequest` na rota collect (validação redundante).

Efeito observado na revisão: `?step=abc` antes dava 422 e agora é ignorado.

### Tarefas

### T0 — Rede de segurança: testes de caracterização da Web Layer
- **Arquivos:** criado `backend/tests/test_web_characterization.py` (nenhum outro alterado; `app/` intacto).
- **Como era:** `routes.py` tinha pouca cobertura dos ramos não-HTMX de `collect_form`/`analyze_event_form`, dos 422 de filtros/período, do wizard (`back`, 404, JSON inválido) e nenhum snapshot de rotas.
- **Como ficou:** 19 casos fixam o comportamento ATUAL: collect e analyze sem HX-Request → 303 (URLs esperadas); filtros inválidos da timeline → 422; período custom/preset inválido → 422; wizard back/404/400; `?tab=profile` → 303 e `?tab=monitoring` = timeline; `/ui/analyses/new?step=3` → 200; snapshot literal de (path, métodos) com o PUT incluído.
- **Testes:** só o novo arquivo; os comentários marcam PUT, `?tab=` e `?step=` como comportamento a ser removido depois.
- **Verificação:** com DATABASE_URL de exemplo, `pytest` do arquivo novo: 19 passed; ruff check e ruff format --check limpos (a suíte completa inclui arquivos de outros agentes em paralelo).
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
**Como ficou**: três módulos, cada um com `router = APIRouter(tags=["Web UI"])`; usam `templates`/`is_htmx` de app.web.templating; contexto é dict simples sem "request"; update_company_form mantém POST e PUT. URLs, status, redirects, templates e mensagens idênticos; código morto mantido (T10). Ainda não incluídos (T9).
**Testes**: n/a (suíte segue exercitando o legacy).
**Verificação**: import dos módulos OK; script no scratchpad (cmp_t6.py) confirmou 10 rotas (path, métodos, nome) idênticas às do legacy; pytest 121 passed/1 skipped; ruff check e format --check limpos.
**Técnica**: cópia literal + substituição mecânica (extract module, replace helper por is_htmx/contexto simples).

### T7 — Rotas do wizard em app/web/routes/wizard.py
**Arquivos**: criado `app/web/routes/wizard.py` (nenhum outro editado; router ainda não incluído, integração na T9).
**Como era**: `new_analysis_page`, `wizard_step`, `create_analysis_form`, `_render_wizard`, `_wizard_state`, `_sync_step_state`, `_validate_wizard_step`, `_parse_range`, `_context` em `legacy_routes.py` (≈l.137-225, 250-358).
**Como ficou**: `router = APIRouter(tags=["Web UI"])` com as 3 rotas + `_render_wizard` (sem `_context`/"request" no contexto) + helper `_load_state_or_400` (ValueError de `wizard.load_state` -> HTTPException 400 com a mesma mensagem). Usa `wizard.new_state/sync_step/validate_step/apply_competitor_intent`, `period_or_422`, `overview_redirect_url`, `templates`/`is_htmx`. `collect_analysis` importado no nível do módulo. Código morto (`step`) mantido para a T10.
**Testes**: nenhum novo; suíte completa: 121 passed, 1 skipped.
**Verificação**: ruff check/format OK; (path, métodos) idênticos aos do legacy; plugin pytest temporário no scratchpad (`swap_t7.py`) trocou as rotas do wizard do legacy pelas novas e rodou test_functional_mvp + test_web_characterization : 31 passed (rotas novas no lugar das antigas, mesma ordem).
**Técnica**: extração de módulo por cópia fiel + delegação à lógica pura já extraída; tradução de exceção na borda HTTP.

### T8 — Rotas de workspace (routes/workspace.py)
**Arquivos**: criado `app/web/routes/workspace.py` (nenhum outro editado; router ainda não incluído).
**Como era**: `analysis_page`, `timeline_fragment`, `collect_form` em `legacy_routes.py` (~linhas 318-350, 441-465, 468-508) usando `_parse_timeline_filters`, `_parse_range`, `_load_events`, `_timeline_context`, `_overview_data`, `_context` (chave "request").
**Como ficou**: mesmas 3 rotas em `APIRouter(tags=["Web UI"])`; usa `filters_or_422`/`period_or_422`, `workspace.timeline_context/overview_data/overview_redirect_url`, `analysis_events` inline, `templates`/`is_htmx`; `collect_analysis` importado no topo; `latest_received` via `latest_events=all_events`. Chaves de contexto, HX-Push-Url e redirect idênticos; `CollectionRequest` mantido.
**Testes**: nenhum novo; reaproveitados test_functional_mvp e test_web_characterization.
**Verificação**: (path, métodos) do novo router ⊂ legacy; app temporário (plugin pytest no scratchpad substituindo as 3 rotas do legacy, mantendo a ordem) -> 31 testes de functional_mvp + characterization passam; suíte completa 121 passed/1 skipped; ruff check e format OK.
**Técnica**: extract module + replace inline helpers by pure functions; paridade provada por substituição de rotas em app temporário.

### T9 — Integração dos sub-routers (sessão principal)
- **Arquivos:** `app/web/router.py` (inclui pages, wizard, workspace, setup, event_analysis); `legacy_routes.py` removido; `tests/test_functional_mvp.py` (monkeypatch → `app.web.routes.wizard.collect_analysis`).
- **Como era:** um único `routes.py` de 620 linhas com 27 funções e 16 decoradores.
- **Como ficou:** 5 módulos de rotas HTTP + 3 módulos de lógica pura; `wizard` é incluído antes de `workspace` para `/ui/analyses/new` não cair em `/ui/analyses/{id}`.
- **Testes:** snapshot de rotas da T0 passou sem alteração (mesmas 16 rotas nesta etapa).
- **Verificação:** pytest 121 passed, 1 skipped; ruff check/format limpos.
- **Técnica:** Extract Module, SRP.

### T10 — Remoção de código morto (sessão principal)
- **Arquivos:** `routes/setup.py` (PUT), `routes/workspace.py` (`?tab=`, `CollectionRequest`), `routes/wizard.py` (`?step=`); testes `test_functional_mvp.py` e `test_web_characterization.py`.
- **Como era:** `PUT /ui/companies/{id}` usado só por 1 teste (o template usa POST); redirects `?tab=profile|monitoring` sem nenhuma referência; `?step=` sem referência; `CollectionRequest` reconstruído na rota apesar de `parse_period` já validar `start <= end`.
- **Como ficou:** removidos os 4 itens; a rota collect passa `start`/`end` direto ao serviço (schema mantido na REST API).
- **Testes:** teste do PUT passou a usar POST; snapshot de rotas perde a linha PUT; novos: PUT → 405, `?tab=` ignorado (200, igual à visão geral), `?step=` ignorado. 
- **Verificação:** pytest 121 passed, 1 skipped; ruff limpo.
- **Técnica:** remoção de código morto (só teste ou nenhuma referência).

### T11 — Revisão independente da refatoração da Web Layer
- **Arquivos:** revisados `backend/app/web/{router,templating,errors,periods,wizard,workspace}.py`, `backend/app/web/routes/*.py`, `main.py`, testes `test_web_*` e docs (`.ai/*`, `backend/README.md`). Nenhum arquivo do repo foi editado.
- **Como era:** `routes.py` com 620 linhas (rotas, wizard, períodos, filtros e view-data misturados).
- **Como ficou:** comparação função a função com `git show HEAD:backend/app/web/routes.py`. Status, mensagens, redirects, ordem de validação, chaves de contexto, HX-Push-Url e rollback/log da coleta inicial estão preservados. Só mudam as remoções deliberadas (PUT, `?tab=`, `?step=`, `CollectionRequest` na Web).
- **Contexto de template:** a chave `request` saiu dos contextos. O único uso em template é `request.query_params` em `workspace/setup.html:7`, e o Starlette injeta `request` via `TemplateResponse(request=...)`. `url_for` também é coberto.
- **Testes:** 121 passed, 1 skipped. Sem cobertura direta: HX-Push-Url exato do fragmento com filtros múltiplos, ramo 404 de `update_company_form` (empresa não vinculada) e `?step=abc`, que antes dava 422.
- **Verificação:** `pytest -q`, `ruff check` e `ruff format --check` passam. Templates e services sem alteração (`git status`).
- **Técnica:** leitura diff a diff, grep de dependências (`request`, `hx-put`, `tab=`, `routes.py`) e execução da suíte.
- **Achados menores:** `errors.py` é um adaptador fino, aceitável. `_load_state_or_400` fica em `routes/wizard.py`, enquanto os outros adaptadores 422 ficam em `errors.py`. As rotas `add_competitor_form` e `update_company_form` mantêm `request` sem uso, como no original.

### Achados menores da revisão (não corrigidos)
- `_load_state_or_400` (`routes/wizard.py`) repete o padrão de `errors.py`, mas ficou local.
- `analysis_events(...)` é chamado em 2 pontos de `routes/workspace.py` (duplicação pequena).
- Riscos sem teste direto: 404 de `update_company_form` para empresa não vinculada; `HX-Push-Url` da timeline com vários filtros.

---

## Frente B — Core / Services / Segurança (Felipe)

> Espaço reservado. Usar o mesmo formato por tarefa (Arquivos, Como era, Como ficou, Testes, Verificação, Técnica).

### Resumo
_(a preencher)_

### Métricas
| Métrica | Antes | Depois |
|---|---:|---:|
| Services importando `HTTPException` | 5 | _ |
| Teste PostgreSQL compatível com o wizard | não | _ |
| Suíte | _ | _ |

### Tarefas
- _Fase 0 — baseline e teste PostgreSQL_
- _7.1 Desacoplar services de FastAPI_
- _7.2 Simplificar `collect_analysis()`_
- _7.3 DRY / identidade por website_
- _Auditoria de segurança_

### Pontos de partida (levantados na Frente A, ainda não verificados pela Frente B)
- `services/collection.py`: o default `providers=None` (fallback para mocks) não é usado por nenhum chamador; `HTTPException` é importado dentro da função.
- `services/event_analysis.py`: `__all__` re-exporta `AnalysisProviderError`, e os testes importam de `app.providers.analysis`.
- `providers/__init__.py`: `__all__` re-exporta os providers; os mocks só têm uso real em `collection.py` (ver item 1) e em testes.
- `app/web/wizard.py` compara websites com `rstrip("/")` + `lower()/casefold()`, regra divergente de `normalize_website` em `services/companies.py` (P3).
- Ao trocar `HTTPException` por erros de domínio, a tradução na Web fica em poucos pontos: `routes/wizard.py` (`create_analysis`), `routes/setup.py` e `routes/workspace.py`.

---

## Integração e validação final

> Espaço reservado: paridade com o baseline, suíte completa, `alembic check`, `npm run build`, teste PostgreSQL opt-in, auditoria de dependências, smoke test da UI e revisão independente da branch integrada.
