# Prompt 03 — Refatoração da Web Layer (Frente A, Luca)

Registro do pedido real e da delegação aos agentes. Não foi editado depois da execução.

## Pedido original (resumo fiel)
Refatorar o MVP conforme `bisb_refactoring_plan.md`, começando por reduzir as responsabilidades concentradas em `backend/app/web/routes.py`; avaliar estruturação em helpers, wizards e workspaces; remover o que não for usado por nenhuma camada (ou só por testes); fazer primeiro o levantamento e um MD com planejamento e estrutura alvo (`docs/refactoring/web-layer-plan.md`). Depois: incluir no plano as mudanças de testes, dividir em sub-tarefas com agentes em paralelo, e pedir a cada agente um registro curto (como era / como ficou).

## Limites dados aos agentes
- Sem novas features; preservar URLs, status, mensagens, templates e chaves de contexto.
- Não tocar em `app/services/`, `models.py`, `migrations/`, contratos REST (Frente B).
- Cada agente edita só os arquivos da sua sub-tarefa e valida com `pytest -q`, `ruff check .`, `ruff format --check .`.
- Registro curto por tarefa: Arquivos, Como era, Como ficou, Testes, Verificação, Técnica.

## Sub-tarefas (ver `docs/refactoring/registro-de-alteracoes.md`)
T0 testes de caracterização · T1 `periods.py` · T2 `wizard.py` · T3 `workspace.py` · T4 docs · T5 `templating.py`/`router.py` (sessão principal) · T6–T8 `routes/*` · T9 integração (sessão principal) · T10 remoção de código morto (sessão principal) · T11 revisão independente (somente leitura).

## Técnica declarada
SRP, Extract Module, Extract Method, KISS, DRY apenas onde havia repetição comprovada.
