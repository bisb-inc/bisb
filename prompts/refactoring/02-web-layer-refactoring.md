# Prompt 02 — Refatoração da Web Layer (Frente A, Luca)

Prompts do usuário usados nesta frente, transcritos como foram enviados. Não foram editados depois da execução.

## Prompt 1 — pedido inicial

> Preciso que refatore algumas partes do nosso MVP. Conforme o plano em MD anexo, preciso que foque primeiramente em algumas partes específicas: redução das responsabilidades concentradas em ./backend/app/web/routes.py. Ao mesmo tempo, verifique a possibilidade da estraturação em helpers, wizards e workspaces. O que pode ser lixo e não estar mais sendo utilizado com base nas referências, se estiver sendo usado apenas em testes e em mais nenhuma outra camada ou serviço, pode remover. Inicialmente faça esse levantamento e crie um outro arquivo .MD com o planejamento e estrutura alvo.

## Prompt 2 — testes e paralelismo

> Anexe no plano também a alteração dos testes relacionados as alterações. Separa tudo isso em sub-tarefas e quando possível, utilize agentes em paralelo para executar as tarefas.

## Prompt 3 — registro de alterações

> Ao mesmo tempo que faz alterações, peça para os agentes que façam um curto registro do que alteraram, como era e como ficou. Quando tudo estiver finalizado, coloque tudo em um novo MD e deixe espaço para que o Felipe faça o mesmo

## Limites dados aos agentes
- Sem novas features; preservar URLs, status, mensagens, templates e chaves de contexto.
- Não tocar em `app/services/`, `models.py`, `migrations/`, contratos REST (Frente B).
- Cada agente edita só os arquivos da sua sub-tarefa e valida com `pytest -q`, `ruff check .`, `ruff format --check .`.
- Registro curto por tarefa: Arquivos, Como era, Como ficou, Testes, Verificação, Técnica.

## Sub-tarefas
Ver [registro-de-alteracoes.md](../../docs/refactoring/registro-de-alteracoes.md): T0 testes de caracterização, T1 `periods.py`, T2 `wizard.py`, T3 `workspace.py`, T4 docs, T5 `templating.py`/`router.py`, T6 a T8 `routes/*`, T9 integração, T10 remoção de código morto, T11 revisão independente.

## Técnica declarada
SRP, Extract Module, Extract Method, KISS, DRY apenas onde havia repetição comprovada.
