# Frente A — Refatoração da Web Layer (Luca): levantamento e estrutura alvo

> Base: plano de refactoring da Entrega 2, seção 6 (Web Layer). Este documento registra o levantamento feito antes da alteração de código e as decisões tomadas depois, na integração.

## 1. Contexto

A Entrega 2 exige modernizar o Bisb sem novas features, sem alterar URLs, templates, contratos REST ou regras de negócio. Minha frente é a **Web Layer**. O alvo é `backend/app/web/routes.py`, que concentra wizard, workspace, períodos, filtros, view-data e ações HTMX. Este documento mapeia as responsabilidades, levanta itens sem uso e propõe a estrutura final.

**Fora do meu escopo** (plano §6.7): `services/*`, `models.py`, `migrations/`, contratos REST. Dívidas encontradas ali ficam na seção 7, como observação para a Frente B.

## 2. Diagnóstico de `app/web/routes.py` (antes)

Métricas medidas: **620 linhas, 27 funções, 16 decoradores de rota**: 16 combinações caminho/método em 13 caminhos Web distintos (`/ui/analyses` e `/ui/analyses/{id}/setup` têm GET e POST; `/ui/companies/{id}` tem POST e PUT).

| # | Responsabilidade misturada | Funções / linhas | Observação |
|---|---|---|---|
| 1 | Períodos (cálculo e parsing) | `_month_before`, `_range_for_preset`, `_parse_range` (40–75) | Puro, exceto por `HTTPException(422)` no parse |
| 2 | Filtros da timeline | `_parse_timeline_filters`, `_load_events` (78–99) | `_load_events` só repassa argumentos a `analysis_events` |
| 3 | View-data do workspace | `_timeline_context`, `_overview_data` (102–134) | `_overview_data` é regra de apresentação (destaques) sem I/O |
| 4 | Estado e validação do wizard | `_wizard_state`, `_sync_step_state`, `_validate_wizard_step` (137–215) | Puro; `_validate_wizard_step` captura `HTTPException` de `_parse_range` |
| 5 | Máquina de passos do wizard | `wizard_step` (255–303) | 50 linhas: sincroniza estado, trata `intent` e navega |
| 6 | Criação via wizard | `create_analysis_form` (306–358) | Valida, cria, coleta e monta redirect |
| 7 | Rotas de workspace | `analysis_page`, `timeline_fragment`, `collect_form` (361–581) | `collect_form` repete montagem de contexto e redirect |
| 8 | Rotas de Setup | setup GET/POST, competitors add/remove, `update_company_form` (407–491) | CRUD simples com redirect |
| 9 | Análise de evento | `analyze_event_form` (584–620) | Mapeia exceções do provider para mensagem de UI |
| 10 | Páginas simples | `home`, `login_page`, `analyses_page` | |

### Acoplamentos observados
- Testes fazem `monkeypatch.setattr(app.web.routes, "collect_analysis", ...)` (`test_functional_mvp.py:257-262`). Esse teste precisa mudar de alvo quando a rota de criação sair do módulo.
- `main.py` importa `app.web.routes.router`.
- Helpers puros (períodos, wizard) estão presos a `HTTPException`, então não são testáveis sem HTTP.
- O mapeamento de `HTTPException` dos services é feito inline em `create_analysis_form`. A Frente B vai trocá-lo por erros de domínio, então esse ponto deve ficar isolado em um único módulo para facilitar o merge.

### Duplicações comprovadas (DRY aplicável)
1. `request.headers.get("HX-Request") == "true"` aparece 5 vezes (linhas 293, 299, 551, 604, mais o teste). Vira `is_htmx(request)`.
2. A URL de redirect para a visão geral (`?view=overview&collection_status=…&persisted=…&from_date=…&to_date=…`) é montada 2 vezes (352 e 552). Vira `overview_redirect_url(...)`.
3. `latest_received` é calculado em `_timeline_context` e recalculado em `collect_form` (571), que o sobrescreve. A função passa a receber o valor.
4. `_context(request, **v)` apenas adiciona `request`, e Starlette 1.7 (`uv.lock`) já injeta `request` em `TemplateResponse(request=…)`. Ele é redundante.
5. O `try/except HTTPException` em `_validate_wizard_step` existe só porque o parse de período lança `HTTPException`.

## 3. Levantamento de itens sem uso

Método: grep de cada símbolo, rota e parâmetro em `app/` (código, templates, JS) e `tests/`. Regra do pedido: referenciado só em testes, ou em nada, pode sair.

### 3.1 Candidatos à remoção (Web Layer, dentro do meu escopo)

> **Decisão na integração:** PUT `/ui/companies/{id}`, `?tab=profile`/`?tab=monitoring` e `?step=` são contratos de compatibilidade da Entrega 1, preservados por decisão de paridade. Dos itens desta tabela, PUT, `?tab=` e `?step=` permanecem; a remoção do uso de `CollectionRequest` na rota collect se mantém, sem efeito externo.

| Item | Evidência | Ação |
|---|---|---|
| `PUT /ui/companies/{company_id}` (decorador em `routes.py:460`) | O template usa `<form method="post">` (`company_profile.html:3`). Não há `hx-put` nem `method="put"` em templates ou `app.js`. **Só `test_functional_mvp.py:115` usa.** | Remover o decorador `.put`. Ajustar o teste para `POST`. |
| Redirects legados `?tab=profile` e `?tab=monitoring` (`routes.py:375-378`) | Nenhuma referência em templates, JS ou testes. Só são citados como compat em `.ai/architecture.md:89` e em `docs/arquitetura.md`. | Remover. Atualizar a frase nos docs. |
| Parâmetro `step` de `GET /ui/analyses/new` (`routes.py:251`) | Nenhum link ou teste usa `?step=`. Renderiza estado vazio em passo arbitrário, o que não tem sentido funcional. | Remover o parâmetro. Sempre passo 1. |
| `CollectionRequest(...)` dentro de `collect_form` (541) | `_parse_range` já garante `start <= end`, então a construção é validação redundante. O schema continua em uso na REST API (`api/routes/analyses.py`). | Remover o uso na Web. O schema permanece. |
| `_load_events`, `_context` | Wrappers sem lógica (ver 2). | Inlinar / eliminar. |
| `company_counts=None, highlights=None` repassados em `analysis_page` | Preenchimento de defaults que o template trata como ausência. | Simplificar. Confirmar com o teste de overview. |

### 3.2 Manter (parecem mortos, mas são usados)
- **Ramos não-HTMX** de `collect_form` e `analyze_event_form`. Os formulários têm `action=` com `hx-post` (`overview.html:29`, `event_analysis.html:20,26`), ou seja, são o fallback sem JS. Hoje quase não têm teste, então entram na rede de segurança (seção 5).
- `GET /` (home), `GET /login` e as ações de Setup (add/remove concorrente, rename). Todas são referenciadas por templates e testes.
- Templates e partials: todos têm um `include`/`extends` ou um `name=` em `routes.py`. **Nenhum template órfão.**
- `app/static/js/app.js` é carregado em `base.html` e tem uso real.

## 4. Estrutura alvo

```text
app/web/
├── router.py            # compõe os sub-routers; exporta `router` (main.py passa a importar daqui)
├── templating.py        # instância única de Jinja2Templates + is_htmx(request)
├── periods.py           # [helpers] presets, _month_before, parse_period — puro, lança ValueError
├── wizard.py            # [wizard] estado, sync por passo, validação por passo, intents do passo 3 — puro
├── workspace.py         # [workspace] parse de filtros da timeline, contexto da timeline,
│                        #   overview_data, overview_redirect_url — puro (sem I/O)
├── routes/
│   ├── pages.py         # home, login, lista de análises
│   ├── wizard.py        # GET /new, POST /new/step/{n}, POST /ui/analyses (criação + coleta inicial)
│   ├── workspace.py     # GET /{id}, GET /{id}/timeline, POST /{id}/collect
│   ├── setup.py         # setup GET/POST, competitors add/remove, POST /ui/companies/{id}
│   └── event_analysis.py# POST /ui/events/{id}/analysis
└── templates/           # inalterado
```

Convenção: `web/<x>.py` contém lógica pura da área e `web/routes/<x>.py` contém só a camada HTTP (parâmetros, chamada a services, resposta). Isso reproduz a referência do plano (§6.2), sem camadas vazias. Três módulos de lógica pura (`periods.py`, `wizard.py`, `workspace.py`) ficam testáveis sem `TestClient`; `templating.py` e `errors.py` dependem de FastAPI.

### Mapa de migração

| Origem (`routes.py`) | Destino | Mudança de comportamento |
|---|---|---|
| `_month_before`, `_range_for_preset`, `_parse_range` | `periods.py` (`parse_period`, lança `ValueError` com a mesma mensagem) | Nenhuma. A rota converte `ValueError` em `HTTPException(422)` com o mesmo `detail`. |
| `_wizard_state`, `_sync_step_state`, `_validate_wizard_step` | `wizard.py` | Nenhuma. A validação do passo 4 passa a capturar `ValueError`. |
| bloco `intent` add/remove de `wizard_step` | `wizard.apply_competitor_intent(state, form, intent) -> erro \| None` | Nenhuma |
| `_render_wizard` | `routes/wizard.py` | Nenhuma |
| `_parse_timeline_filters`, `_timeline_context`, `_overview_data` | `workspace.py` | Nenhuma. `timeline_context` aceita `latest_events` opcional, a lista usada para calcular `latest_received` (a coleta passa todos os eventos da análise). |
| redirect de visão geral (2 cópias) | `workspace.overview_redirect_url` | Nenhuma. A URL gerada é idêntica. |
| `HX-Request` (5 cópias) | `templating.is_htmx` | Nenhuma |
| `create_analysis_form` | `routes/wizard.py` | Nenhuma. A captura do erro de `create_analysis` fica concentrada em **um** ponto; na integração com a Frente B, passou a capturar `ApplicationError`. |

### Invariantes (conferir no final)
- As 16 combinações caminho/método (13 caminhos Web distintos) permanecem, incluindo `PUT /ui/companies/{id}` (decisão na integração, 3.1). `app.routes` é comparado antes e depois.
- Mesmos nomes de template e mesmas chaves de contexto. Os templates não são editados.
- Mesmos status HTTP, mensagens de erro e headers (`HX-Push-Url`).
- Não há nova abstração, classe ou dependência. Só funções movidas, mais 3 helpers de DRY.

## 5. Plano de execução (commits pequenos, suíte verde a cada passo)

0. **Pré-condição:** registrar métricas "antes". A branch `refactor/web-layer` foi criada a partir de `v1.0-mvp`; a integração com o baseline e a Frente B ocorreu em `refactor/integration`.
1. **Testes de caracterização Web** (só se faltarem, plano §6.4). Entram: `collect` sem HX-Request redireciona; `analyze` sem HX redireciona; filtro inválido da timeline → 422; intent `back` do wizard; período `custom` inválido → 422; snapshot da lista de rotas (método + path). Commit isolado.
2. **Extrair `periods.py`** (puro) e ajustar os chamadores.
3. **Extrair `wizard.py`** (puro), incluindo `apply_competitor_intent`.
4. **Extrair `workspace.py`** (puro), com `overview_redirect_url` e `latest_events` opcional em `timeline_context`.
5. **Criar `templating.py`, `routes/*` e `router.py`**. `main.py` passa a importar `app.web.router`. Atualizar o `monkeypatch` do teste para `app.web.routes.wizard`. Remover `routes.py`.
6. **Tratar os itens de 3.1** em um commit separado, para facilitar o revert. Estado final: remoção do uso de `CollectionRequest` na rota collect; PUT, `?tab=` e `?step=` preservados como contratos de compatibilidade (decisão na integração).
7. **Docs:** atualizar `.ai/standards.md` (árvore da seção "Organização da Web UI"), `.ai/architecture.md` (linha "Web Routes" e a nota sobre `?tab=`) e `docs/arquitetura.md`.
8. **Evidências:** métricas depois e o prompt da frente em `prompts/refactoring/03-web-layer-refactoring.md`. A seção do relatório sobre a Web Layer vem no fim.

### Verificação (a cada passo e no final)
```bash
cd backend
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```
Mais: (a) diff do conjunto de rotas (`[(r.path, sorted(r.methods)) for r in app.routes]`) comparado ao snapshot; (b) smoke manual na UI: wizard completo → visão geral → timeline com filtros → coleta via HTMX → Setup → "Analisar com IA" (mock); (c) `npm run build` não é afetado, pois nenhum template muda.

### Métricas a registrar
| Métrica | Antes | Depois |
|---|---:|---|
| Linhas em `web/routes.py` | 620 | arquivo removido; medir cada módulo novo |
| Funções no módulo Web principal | 27 | medir por módulo |
| Rotas (decoradores) | 16 | 16, mesmas combinações caminho/método |
| Maior módulo de rotas | 620 | medir |
| Suíte | registrar | registrar |

## 5.1 Alterações de testes (por mudança)

| Mudança | Teste afetado | Ajuste |
|---|---|---|
| Rede de segurança (passo 1) | novo `tests/test_web_characterization.py` | `collect` e `analyze` sem HX-Request → 303; filtro inválido → 422; período `custom` inválido → 422; wizard `intent=back`; snapshot de `(path, métodos)` das rotas Web |
| Extração de `routes/wizard.py` | `test_functional_mvp.py:257-262` (`monkeypatch` em `routes.collect_analysis`) | Alvo passa a `app.web.routes.wizard.collect_analysis`; asserts inalterados |
| Preservação do `PUT /ui/companies/{id}` | `test_functional_mvp.py:115` (`put`) | Inalterado; snapshot de rotas inclui o PUT; novo teste: PUT responde como o POST (303 para o Setup) |
| Preservação de `?tab=` | testes de caracterização do baseline | Novos testes: `?tab=profile` → 303 para `/ui/analyses/{id}/setup`; `?tab=monitoring` seleciona a Timeline quando `view` não é informado |
| Preservação de `?step=` | testes de caracterização do baseline | Novos testes: `?step=3` renderiza a etapa 3; valores fora de 1..5 são limitados; `?step=abc` → 422 |
| `periods.py` | novo `tests/test_web_periods.py` | presets week/month/quarter, fim de mês (31→30/28), `custom` válido/inválido, mensagens idênticas às atuais |
| `wizard.py` | novo `tests/test_web_wizard.py` | `new_state` padrão, `sync` por passo, cada regra de `validate_step` (nome, alvo, concorrente vazio/repetido/igual ao alvo, período), `apply_competitor_intent` add/remove/índice inválido, JSON inválido |
| `workspace.py` | novo `tests/test_web_workspace.py` | `parse_timeline_filters`, `overview_data` (destaques Gemini vs recência, contagem), `overview_redirect_url` idêntica à URL atual |
| `postgres_integration` | **não tocar** (Frente B/Felipe) | Registrar dependência |

Os testes unitários novos não usam `TestClient` nem banco (módulos puros). Os existentes de `test_functional_mvp.py` e `test_event_analysis.py` continuam como prova de paridade.

## 5.2 Sub-tarefas e paralelismo

Contratos fixados antes de paralelizar (evitam divergência entre sub-tarefas):
- `periods.parse_period(preset, from_value, to_value) -> tuple[date, date]` (lança `ValueError`); `periods.range_for_preset(preset, today=None)`.
- `wizard.new_state() -> dict`, `wizard.sync_step(state, form, step)`, `wizard.validate_step(state, step) -> str | None`, `wizard.apply_competitor_intent(state, form, intent) -> str | None`.
- `workspace.parse_timeline_filters(company, source, from_date, to_date)`, `workspace.timeline_context(analysis, events, latest_events=None, **v)`, `workspace.overview_data(analysis, events)`, `workspace.overview_redirect_url(analysis_id, status, persisted, start, end)`.
- `templating.templates`, `templating.is_htmx(request)`.

| Onda | Sub-tarefa | Arquivos (disjuntos) | Execução |
|---|---|---|---|
| 0 | **T0** Baseline + snapshot de rotas + `test_web_characterization.py`; suíte verde | `tests/` | Sequencial |
| 1 | **T1** `periods.py` + `test_web_periods.py` | `web/periods.py` | **Paralelo** |
| 1 | **T2** `wizard.py` + `test_web_wizard.py` | `web/wizard.py` | **Paralelo** |
| 1 | **T3** `workspace.py` + `test_web_workspace.py` | `web/workspace.py` | **Paralelo** |
| 1 | **T4** Docs (`.ai/standards.md`, `.ai/architecture.md`, `docs/arquitetura.md`) para a estrutura alvo | `.ai/`, `docs/` | **Paralelo** |
| 2 | **T5** `templating.py`, `router.py`; `main.py` aponta para `app.web.router` (as rotas ainda vêm de `routes.py`) | `web/templating.py`, `web/router.py`, `main.py` | Sequencial |
| 3 | **T6** `routes/pages.py`, `routes/setup.py`, `routes/event_analysis.py` | `web/routes/` (3 arquivos) | **Paralelo** |
| 3 | **T7** `routes/wizard.py` + ajuste do `monkeypatch` | `web/routes/wizard.py`, `test_functional_mvp.py:257` | **Paralelo** |
| 3 | **T8** `routes/workspace.py` | `web/routes/workspace.py` | **Paralelo** |
| 4 | **T9** Integração: `router.py` inclui os sub-routers, remove `routes.py`, compara snapshot de rotas | `web/` | Sequencial |
| 5 | **T10** Itens de 3.1 + testes novos/alterados (5.1) | `web/routes/*`, `tests/` | Sequencial, commit separado |
| 6 | **T11** Revisão independente + métricas "depois" + `prompts/refactoring/03-web-layer-refactoring.md` | `prompts/`, relatório | Paralelo entre si |

Regras de cada sub-tarefa: editar só os arquivos da sua linha; rodar `pytest -q`, `ruff check .` e `ruff format --check .`; não tocar em `services/`, `models.py`, `migrations/`; sem features novas. A integração dos sub-routers (T9) e a T10 são sequenciais.

## 5.3 Registro de alterações (feito junto com o código)

Cada sub-tarefa gera um registro curto, consolidado em `docs/refactoring/registro-de-alteracoes.md`. Formato fixo, no máximo ~15 linhas:

```markdown
### T<n> — <título>
- **Arquivos:** <criados / alterados / removidos>
- **Como era:** <2–3 linhas, com função e linhas de origem>
- **Como ficou:** <2–3 linhas, com módulo e função de destino>
- **Testes:** <criados / alterados / removidos e por quê>
- **Verificação:** <comandos rodados e resultado>
- **Técnica:** <SRP / Extract Module / Extract Method / DRY / remoção de redundância>
```

Estrutura de **`docs/refactoring/registro-de-alteracoes.md`**:

```markdown
# Registro de alterações — Refatoração (Entrega 2)
## Frente A — Web Layer (Luca)
   (resumo, métricas antes/depois, um bloco por T<n>, contratos de compatibilidade, decisões)
## Frente B — Core / Services / Segurança (Felipe)
   (resumo técnico, métricas e referências aos documentos da frente Core)
## Integração e validação final
   (resolução de conflitos, paridade, suíte completa)
```

## 6. Riscos e decisões

1. **Remover `PUT /ui/companies/{id}`** muda a superfície da Web UI (§2 do plano veta alterar URLs "sem necessidade"). Como só o teste usa, a recomendação é remover, conforme sua regra. Se preferir ser conservador, deixo o PUT e só o marco como dívida. **Decisão:** mantido como contrato de compatibilidade (3.1).
2. **Remover os redirects `?tab=`.** Eles quebram marcadores antigos, se existirem. Não há referência no código. Recomendo remover. **Decisão:** mantidos como contrato de compatibilidade, assim como `?step=` (3.1).
3. **O `monkeypatch` em `test_functional_mvp.py:262`** passa a mirar `app.web.routes.wizard.collect_analysis`. É um ajuste de teste, não de comportamento.
4. **Conflito com a Frente B:** a remoção de `HTTPException` dos services afeta a captura de erro em `routes/wizard.py` (`create_analysis`). Na integração (`refactor/integration`), a Frente B foi a base e essa captura passou a usar `ApplicationError`; `routes/setup.py` e `routes/workspace.py` não precisaram de ajuste, pois os erros de aplicação são traduzidos pelos handlers globais de `app/http_errors.py`.

## 7. Observações para a Frente B (não executar aqui)

Dívidas e código sem uso fora de `app/web/`, só registradas:
- `services/collection.py:35`: o default `providers=None` cai em `MockNewsProvider/MockXProvider`. As rotas Web e REST sempre passam `providers=`, mas os testes de caracterização da coleta usam o default (`test_collection_defaults_to_mock_news_and_x_providers`, `test_collection_without_companies_or_outcomes_is_failure`); por isso a Frente B o manteve. `HTTPException` é importado dentro da função (linha 29).
- `services/event_analysis.py:65`: o `__all__` re-exporta `AnalysisProviderError`. Os testes já importam de `app.providers.analysis`, então o re-export é redundante.
- `providers/__init__.py`: o `__all__` re-exporta `GNewsProvider`, `MockNewsProvider` e `MockXProvider`. Os mocks só são usados por testes e por `collection.py` (ver o primeiro item).
- `HTTPException` em 5 services (`analyses`, `collection`, `companies`, `event_analysis`, `events`), que é o P1 da Frente B.
- `normalize_website` só é usada em `services/companies.py` (2 pontos). O wizard compara sites com `rstrip("/").lower()` próprio (`_validate_wizard_step`, linhas 198-206), uma regra equivalente e divergente. Como a Web não pode importar a regra de domínio sem mudar o escopo, deixo isso para a Frente B (P3). Quando a regra estiver única, o `wizard.py` passa a chamá-la.
- `tests/test_postgres_integration.py` está desatualizado (P0, Felipe); reescrito no baseline da branch `refactoring`.

## 8. Prompts utilizados

Registrados em [prompts/refactoring/03-web-layer-refactoring.md](../../prompts/refactoring/03-web-layer-refactoring.md).
