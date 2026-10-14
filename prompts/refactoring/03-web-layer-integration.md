# Prompt 03 — Integração da Web Layer com a frente Core/Services

Prompt do usuário enviado ao Claude Code, transcrito literalmente do texto colado na sessão (2026-10-13). Trechos omitidos estão marcados entre colchetes; o restante não foi editado. Resultado registrado na seção "Integração e validação final" de [registro-de-alteracoes.md](../../docs/refactoring/registro-de-alteracoes.md#integração-e-validação-final).

````text
Vamos integrar a implementação real da Web Layer com a frente Core/Services já validada.

Branches disponíveis:

- `refactor/felipe-core` — baseline + Core/Services + correção de segurança;
- `review/luca-web` — Web Layer implementada independentemente a partir de `v1.0-mvp`;
[Trecho omitido: instruções sobre uma branch local auxiliar, que não integra a entrega.]

## Objetivo

Criar uma branch temporária:

`refactor/integration`

a partir de:

`refactor/felipe-core`

e integrar `review/luca-web`, preservando a autoria e os commits do Luca.

Não fazer squash.

Não reescrever os commits do Luca.

[Trecho omitido: instruções sobre uma branch local auxiliar, que não integra a entrega.]

A implementação arquitetural oficial da Web deve ser a desenvolvida em `review/luca-web`, com apenas os ajustes necessários para:

1. preservar os contratos da Entrega 1;
2. integrar a frente Core;
3. preservar a correção de segurança.

## Contratos que devem ser restaurados

A branch do Luca removeu deliberadamente alguns comportamentos existentes em `v1.0-mvp`.

Para esta entrega de refactoring queremos preservar comportamento externo.

Restaure:

### `PUT /ui/companies/{company_id}`

A rota original aceitava POST e PUT.

O resultado integrado deve voltar a aceitar ambos com a mesma função e comportamento.

### `?tab=profile`

Em:

`GET /ui/analyses/{analysis_id}?tab=profile`

preservar o comportamento original:

- resposta 303;
- redirect para `/ui/analyses/{analysis_id}/setup`.

### `?tab=monitoring`

Preservar:

- quando `view` não foi explicitamente alterada, `tab=monitoring` seleciona a Timeline;
- os demais comportamentos originais continuam iguais.

### `/ui/analyses/new?step=`

A rota original possuía:

`step: int = 1`

e limitava o valor ao intervalo 1..5.

Preserve esse contrato.

Isso também deve preservar o 422 automático do FastAPI para valores não inteiros.

Não altere os testes de baseline para aceitar a remoção desses comportamentos.

Em vez disso, ajuste os testes adicionados pela frente Web para refletirem novamente o contrato original.

Ao final devem existir:

- 16 combinações caminho/método Web;
- 13 caminhos Web distintos.

## Integração com ApplicationError

A frente Core removeu `HTTPException` de `app/services/`.

Preserve essa arquitetura.

Em particular, `create_analysis_form` na Web Layer do Luca ainda captura `HTTPException` vindo de `create_analysis`.

Atualize somente esse comportamento necessário para capturar:

`ApplicationError`

e apresentar `exc.message` na etapa de revisão, mantendo o comportamento existente.

Não reintroduza FastAPI nos Services.

Preserve também o registro global de handlers existente em:

`app/http_errors.py`

e sua configuração em `create_app()`.

## Preservação da correção de XSS

A frente Core corrigiu uma vulnerabilidade de links com esquemas executáveis através de `safe_href`.

Essa correção é obrigatória e não pode ser perdida durante a substituição de `app/web/routes.py`.

Na arquitetura do Luca, mova/adapte essa responsabilidade preferencialmente para:

`app/web/templating.py`

de forma que esse módulo concentre:

- `Jinja2Templates`;
- registro do filtro `safe_href`;
- `is_htmx`.

Preserve a política já testada:

- `http` permitido;
- `https` permitido;
- ausência de esquema preservada;
- demais esquemas neutralizados para `#`;
- tratamento de espaços/caracteres de controle;
- falhas de parsing neutralizadas.

Preserve os templates modificados e `tests/test_security_links.py`.

Não enfraqueça nem remova esses testes.

## Arquitetura do Luca

Preserve, salvo necessidade técnica concreta:

- `app/web/router.py`;
- `app/web/templating.py`;
- `app/web/errors.py`;
- `app/web/periods.py`;
- `app/web/wizard.py`;
- `app/web/workspace.py`;
- `app/web/routes/pages.py`;
- `app/web/routes/wizard.py`;
- `app/web/routes/workspace.py`;
- `app/web/routes/setup.py`;
- `app/web/routes/event_analysis.py`.

[Trecho omitido: instruções sobre uma branch local auxiliar, que não integra a entrega.]

O objetivo é integrar o trabalho do Luca, não substituí-lo.

## Testes

Mantenha:

- testes de caracterização comuns;
- testes Core;
- testes de segurança;
- testes Web criados pelo Luca.

Duplicação moderada de cobertura é aceitável nesta etapa. Não remova testes apenas para reduzir a contagem.

Depois da resolução execute:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic check
npm run build
```

Execute também a suíte com PostgreSQL opt-in.

Confirme explicitamente:

- OpenAPI original × integrado;
- 16 combinações caminho/método Web;
- 13 caminhos Web distintos;
- 13 combinações caminho/método REST;
- comportamento de `PUT`;
- `?tab=profile`;
- `?tab=monitoring`;
- `?step=3`;
- `?step=abc`;
- fluxo do wizard;
- HTMX;
- correção `safe_href`;
- tratamento de `ApplicationError`.

## Documentação

Não mantenha no relatório final afirmações de que PUT, `?tab=` ou `?step=` eram código morto removido.

Eles devem passar a ser descritos como contratos de compatibilidade preservados por decisão de paridade.

Corrija também qualquer uso de:

“15 URLs Web”

para a métrica reproduzível:

- 16 combinações caminho/método;
- 13 caminhos Web distintos.

Não altere retroativamente o arquivo de prompts utilizados.

## Final

Ao terminar, não faça merge em `refactoring` ainda.

Reporte:

1. conflitos encontrados e como foram resolvidos;
2. commits da integração;
3. testes e resultados;
4. inventário final das rotas;
5. confirmação da correção de segurança;
6. confirmação do tratamento de `ApplicationError`;
7. qualquer mudança de comportamento restante em relação a `v1.0-mvp`;
8. arquivos/documentos que ainda precisariam ser atualizados antes da entrega.

Não faça push nem merge adicional sem instrução.
````
