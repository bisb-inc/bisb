# Competitive Monitor

**Competitive Monitor** é um MVP de monitoramento competitivo para acompanhar uma empresa-alvo e seus concorrentes em uma timeline única de notícias e publicações do X/Twitter. O Analista informa manualmente as empresas; cada uma pode ter perfil manual opcional com mercado, produtos e público-alvo.

## Fluxo principal

```text
Criar análise
→ definir TARGET
→ adicionar COMPETITOR
→ executar coleta
→ persistir eventos
→ consultar timeline comparativa
```

O fluxo funciona localmente com providers mockados, sem credenciais externas. Providers reais podem ser adicionados, mas não são necessários para a demonstração. Perfil e `search_term` são opcionais; sem termo explícito, usa-se o nome da empresa.

## Arquitetura

O MVP é um **monólito modular FastAPI** com Web UI server-rendered, Web Routes, REST API Routes, `Application / Services` compartilhados, PostgreSQL e Source Providers. Web Routes retornam HTML Jinja2; API Routes retornam contratos REST. Ambas usam diretamente os mesmos serviços, sem chamadas HTTP internas da Web UI à REST API.

Consulte a [arquitetura oficial da Aula 1](docs/arquitetura.md) para modelo de dados, endpoints e fluxos.

## Stack

### Backend

- Python 3.14, FastAPI, Uvicorn e Pydantic Settings;
- PostgreSQL 16, SQLAlchemy síncrono, psycopg e Alembic;
- uv, pytest, HTTPX/TestClient e Ruff;
- Docker Compose para PostgreSQL local.

As versões Python estão registradas em [backend/uv.lock](backend/uv.lock).

### Web UI

- Jinja2 e HTML5, renderizados pelo FastAPI;
- Tailwind CSS compilado em CSS estático;
- HTMX servido localmente;
- JavaScript vanilla apenas quando necessário.

Não existe SPA nem aplicação frontend independente. Node/npm serve somente como ferramenta local de compilação/cópia dos assets, nunca como runtime da aplicação. A execução da demonstração não depende de CDN.

## Estado implementado

O fluxo funcional do MVP está implementado no código atual:

- Entidades `Analysis`, `Company`, `AnalysisCompany` e `Event`, migração Alembic e deduplicação por `(company_id, source, url)`;
- TARGET único por análise, concorrentes adicionados/removidos manualmente e Company compartilhada entre análises;
- REST API para análises, empresas, coleta e eventos;
- Web UI para criar/listar análises, manter concorrentes, editar perfil/termo de busca, executar coleta e consultar timeline;
- Filtros por empresa, fonte e período; ordenação por `published_at DESC` e `collected_at DESC`;
- Mock Providers de notícias (`GNEWS`) e X, sem credenciais externas, com identificação `is_mock` na interface;
- Falha total/parcial por provider sem descartar resultados bem-sucedidos;
- Templates Jinja2, Tailwind CSS compilado e HTMX local.

Providers reais GNews/X não estão integrados. O período é informado em cada coleta; o grupo não definiu período padrão. Autenticação, autorização, IA, workers, filas, alertas e funcionalidades V2–V5 continuam fora do MVP.

## Executar localmente

Requisitos: Python 3.14, uv, Docker Desktop e Node.js/npm para compilar os assets. Os comandos abaixo são PowerShell, executados em `backend/`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv sync --locked
npm ci
npm run build
docker compose --env-file .env up -d --wait
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app --reload
```

A Web UI abre em <http://127.0.0.1:8000/> e a REST API em <http://127.0.0.1:8000/docs>. O banco usa `127.0.0.1:5433`. A configuração completa, schemas e modo mock estão no [README do backend](backend/README.md).

## Critério de aceite

O MVP funcional está demonstrável pela Web UI: criar análise, definir exatamente um TARGET, adicionar ao menos um COMPETITOR, executar coleta real ou mockada, persistir eventos e consultar a timeline com filtros. Perfil manual e `search_term` são opcionais.

## Estrutura do repositório

```text
.ai/
├── architecture.md
├── business-rules.md
├── standards.md
└── tech-stack.md

backend/
├── app/
├── migrations/
├── tests/
└── README.md

frontend/
└── README.md

docs/
└── arquitetura.md

prompts/
├── prompt_architecture.md
├── context-generation.md
└── implementation.md

competitive_monitor_mvp.md
README.md
```

O diretório `frontend/` contém apenas orientação; a interface está integrada à aplicação FastAPI.

## Documentação e prompts

- [Arquitetura oficial da Aula 1](docs/arquitetura.md)
- [Discovery, visão e roadmap](competitive_monitor_mvp.md)
- [Prompt utilizado na arquitetura da Aula 1](prompts/prompt_architecture.md)
- [Prompt 1 da Aula 2 — contexto operacional](prompts/context-generation.md)
- [Prompt 2 da Aula 2 — implementação](prompts/implementation.md)
- [Arquitetura operacional](.ai/architecture.md)
- [Regras de negócio](.ai/business-rules.md)
- [Padrões de desenvolvimento](.ai/standards.md)
- [Stack técnica](.ai/tech-stack.md)
- [Execução do backend e Web UI](backend/README.md)
- [Estrutura do diretório frontend](frontend/README.md)

## Verificações

Em `backend/`:

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic check
npm run build
```

Os testes padrão usam SQLite temporário e providers mockados. A integração PostgreSQL pode ser executada com `TEST_POSTGRES_URL` apontando para uma base de teste isolada; detalhes em [backend/README.md](backend/README.md).

## Entregáveis da disciplina

- Documento de arquitetura;
- contexto `.ai/`;
- prompts utilizados;
- implementação em repositório público;
- MVP executável localmente;
- vídeo de demonstração de 3 a 10 minutos.

A gravação do vídeo e a escolha final do cenário de apresentação continuam pendentes.

## Pendências atuais

- Provider real definitivo de notícias e viabilidade do X Provider real;
- contratos/validações não definidos pela arquitetura e contexto operacional;
- período padrão da coleta, que não é imposto pelo código;
- cenário final da demonstração.

Providers mockados permitem executar localmente e demonstrar o fluxo completo sem credenciais externas.

## Equipe

- Leticia
- Luane
- Luca
- Felipe
