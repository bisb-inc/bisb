# Relatório de Modernização Arquitetural — Bisb — Competitive Monitor

**Atividade:** Refatoração de Arquitetura  
**Projeto:** Bisb — Competitive Monitor  
**Versão original:** `v1.0-mvp` (`0274c56`)  
**Baseline de caracterização:** `refactoring` (`0656238`)  
**Resultado final integrado:** `refactor/integration` (`91fe184`)  
**Data da consolidação:** 13/10/2026

---

## 1. Resumo executivo

A segunda entrega do Bisb teve como objetivo modernizar a arquitetura do MVP entregue anteriormente sem adicionar novas funcionalidades de negócio.

A estratégia adotada foi:

> **Blindagem → Auditoria → Refatoração → Integração → Validação**

Antes de qualquer alteração estrutural, a versão original foi preservada pela tag `v1.0-mvp` e recebeu uma suíte ampliada de testes de caracterização. Essa etapa estabeleceu uma referência reproduzível para os comportamentos que deveriam permanecer estáveis durante o refactoring.

A auditoria do código confirmou quatro pontos principais de dívida técnica:

- dependência direta de FastAPI dentro de toda a camada de Services;
- concentração de responsabilidades em `collect_analysis()`;
- duplicação localizada na identificação de empresas por website;
- concentração da Web Layer em um único módulo de 620 linhas.

As intervenções reduziram o acoplamento ao transporte HTTP, distribuíram responsabilidades da coleta em funções menores, eliminaram duplicação localizada e modularizaram a Web Layer em componentes coesos.

Durante a auditoria de segurança também foi identificada uma vulnerabilidade real de XSS armazenado por esquema de URL. A correção foi implementada e coberta por testes. Essa mudança é tratada separadamente do refactoring comportamental, pois altera deliberadamente o comportamento de entradas inseguras.

O resultado final preserva os contratos e fluxos caracterizados da Entrega 1, com exceção dessa neutralização intencional de URLs inseguras.

A validação final registrou:

- **246 testes aprovados e 1 teste PostgreSQL opt-in pulado** na suíte padrão;
- **247 testes aprovados** com PostgreSQL habilitado;
- Ruff lint e format sem erros;
- Alembic sem novas operações pendentes;
- build dos assets concluído;
- OpenAPI e inventários REST/Web equivalentes à versão original;
- nenhuma correção de código obrigatória apontada pela revisão técnica final.

---

## 2. Contexto e escopo

O Bisb é um sistema de apoio a inteligência competitiva. O módulo implementado nesta entrega é o **Competitive Monitor**.

O fluxo principal permite:

1. criar uma análise;
2. definir uma empresa principal (`TARGET`);
3. cadastrar concorrentes (`COMPETITOR`);
4. coletar eventos a partir de providers;
5. persistir e deduplicar acontecimentos;
6. consultar uma timeline comparativa;
7. opcionalmente enriquecer eventos individuais com um `AnalysisProvider`.

A aplicação utiliza um monólito modular em FastAPI, com PostgreSQL, SQLAlchemy, Alembic, Pydantic, Jinja2, HTMX e Tailwind CSS.

Como o stack já era atual, modernização não foi tratada como simples atualização de dependências. O foco foi:

- manutenibilidade;
- coesão;
- desacoplamento;
- testabilidade;
- segurança;
- preservação de contratos.

### 2.1 Fora do escopo

Foram deliberadamente excluídos:

- novas funcionalidades de negócio;
- autenticação ou SSO real;
- integração real com X;
- workers e filas;
- scheduler;
- microsserviços;
- SPA ou novo framework frontend;
- Repository Pattern genérico;
- CQRS;
- Clean Architecture completa;
- atualização arbitrária de dependências.

Essas exclusões seguem **KISS** e **YAGNI** e evitam transformar uma atividade de refactoring em expansão de produto.

---

## 3. Metodologia

### 3.1 Preservação da versão original

A Entrega 1 foi preservada em:

```text
v1.0-mvp
└── 0274c56
```

Isso tornou possível comparar continuamente o estado refatorado com o comportamento original.

### 3.2 Blindagem pré-refactoring

A branch `refactoring` foi criada diretamente a partir de `v1.0-mvp`.

Antes das mudanças arquiteturais foram adicionados testes de caracterização para:

- contratos REST;
- URLs e métodos Web;
- wizard;
- TARGET e COMPETITOR;
- coleta;
- falha parcial;
- rollback;
- deduplicação;
- timezone;
- timeline;
- filtros;
- HTMX;
- Setup;
- análise de evento;
- integração PostgreSQL.

O teste PostgreSQL existente também foi reescrito, pois ainda representava o fluxo anterior ao wizard.

### 3.3 Refatoração incremental

As mudanças foram realizadas em intervenções pequenas e semanticamente separadas, com validação frequente da suíte.

### 3.4 Integração

As frentes Core/Services/Segurança e Web Layer foram desenvolvidas separadamente e depois integradas.

Na integração, contratos da Entrega 1 que haviam sido removidos durante uma etapa intermediária da Web Layer foram restaurados:

- `PUT /ui/companies/{id}`;
- `?tab=profile`;
- `?tab=monitoring`;
- `/ui/analyses/new?step=`;
- `?step=abc` → 422.

A decisão foi preservar comportamento externo, mesmo quando esses contratos não eram mais utilizados diretamente pelos templates.

### 3.5 Revisão independente

Uma revisão técnica independente e somente leitura comparou `v1.0-mvp` com o resultado integrado.

O veredito foi:

> **APROVADO COM RESSALVAS.**

Nenhuma correção de código obrigatória foi identificada. As ressalvas finais estavam concentradas em documentação e em dívidas herdadas já existentes na versão original.

---

## 4. Baseline

### 4.1 Validação da versão original

Sobre `v1.0-mvp`:

| Verificação | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 53 passed, 1 skipped |
| `uv run --locked ruff check .` | sem erros |
| `uv run --locked ruff format --check .` | 39 arquivos conformes |
| `uv run --locked alembic check` | nenhuma nova operação detectada |
| `npm run build` | concluído |
| Teste PostgreSQL opt-in | desatualizado em relação ao wizard |

### 4.2 Estado após a blindagem

| Verificação | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 161 passed, 1 skipped |
| Suíte com PostgreSQL opt-in | 162 passed |
| Ruff lint | passou |
| Ruff format | passou |
| Alembic check | passou |
| Build | passou |

Nessa etapa não houve refactoring estrutural da aplicação.

---

## 5. Diagnóstico das dívidas técnicas

| Problema | Diagnóstico |
| --- | --- |
| Teste PostgreSQL representando fluxo antigo | confirmado |
| Services dependentes de FastAPI/`HTTPException` | confirmado |
| `collect_analysis()` concentrando responsabilidades | confirmado |
| Busca de empresa por website duplicada | confirmado |
| Web Layer concentrada em único módulo | confirmado |
| Divergência entre regra de website do wizard e serviço | confirmada e preservada como dívida |

Mudanças arquiteturais maiores, como Repository Pattern genérico ou hierarquias extensas de exceções, foram avaliadas e rejeitadas por não apresentarem benefício proporcional ao tamanho do MVP.

---

## 6. Intervenções aplicadas

### 6.1 Testes de caracterização

A primeira intervenção não alterou a arquitetura. Seu objetivo foi criar uma rede de segurança antes do refactoring.

Os testes adicionados passaram a proteger propriedades como:

- status e mensagens de erro;
- sequência do wizard;
- rotas e métodos HTTP;
- semântica transacional da coleta;
- rollback isolado por empresa/provider;
- deduplicação;
- redirects;
- HTMX;
- filtros;
- integração PostgreSQL.

Uma lacuna concreta foi detectada durante o trabalho: em determinado momento da evolução da suíte, a remoção do `rollback()` não era suficientemente detectada pelos testes existentes.

Foi então adicionado um teste específico para garantir que uma falha real de persistência:

- descarte os eventos pendentes daquele par;
- mantenha pares anteriormente confirmados;
- zere `persisted` do par que falhou;
- permita que o processamento continue.

Essa sequência exemplifica o papel dos testes de caracterização: **fixar o comportamento antes de alterar a estrutura interna**.

### 6.2 Desacoplamento de Services em relação ao FastAPI

#### Problema

Na versão original, todos os cinco módulos de `app/services/` importavam FastAPI e utilizavam `HTTPException`.

Isso fazia a camada de aplicação conhecer detalhes do protocolo HTTP.

#### Técnica

- Separation of Concerns;
- desacoplamento do transporte;
- erros semânticos de aplicação.

#### Solução

Foram introduzidas três categorias:

- `NotFoundError`;
- `ConflictError`;
- `BusinessRuleError`.

Todas herdam de `ApplicationError`.

A tradução para 404, 409 e 422 passou a ocorrer em `app/http_errors.py`, registrado na composição da aplicação.

#### Resultado

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Services importando FastAPI | 5 | 0 |
| `raise HTTPException` em Services | 15 | 0 |

Os corpos `{"detail": ...}` e os status observáveis foram preservados.

Essa alteração melhora a separação entre aplicação e transporte, mas não é apresentada como adoção integral de Dependency Inversion em toda a arquitetura: os Services continuam utilizando SQLAlchemy diretamente, decisão proporcional ao MVP.

### 6.3 Simplificação de `collect_analysis()`

#### Problema

`collect_analysis()` concentrava:

- carregamento da análise;
- empresas;
- providers;
- chamadas externas;
- validação;
- deduplicação;
- criação de eventos;
- commit;
- rollback;
- contadores;
- status agregado.

#### Técnica

- Extract Method;
- SRP;
- KISS.

#### Resultado

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Complexidade ciclomática de `collect_analysis()` | 11 | 3 |
| Linhas da função | 83 | 23 |
| Maior complexidade dos helpers extraídos | — | 4 |

A função passou a atuar principalmente como orquestradora.

Os helpers mantêm responsabilidades específicas, como:

- coleta de um par empresa/provider;
- validação de registros;
- persistência de eventos;
- derivação do status agregado.

#### Semântica preservada

Continuam válidos:

- commit por par empresa/provider;
- rollback do par que falha;
- continuidade dos demais pares;
- preservação de commits anteriores;
- deduplicação por empresa, fonte e URL;
- validação de fonte;
- obrigatoriedade de timezone;
- conversão para UTC;
- estados `success`, `partial` e `failure`.

A métrica `11 → 3` representa **redução da complexidade da função de orquestração e melhor distribuição de responsabilidades**, não eliminação das decisões existentes no algoritmo.

### 6.4 Consolidação da identidade por website

#### Problema

`get_or_create_company()` e `update_company()` possuíam implementações independentes da mesma busca por website normalizado.

#### Técnica

- DRY;
- Extract Function;
- Single Source of Truth localizada.

#### Resultado

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Implementações da busca em `companies.py` | 2 | 1 |
| Complexidade de `update_company()` | 6 | 4 |
| Complexidade de `get_or_create_company()` | 4 | 3 |

A divergência entre a comparação usada pelo wizard e `normalize_website()` foi deliberadamente preservada, pois alterá-la mudaria quando e como o erro aparece para o usuário.

### 6.5 Modularização da Web Layer

#### Problema

A versão original concentrava toda a Web UI em:

```text
app/web/routes.py
```

Esse arquivo possuía:

- 620 linhas;
- 27 funções;
- 16 combinações caminho/método.

Misturava:

- páginas simples;
- wizard;
- períodos;
- workspace;
- filtros;
- view data;
- Setup;
- HTMX;
- análise de evento.

#### Técnica

- Extract Module;
- Extract Function;
- SRP;
- DRY;
- Functional Core;
- KISS.

#### Estrutura final

```text
app/web/
├── router.py
├── templating.py
├── errors.py
├── periods.py
├── wizard.py
├── workspace.py
└── routes/
    ├── pages.py
    ├── wizard.py
    ├── workspace.py
    ├── setup.py
    └── event_analysis.py
```

`periods.py`, `wizard.py` e `workspace.py` contêm lógica pura, testável sem `TestClient`.

`routes/*` permanece responsável pela fronteira HTTP.

`errors.py` concentra a tradução `ValueError → HTTPException(422)` para regras da Web.

`router.py` compõe os sub-routers e preserva a ordem necessária para que `/ui/analyses/new` seja registrado antes de `/ui/analyses/{analysis_id}`.

#### Métricas

| Métrica | Antes | Depois |
| --- | ---: | ---: |
| Maior módulo Web | 620 | 149 |
| Funções no maior módulo | 27 | no máximo 5 |
| Combinações caminho/método Web | 16 | 16 |
| Caminhos Web distintos | 13 | 13 |
| Módulos de lógica pura | 0 | 3 |
| Total de linhas Python em `app/web/` | 620 | 734 |

O crescimento total de 620 para 734 linhas não contradiz a modernização.

A modularização adiciona imports, declarações de router, assinaturas explícitas e fronteiras entre arquivos. O indicador relevante é a redução de **concentração de responsabilidade**, não a redução absoluta de LOC.

---

## 7. Preservação de contratos

A integração final restaurou e protegeu contratos presentes na Entrega 1.

### `PUT /ui/companies/{id}`

Permanece com o mesmo comportamento do POST.

### `?tab=profile`

Continua retornando 303 para:

```text
/ui/analyses/{id}/setup
```

### `?tab=monitoring`

Continua selecionando a Timeline quando `view` não foi explicitamente definido.

### `/ui/analyses/new?step=`

O parâmetro `step: int = 1` permanece limitado ao intervalo de 1 a 5.

Um valor inválido como:

```text
?step=abc
```

continua produzindo 422 pelo FastAPI.

### Contratos finais

| Superfície | Resultado |
| --- | --- |
| Web | 16 combinações caminho/método em 13 caminhos |
| REST | 13 combinações caminho/método em 11 caminhos |
| OpenAPI | equivalente à versão original |
| Parâmetros e status relevantes | equivalentes |

---

## 8. Auditoria de segurança

### 8.1 Achado corrigido: esquema executável em links

Na versão original, valores de `Company.website` e `Event.url` eram renderizados diretamente em `href`.

O autoescape do Jinja2 protege o conteúdo HTML, mas não impede a execução de esquemas como:

```text
javascript:alert(1)
```

O vetor foi reproduzido na versão original.

### Correção

Foi criado o filtro `safe_href`, registrado na instância única de `Jinja2Templates`.

A política final:

- permite `http`;
- permite `https`;
- preserva valores sem esquema;
- neutraliza outros esquemas para `#`;
- trata diferenças de caixa;
- trata espaços e caracteres de controle;
- neutraliza falhas de parsing.

O filtro é aplicado aos quatro links dinâmicos relevantes da Web UI.

### Testes

Os testes cobrem exemplos de:

- `javascript:`;
- `data:`;
- `vbscript:`;
- variações com caixa mista;
- tabs;
- espaços;
- quebras de linha;
- caracteres de controle;
- URLs legítimas.

Contra `v1.0-mvp`, oito desses testes falham, reproduzindo a vulnerabilidade original.

### Natureza da alteração

Essa é a **única mudança de comportamento observável intencional** em relação à versão original.

Ela é classificada como correção de segurança associada à modernização e não como refactoring comportamental puro.

### 8.2 Dívida herdada: CSRF e validação de Host

A aplicação não implementa:

- token CSRF;
- validação de `Origin`;
- validação de `Referer`;
- validação explícita de `Host`;
- `TrustedHostMiddleware`.

O Docker Compose publica a aplicação somente em `127.0.0.1`, reduzindo a superfície de exposição.

Isso, porém, não elimina requisições cross-site iniciadas pelo navegador local e também não elimina o risco de DNS rebinding na ausência de validação de Host.

O Dockerfile faz bind em `0.0.0.0`; portanto, uma publicação do container em todas as interfaces ampliaria a exposição.

Essa limitação:

- já existia em `v1.0-mvp`;
- não foi introduzida pelo refactoring;
- permanece fora do escopo desta entrega.

O estado atual não deve ser tratado como configuração apropriada para exposição pública.

### 8.3 Outras verificações de segurança

Também foram verificados:

- segredos versionados;
- `.env`;
- `SecretStr`;
- logs;
- chaves de GNews e Gemini;
- mensagens de providers;
- SQL;
- templates;
- dependências;
- Docker;
- tratamento de exceções.

A auditoria registrada durante a execução reportou:

- `npm audit`: nenhuma vulnerabilidade conhecida naquele momento;
- `pip-audit`: nenhuma vulnerabilidade conhecida no conjunto exportado de dependências naquele momento.

Os lockfiles não foram alterados após essa auditoria.

Esses resultados são evidência temporal, não garantia permanente sobre vulnerabilidades futuras.

---

## 9. Validação de paridade

### 9.1 Testes finais

| Comando | Resultado |
| --- | --- |
| `uv run --locked pytest -q` | 246 passed, 1 skipped |
| Suíte completa com `TEST_POSTGRES_URL` | 247 passed |
| `uv run --locked ruff check .` | sem erros |
| `uv run --locked ruff format --check .` | 60 arquivos conformes |
| `uv run --locked alembic check` | nenhuma nova operação detectada |
| `npm run build` | concluído |

### 9.2 Comparação independente

A revisão técnica final confirmou:

- OpenAPI completo equivalente;
- inventário de rotas equivalente;
- 13 combinações REST em 11 caminhos;
- 16 combinações Web em 13 caminhos;
- parâmetros, schemas e status relevantes equivalentes;
- ordem necessária dos routers preservada;
- wizard preservado;
- redirects preservados;
- HTMX preservado;
- Timeline preservada;
- Setup preservado;
- coleta preservada;
- análise de evento preservada.

Também foram executados testes da versão atual contra o código da versão original.

A divergência observada foi a esperada:

- testes de segurança falham contra o código vulnerável original;
- um monkeypatch aponta para um módulo diferente devido à reorganização estrutural.

### Formulação adotada

A conclusão correta é:

> **Há evidência forte de paridade funcional nos fluxos e contratos caracterizados, exceto pela correção deliberada de segurança em links externos.**

Não se afirma equivalência formal para qualquer entrada possível ou qualquer condição concorrente.

---

## 10. Métricas antes e depois

| Indicador | Antes | Depois | Interpretação |
| --- | ---: | ---: | --- |
| Services importando FastAPI | 5 | 0 | menor acoplamento ao transporte |
| `HTTPException` nos Services | 15 | 0 | erros de aplicação independentes de HTTP |
| complexidade de `collect_analysis()` | 11 | 3 | orquestração mais simples |
| linhas de `collect_analysis()` | 83 | 23 | responsabilidade mais focada |
| busca de website em `companies.py` | 2 | 1 | duplicação eliminada |
| maior módulo Web | 620 | 149 | menor concentração |
| total Python em `app/web/` | 620 | 734 | crescimento estrutural esperado |
| Web caminho/método | 16 | 16 | contrato preservado |
| caminhos Web | 13 | 13 | contrato preservado |
| REST caminho/método | 13 | 13 | contrato preservado |

A modernização não buscou minimizar LOC, mas reduzir acoplamento e concentração de responsabilidade.

---

## 11. KISS, YAGNI e decisões conscientemente rejeitadas

Durante o processo, algumas possibilidades foram descartadas por ausência de necessidade concreta.

### Hierarquia extensa de exceções

Não foram criadas classes específicas para cada entidade, pois três categorias semânticas já representam todos os tratamentos existentes.

### Repository Pattern

Os Services continuam utilizando `Session` do SQLAlchemy diretamente.

No tamanho atual do sistema, introduzir outra camada aumentaria a abstração sem remover complexidade relevante.

### `Literal` para status de coleta

Foi evitado porque alteraria o schema OpenAPI publicado.

### Microsserviços e novas camadas

Nenhuma decomposição em serviços distribuídos foi realizada.

### Remoção de contratos legados

`PUT`, `?tab=` e `?step=` foram preservados mesmo sem uso direto pelos templates, pois faziam parte do comportamento observável da Entrega 1.

Essas decisões mostram que modernização foi tratada como melhoria de desenho existente, e não como oportunidade para criar arquitetura futura especulativa.

---

## 12. Uso de IA no processo

Agentes de IA foram utilizados em papéis diferentes:

1. análise e planejamento técnico;
2. execução assistida das intervenções;
3. geração e ampliação de testes;
4. revisão independente;
5. integração;
6. revisão final de documentação.

Os agentes receberam restrições explícitas de:

- não adicionar features;
- preservar contratos;
- utilizar commits pequenos;
- justificar abstrações;
- validar mudanças;
- respeitar KISS/YAGNI.

A utilização de contexto independente na revisão buscou reduzir o risco de **Architectural Drift**, isto é, aceitar automaticamente decisões produzidas pelo mesmo agente que implementou a solução.

### 12.1 Prompts versionados

Os prompts recuperados e versionados em `prompts/refactoring/` incluem:

- `03-web-layer-refactoring.md`;
- `core-services-refactoring.md`;
- `web-layer-integration.md`;
- `final-documentation-hygiene.md`.

Nos arquivos recuperados posteriormente, trechos estritamente operacionais que não pertencem ao conteúdo técnico da entrega foram omitidos e **marcados explicitamente entre colchetes**.

Não foram reconstruídos retroativamente prompts que não puderam ser recuperados de forma fiel.

Prompts puramente operacionais de Git também não foram incluídos por não constituírem instruções de refactoring.

---

## 13. Evidências e reprodutibilidade

As evidências principais versionadas são:

- `docs/refactoring/00-baseline.md`;
- `docs/refactoring/01-core-services.md`;
- `docs/refactoring/02-security-audit.md`;
- `docs/refactoring/registro-de-alteracoes.md`;
- `docs/refactoring/web-layer-plan.md`;
- testes automatizados;
- inventários de rotas;
- commits da implementação;
- prompts recuperados.

### 13.1 Evidência auxiliar

Durante o desenvolvimento foi executado um golden master de 117 requisições para comparar respostas Web antes e depois.

O executor não foi versionado.

Por isso, essa execução é tratada somente como **evidência auxiliar não reproduzível a partir do repositório**.

Ela não é usada como base principal da conclusão.

A evidência principal permanece nos testes versionados, na integração PostgreSQL, na comparação de contratos e na revisão independente.

---

## 14. Dívidas remanescentes

A entrega não elimina toda a dívida técnica do sistema.

Permanecem registradas:

1. **CSRF e validação de Host**  
   Ausência de token antifalsificação, verificação de origem e TrustedHost.

2. **Divergência da identidade de website no wizard**  
   A regra de UX continua diferente de `normalize_website()`.

3. **Contagem HTMX após coleta**  
   A resposta considera todos os eventos da análise, e não apenas o período solicitado.

4. **Validação de website na entrada**  
   O formato não é restringido na entrada; a segurança de links é aplicada na saída.

5. **Busca linear por website**  
   Adequada ao volume do MVP, mas linear no número de empresas.

6. **Handler da classe base `ApplicationError`**  
   Os handlers estão registrados para as três subclasses atualmente utilizadas. Um `ApplicationError` lançado diretamente produziria erro 500; atualmente não há chamador que faça isso.

7. **Pontos de maior complexidade remanescentes**  
   `wizard.validate_step` e `gnews.fetch` permanecem entre os pontos mais complexos da aplicação.

Esses itens não configuram regressões da modernização.

---

## 15. Limitações da avaliação

A validação comprova os cenários cobertos e caracterizados, mas não constitui prova formal de equivalência para qualquer estado possível.

Em particular:

- os testes PostgreSQL cobrem o fluxo integrado, mas não esgotam todos os cenários concorrentes;
- a auditoria de vulnerabilidades de dependências representa o momento em que foi executada;
- não foi realizado smoke test manual final da interface após a última passagem documental;
- o golden master externo não é reproduzível a partir do repositório.

Essas limitações são registradas para evitar conclusões mais fortes do que as evidências permitem.

---

## 16. Conclusão

A modernização atingiu o objetivo da atividade sem transformar o refactoring em expansão de produto.

A versão final mantém o monólito modular e os fluxos funcionais já existentes, mas apresenta fronteiras internas mais claras:

- Services deixaram de depender diretamente de FastAPI;
- erros de aplicação passaram a ser independentes do transporte HTTP;
- `collect_analysis()` foi reduzido a uma orquestração mais simples;
- duplicação na identidade por website foi eliminada nos Services;
- a Web Layer deixou de concentrar múltiplas responsabilidades em um único módulo;
- regras puras da Web passaram a ter testes específicos;
- contratos de compatibilidade foram preservados;
- uma vulnerabilidade real de XSS foi identificada, reproduzida e corrigida;
- a suíte final passou com PostgreSQL habilitado.

As métricas mostram menor concentração e menor acoplamento, não necessariamente menor volume total de código.

A revisão independente não identificou regressão funcional não intencional introduzida pela modernização.

A conclusão sustentada pelas evidências é:

> **A modernização melhorou a sustentabilidade arquitetural do Bisb e preservou os fluxos e contratos caracterizados da Entrega 1, com uma única mudança comportamental deliberada para neutralizar URLs inseguras.**

Ao mesmo tempo, o resultado não deve ser interpretado como eliminação integral da dívida técnica nem como configuração pronta para exposição pública.
