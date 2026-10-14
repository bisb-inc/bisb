# Prompt 01 — Execução do refactoring Core/Services

Prompt do usuário enviado ao Claude Code, transcrito literalmente do texto colado na sessão (2026-10-10). Trechos omitidos estão marcados entre colchetes; o restante não foi editado. Execução registrada em [00-baseline.md](../../docs/refactoring/00-baseline.md), [01-core-services.md](../../docs/refactoring/01-core-services.md) e [02-security-audit.md](../../docs/refactoring/02-security-audit.md).

````text
Vamos executar o plano de refactoring da Entrega 2 do Bisb.

Leia primeiro:

- o plano de refactoring existente no repositório;
- `.ai/`;
- `docs/arquitetura.md`;
- os testes atuais;
- o código atual.

O objetivo é **refatoração e modernização**, não adicionar funcionalidades.

## Estratégia de Git obrigatória

Quero manter a minha parte e a parte atribuída ao Luca completamente separáveis.

NÃO faça push.

NÃO faça squash.

NÃO faça amend de commits existentes.

NÃO reescreva histórico.

Antes de qualquer alteração, confirme que o working tree está limpo.

### Base comum

Use a branch `refactoring` como base comum.

A primeira intervenção deve ser exclusivamente a blindagem pré-refactoring:

- atualizar os testes de caracterização;
- principalmente o teste PostgreSQL opt-in que ainda representa o fluxo antigo;
- registrar o baseline funcional atual.

Esse trabalho deve ficar em commit próprio, conceitualmente:

`test(refactor): establish characterization baseline`

Não faça refactoring arquitetural nesse commit.

Execute a suíte relevante e registre os resultados.

---

## Fase 1 — minha parte

Crie a partir desse baseline:

`refactor/felipe-core`

Nesta branch implemente SOMENTE a frente Core/Services prevista no plano.

Prioridades:

1. auditoria técnica dos itens previstos;
2. confirmar os smells antes de alterá-los;
3. desacoplar `app/services/` de FastAPI/`HTTPException`;
4. introduzir erros semânticos simples de aplicação e mapping na fronteira HTTP;
5. simplificar `collect_analysis()` por extração de responsabilidades, preservando rigorosamente sua semântica transacional;
6. investigar e, somente se confirmado, eliminar duplicação na normalização/identidade de website;
7. executar auditoria de segurança prevista no plano;
8. preservar comportamento externo.

Não altere intencionalmente a arquitetura da Web Layer nesta branch além do mínimo inevitável para manter compatibilidade com a nova política de erros.

Não modularize `app/web/routes.py` nesta branch.

Faça commits atômicos por intervenção.

Exemplos conceituais:

- `refactor(core): introduce application-level errors`
- `refactor(core): decouple services from FastAPI`
- `refactor(collection): simplify collection orchestration`
- `refactor(domain): centralize company website identity`

Só crie um commit quando a respectiva intervenção estiver validada.

Após cada intervenção relevante rode os testes apropriados.

Ao terminar, `refactor/felipe-core` deve representar **somente a minha parte da divisão de trabalho**.

---

[Trecho omitido: instruções sobre uma branch local auxiliar, que não integra a entrega.]

---

## Paridade funcional

Em nenhuma das duas frentes adicione feature.

Preserve:

- TARGET/COMPETITOR;
- wizard;
- criação da Analysis;
- coleta;
- GNews;
- X mock;
- falha parcial;
- deduplicação;
- Timeline;
- filtros;
- Setup;
- EventAnalysis;
- Gemini;
- mocks;
- URLs existentes;
- REST API existente.

O comportamento externo antes e depois deve permanecer equivalente.

---

## Validação

Ao longo do trabalho e ao final, execute quando aplicável:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic check
npm run build
```

Execute também o teste PostgreSQL opt-in se o ambiente estiver configurado para isso.

Não afirme que um teste externo foi validado caso não tenha sido executado.

---

## Segurança

Faça a auditoria prevista no plano sem criar mudanças artificiais.

Verifique pelo menos:

- secrets;
- `.env`;
- `SecretStr`;
- logs;
- URLs de providers;
- mensagens externas;
- SQL;
- templates;
- dependências;
- Docker;
- tratamento de exceções.

Se não houver vulnerabilidade relevante, documente isso.

Não invente problemas para gerar alterações.

---

## Documentação e evidências

Durante o trabalho, preserve evidências para o futuro `modernization-report.md`.

Para cada intervenção registre:

- problema original;
- evidência;
- técnica aplicada;
- arquivos afetados;
- comportamento preservado;
- testes executados;
- resultado;
- métricas reproduzíveis de antes/depois quando existirem.

Não invente percentuais subjetivos de melhoria.

Ainda não transforme o relatório em marketing.

---

## Restrições importantes

Não implementar:

- SSO real;
- autenticação;
- X real;
- JEV;
- workers;
- filas;
- scheduler;
- features do roadmap;
- microsserviços;
- nova UI;
- novo framework;
- atualização arbitrária de dependências;
- Repository Pattern genérico;
- CQRS;
- Clean Architecture completa;
- abstrações sem necessidade concreta.

KISS e YAGNI também fazem parte da avaliação.

---

## Saída final

Quando concluir, apresente:

1. branch e commit de baseline;
2. commits existentes em `refactor/felipe-core`;
[Trecho omitido: instruções sobre uma branch local auxiliar, que não integra a entrega.]
4. diagnóstico confirmado e itens rejeitados;
5. testes executados e resultados;
6. métricas antes/depois disponíveis;
7. achados da auditoria de segurança;
8. eventuais riscos ou dívidas que permaneceram;
9. confirmação explícita de que nenhuma branch foi enviada para o remoto.

Não faça push.
````
