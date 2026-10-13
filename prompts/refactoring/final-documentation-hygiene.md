# Prompt — Higienização final da documentação de evidências

Prompt do usuário enviado ao Claude Code, transcrito literalmente do texto colado na sessão (2026-10-13). Trechos omitidos estão marcados entre colchetes; o restante não foi editado. Aplicado após a revisão técnica da branch `refactor/integration`.

````text
Estamos na branch `refactor/integration`.

A revisão técnica final concluiu:

**APROVADO COM RESSALVAS.**
Não há correção obrigatória de código.
As pendências que bloqueiam a entrega são documentais.

Faça somente a higienização final da documentação e dos prompts reais utilizados.

## Restrições

NÃO altere código da aplicação.

NÃO altere comportamento.

NÃO refatore mais nada.

NÃO faça merge, rebase, squash ou amend.

NÃO faça push ao final.

NÃO versione `docs/bisb_refactoring_plan.md`.

Esse arquivo contém planejamento operacional interno e deve permanecer não rastreado.

Não invente prompts retroativamente.

Versione apenas prompts que foram efetivamente usados.

## 1. Limpar efeitos do build

Restaure somente os dois arquivos marcados como modificados por conversão LF/CRLF:

- `backend/app/static/css/app.css`
- `backend/app/static/js/HTMX-LICENSE.txt`

O conteúdo é idêntico ao versionado.

Depois confirme que não existe alteração funcional nesses arquivos.

## 2. Corrigir `docs/refactoring/02-security-audit.md`

Remova a conclusão incorreta de que a ausência de autenticação implica ausência de risco de CSRF.

Registre de forma objetiva:

- não existe token CSRF;
- não existe validação de `Origin`/`Referer`;
- não existe validação explícita de Host/`TrustedHostMiddleware`;
- o Docker Compose publica a aplicação em `127.0.0.1`, reduzindo a superfície de exposição;
- isso não elimina requisições cross-site originadas pelo navegador local;
- existe risco de DNS rebinding na ausência de validação de Host;
- o Dockerfile faz bind em `0.0.0.0`, portanto uma publicação do container em todas as interfaces ampliaria a exposição;
- a aplicação atual não deve ser tratada como pronta para exposição pública.

Não implemente mitigação nesta entrega. Apenas documente a dívida, pois ela já existia em `v1.0-mvp`.

Preserve o achado e a correção de `safe_href`.

## 3. Corrigir `docs/refactoring/registro-de-alteracoes.md`

Remova placeholders da seção Core / Services / Segurança.

Não duplique integralmente os documentos existentes.

Em vez disso, faça a seção resumir tecnicamente a frente e apontar para:

- `00-baseline.md`
- `01-core-services.md`
- `02-security-audit.md`

Inclua as principais métricas finais:

- Services importando FastAPI: 5 → 0;
- `HTTPException` nos Services: 15 → 0;
- complexidade de `collect_analysis`: 11 → 3;
- busca de empresa por website em `companies.py`: 2 → 1.

Corrija também:

- afirmação de que `CollectionRequest` foi mantido na Web, pois ele foi removido da rota de coleta;
- afirmação de que o 404 de `update_company_form` não possui teste;
- referências a scripts de scratchpad que não estão no repositório;
- golden master de 117 requisições: classifique como **evidência auxiliar não reproduzível a partir do repositório**, pois o executor não foi versionado;
- afirmação de que auditoria de dependências está pendente, pois `02-security-audit.md` registra que ela foi executada.

Use tom técnico e acadêmico.

[Trecho omitido: orientação editorial interna.]

## 4. Corrigir `docs/refactoring/web-layer-plan.md`

O documento pode continuar existindo como registro técnico da frente Web, mas remova conteúdo operacional irrelevante à entrega final.

Remova ou corrija:

- caminhos locais como `~/Downloads/...`;
- referências a `<scratchpad>`;
- nomes de scripts temporários não versionados;
- “Destino após aprovação” ou outras instruções operacionais obsoletas;
- tabela de testes que ainda descreve a remoção de PUT, `?tab=` e `?step=`.

O estado final deve registrar a decisão de preservar compatibilidade:

- `PUT /ui/companies/{id}` permanece;
- `?tab=profile` permanece;
- `?tab=monitoring` permanece;
- `/ui/analyses/new?step=` permanece;
- `?step=abc` continua gerando 422.

Corrija ainda:

- `timeline_context` para refletir o uso atual de `latest_events`;
- “quatro módulos de lógica pura” para a contagem real;
- afirmação de que nenhum chamador usa `providers=None`, pois os testes de caracterização usam esse comportamento.

Não reescreva o documento inteiro. Preserve o histórico técnico útil e retire apenas o que estiver desatualizado ou operacional demais.

## 5. Ajustar `docs/refactoring/00-baseline.md`

Esse documento representa historicamente a blindagem feita na branch `refactoring`.

Não substitua esse fato por `refactor/integration`.

Em vez disso, deixe explícito algo como:

- branch do baseline: `refactoring`;
- versão original: `v1.0-mvp`;
- resultado final integrado: `refactor/integration`.

Remova ou atualize referências a arquivos ainda inexistentes quando necessário.

Não cite `docs/bisb_refactoring_plan.md`.

## 6. Ajustar `docs/refactoring/01-core-services.md`

Preserve as métricas históricas da frente Core.

A métrica:

`app/web/routes.py: 620 → 637`

pode permanecer como estado intermediário da frente Core, mas acrescente uma nota deixando claro que, após a integração com a Web Layer, `routes.py` foi removido e o maior módulo Web final possui 149 linhas.

Não altere retroativamente os resultados dos testes executados naquela etapa.

## 7. Prompts reais utilizados

Atualmente existe:

`prompts/refactoring/03-web-layer-refactoring.md`

Preserve esse arquivo exatamente como registro do prompt usado pela frente Web.

Adicione somente prompts que realmente foram utilizados e cujo conteúdo possa ser recuperado fielmente.

Não crie arquivos apenas para satisfazer uma numeração previamente planejada.

A estrutura final não precisa ser sequencial.

Por exemplo, se os prompts reais disponíveis forem:

- execução do refactoring Core/Services;
- Web Layer;
- revisão independente;
- integração final;
- revisão final;

use nomes descritivos para esses prompts.

Se algum prompt não puder ser recuperado fielmente, NÃO o invente. Registre essa limitação no resumo final.

[Trecho omitido: orientação editorial interna.]

## 8. Não criar ainda `docs/modernization-report.md`

O relatório final será produzido depois desta higienização.

Neste momento apenas deixe os documentos de evidência consistentes para que o relatório possa ser gerado a partir deles.

## 9. Validação

Depois das alterações execute:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic check
npm run build
```

Se `TEST_POSTGRES_URL` estiver disponível, execute também a suíte completa com PostgreSQL.

Se não estiver disponível, diga explicitamente que não executou essa validação.

Depois do build, caso os dois assets apareçam novamente como modificados somente por LF/CRLF e `git diff` esteja vazio, restaure-os novamente.

## 10. Commit

Crie no máximo um commit documental final, por exemplo:

`docs(refactor): finalize modernization evidence`

Esse commit pode conter:

- documentação corrigida;
- prompts reais recuperados;
- nenhuma alteração funcional.

Não inclua `docs/bisb_refactoring_plan.md`.

## Saída

Ao final reporte:

1. arquivos alterados;
2. inconsistências corrigidas;
3. prompts efetivamente versionados;
4. prompts que não puderam ser recuperados fielmente;
5. testes executados e resultados;
6. resultado PostgreSQL ou confirmação de que não foi executado;
7. `git status`;
8. SHA do commit criado;
9. confirmação de que nenhum código funcional foi alterado;
10. confirmação de que `docs/bisb_refactoring_plan.md` continua fora do Git.

Não faça push.
````
