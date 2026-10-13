# Refactoring — Baseline pré-refatoração

Registro do comportamento e das métricas da Entrega 1 antes de qualquer alteração estrutural. Serve de referência para a validação de paridade e para o relatório de modernização.

## Referência

| Item | Valor |
| --- | --- |
| Versão original | tag `v1.0-mvp` (commit `0274c56`), igual a `main` no início do refactoring |
| Branch do baseline | `refactoring` (commit `0656238`, `test(refactor): establish characterization baseline`) |
| Resultado final integrado | `refactor/integration` (frente Core/Services e frente Web Layer sobre este baseline; ver [registro-de-alteracoes.md](registro-de-alteracoes.md#integração-e-validação-final)) |
| Python / FastAPI | Python 3.14 (uv 0.10.4), FastAPI 0.141.1 |
| Node / npm | Node 22.20.0, npm 10.9.3 |
| PostgreSQL do teste opt-in | `postgres:16` do Docker Compose do projeto, base dedicada `competitive_monitor_test` |

## Validação do código de referência (antes da blindagem)

Executado a partir de `backend/`, sobre `v1.0-mvp`:

| Comando | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 53 passed, 1 skipped (teste PostgreSQL opt-in sem `TEST_POSTGRES_URL`) |
| `uv run --locked ruff check .` | sem erros |
| `uv run --locked ruff format --check .` | 39 arquivos formatados |
| `uv run --locked alembic check` | `No new upgrade operations detected.` |
| `npm run build` | concluído; assets gerados idênticos aos versionados |
| `pytest tests/test_postgres_integration.py` com `TEST_POSTGRES_URL` | **falha**: `assert 200 == 303` — o teste envia `name`, `target_name` e `target_website`, mas `/ui/analyses` espera `wizard_state` e re-renderiza o wizard |

Em Windows com `core.autocrlf=true`, `npm run build` regrava `app.css` e `HTMX-LICENSE.txt` com LF; o conteúdo é idêntico ao blob versionado e o `git status` acusa alteração apenas de fim de linha.

## Blindagem adicionada

| Arquivo | Escopo |
| --- | --- |
| `tests/test_postgres_integration.py` | Reescrito para o fluxo atual: wizard em cinco etapas, criação com coleta inicial, workspace, Setup, nova coleta com deduplicação pela restrição única real, timeline com filtro HTMX, análise de evento com provider mockado (`SELECT ... FOR UPDATE` no PostgreSQL) e assets. Remove os registros que cria |
| `tests/test_characterization_core.py` | Contrato de erros (status e corpo JSON) dos serviços pela REST API e pela Web UI; conflito de serviço exibido na revisão do wizard; semântica da coleta (ordem empresa → provider, intervalo UTC com fim exclusivo, validação de fonte e timezone, rollback isolado por par, deduplicação no lote e entre coletas, conversão para UTC, status agregado, providers padrão); contrato JSON da coleta; regras de `normalize_website` e reaproveitamento de empresa |
| `tests/test_characterization_web.py` | Inventário da REST API pelo OpenAPI; resposta de cada URL Web; wizard (estado inicial, limites de etapa, rascunho inválido, validações por etapa com e sem HTMX, voltar, presets de período, ações de concorrentes, revalidação na confirmação, redirect com resumo da coleta inicial); workspace (views, parâmetros legados `tab`, filtros inválidos, banner de status); fragmento da timeline e `HX-Push-Url`; coleta com e sem HTMX, incluindo a limitação conhecida das contagens; redirects do Setup; análise de evento pela Web |

Os testes de caracterização usam somente HTTP ou funções públicas dos serviços, para continuarem válidos quando a organização interna mudar.

Comportamentos fixados que merecem decisão explícita antes de qualquer mudança:

- O wizard compara sites apenas por barra final e caixa (`rstrip("/").lower()`), enquanto o serviço usa `normalize_website`. Um concorrente igual ao TARGET escrito sem protocolo passa pela etapa 3 e é rejeitado pelo serviço na confirmação (`test_wizard_site_rule_differs_from_service_identity_rule`).
- A resposta HTMX da coleta conta todos os eventos da análise, não apenas os do período (`test_collect_form_htmx_fragment_reports_pairs_and_counts_all_events`), conforme a limitação registrada no `backend/README.md`.
- Sem `remove_index`, a ação de remover concorrente no wizard remove o último item da lista.

## Validação após a blindagem

| Comando | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 161 passed, 1 skipped |
| `uv run --locked pytest -q` com `TEST_POSTGRES_URL` | 162 passed |
| `uv run --locked ruff check .` | sem erros |
| `uv run --locked ruff format --check .` | 41 arquivos formatados |
| `uv run --locked alembic check` | `No new upgrade operations detected.` |
| `npm run build` | concluído |

Preparação da base dedicada para o teste opt-in:

```powershell
docker exec backend-db-1 psql -U competitive_monitor -d postgres -c "CREATE DATABASE competitive_monitor_test"
$env:TEST_POSTGRES_URL = "postgresql+psycopg://competitive_monitor:local_dev_only@127.0.0.1:5433/competitive_monitor_test"
$env:DATABASE_URL = $env:TEST_POSTGRES_URL
uv run --locked alembic upgrade head
uv run --locked pytest -q tests/test_postgres_integration.py
```

## Métricas de referência

Comandos executados a partir de `backend/`.

| Métrica | Valor | Comando |
| --- | ---: | --- |
| Linhas em `app/web/routes.py` | 620 | `wc -l app/web/routes.py` |
| Funções em `app/web/routes.py` | 27 | `grep -cE '^\s*(async )?def ' app/web/routes.py` |
| Registros de rota em `app/web/routes.py` | 16 | `grep -cE '^@router\.' app/web/routes.py` |
| Módulos de `app/services/` que importam FastAPI | 5 de 5 | `grep -l fastapi app/services/*.py` |
| `raise HTTPException` em `app/services/` | 15 | `grep -c 'raise HTTPException' app/services/*.py` |
| Complexidade ciclomática de `collect_analysis` | 11 | `uv run --locked ruff check app --select C901 --config "lint.mccabe.max-complexity=0"` |
| Maior complexidade ciclomática em `app/` | 11 (`collect_analysis`) | idem |
| Funções de `companies.py` com busca própria por site normalizado | 2 | inspeção de `get_or_create_company` e `update_company` |
| Rotas REST publicadas no OpenAPI | 13 pares caminho/método | `test_rest_contract_inventory_is_preserved` |
| Testes automatizados | 162 coletados | `uv run --locked pytest -q --collect-only` |
