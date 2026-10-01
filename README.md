# Competitive Monitor

**Competitive Monitor** é um MVP de monitoramento competitivo que permite acompanhar uma empresa-alvo e seus concorrentes em uma timeline única, reunindo notícias e publicações do X/Twitter.

O analista define manualmente as empresas monitoradas. Cada empresa pode ter um perfil básico manual e opcional com mercado, produtos e público-alvo. O projeto está antes da execução do Prompt 2: a base técnica do backend existe, mas o fluxo funcional do MVP ainda está planejado.

## Fluxo principal do MVP

```text
Criar análise
→ definir TARGET
→ adicionar COMPETITOR
→ executar coleta
→ persistir eventos
→ consultar timeline comparativa
```

Os providers podem ser reais ou mockados. O MVP deve funcionar localmente sem credenciais externas. `search_term` e o perfil manual são opcionais.

## Arquitetura

O MVP adota um **monólito modular FastAPI**. A aplicação reúne:

- Web UI server-rendered pelo FastAPI;
- Web Routes para páginas e fragmentos HTML;
- REST API Routes para contratos de API;
- camada compartilhada `Application / Services`;
- PostgreSQL;
- Source Providers para notícias e publicações do X.

Web Routes e REST API Routes reutilizam diretamente os mesmos serviços. A Web UI não chama sua própria REST API via HTTP interno apenas para reutilizar regras. Consulte a [arquitetura oficial da Aula 1](docs/arquitetura.md) para os componentes, modelo, endpoints e fluxos detalhados.

## Stack

### Backend

- Python 3.14, FastAPI, Uvicorn e Pydantic Settings;
- PostgreSQL 16, SQLAlchemy síncrono, psycopg e Alembic;
- uv para dependências;
- pytest e HTTPX/TestClient para testes;
- Ruff para lint e formatação;
- Docker Compose para o banco local.

As versões exatas das dependências de Python estão no [lockfile](backend/uv.lock).

### Web UI

- Jinja2 e HTML5;
- Tailwind CSS;
- HTMX;
- JavaScript vanilla apenas quando necessário.

A interface será renderizada pelo próprio FastAPI. Não haverá SPA ou aplicação frontend independente. Tailwind será compilado para CSS estático e HTMX estará disponível como asset local; a demonstração não deve depender de CDN em runtime. Essas tecnologias estão decididas, mas ainda não estão configuradas ou implementadas no repositório.

## Estado atual

### Implementado/configurado

- Aplicação base FastAPI com `create_app`.
- Configuração por ambiente com Pydantic Settings.
- PostgreSQL 16 via Docker Compose e infraestrutura de conexão SQLAlchemy.
- Ambiente Alembic, sem migrações de negócio.
- Health checks `/health` e `/health/ready`.
- OpenAPI e Swagger.
- Testes de configuração e health checks da infraestrutura.
- pytest, HTTPX/TestClient e Ruff configurados.
- Dependências gerenciadas por uv e registradas no lockfile.

### Planejado para o MVP

- Entidades `Analysis`, `Company`, `AnalysisCompany` e `Event`, com migrações de negócio.
- Application / Services e endpoints REST de negócio.
- Web Routes, templates Jinja2, Tailwind compilado e HTMX local.
- Providers mockados ou reais, coleta, deduplicação e persistência de eventos.
- Timeline com filtros e interface completa.

Essas funcionalidades ainda não estão entregues. Health checks e conexão ao banco, isoladamente, não representam o MVP funcional.

## Critério de aceite

O MVP funcional será considerado concluído quando for possível, pela Web UI:

1. Criar uma análise.
2. Definir exatamente uma empresa `TARGET`.
3. Ter ao menos um `COMPETITOR`.
4. Executar uma coleta real ou mockada.
5. Persistir os eventos.
6. Consultar a timeline comparativa com filtros.

O perfil manual e `search_term` são opcionais.

## Estrutura do repositório

```text
.ai/
├── architecture.md
├── business-rules.md
├── standards.md
└── tech-stack.md

backend/
frontend/

docs/
└── arquitetura.md

prompts/
├── prompt_architecture.md
├── context-generation.md
└── implementation.md

competitive_monitor_mvp.md
README.md
```

O diretório `frontend/` existente contém documentação e não representa uma aplicação frontend independente. A Web UI do MVP será servida pelo FastAPI.

## Documentação e prompts

- [Arquitetura oficial da Aula 1](docs/arquitetura.md)
- [Discovery, visão e roadmap](competitive_monitor_mvp.md)
- [Contexto de arquitetura](.ai/architecture.md)
- [Regras de negócio](.ai/business-rules.md)
- [Padrões de desenvolvimento](.ai/standards.md)
- [Stack técnica](.ai/tech-stack.md)
- [Registro de prompts da Aula 1](prompts/prompt_architecture.md)
- [Prompt 1 oficial da Aula 2 — geração de contexto](prompts/context-generation.md)
- [Prompt 2 oficial da Aula 2 — implementação](prompts/implementation.md)
- [README do backend](backend/README.md)
- [README do frontend](frontend/README.md)

## Entregáveis da disciplina

- Documento de arquitetura.
- Contexto operacional em `.ai/`.
- Prompts utilizados.
- Implementação em repositório público.
- MVP executável localmente.
- Vídeo de demonstração de 3 a 10 minutos.

Os entregáveis são acompanhados durante o desenvolvimento; esta lista não marca conclusão antecipada.

## Pendências atuais

- Período padrão da coleta; 7 dias permanece uma proposta.
- Escolha definitiva do provider real de notícias.
- Viabilidade do X Provider real.
- Detalhes finais de contratos HTTP e validações que ainda não tenham sido definidos pela arquitetura e pelos arquivos .ai/.
- Cenário final da demonstração.

A escolha ou viabilidade dos providers reais não bloqueia o MVP: os providers mockados devem permitir a execução local e a demonstração do fluxo completo sem credenciais externas.

## Próximos passos

1. Executar [prompts/implementation.md](prompts/implementation.md).
2. Implementar e validar o fluxo funcional local.
3. Executar testes, lint e migrações.
4. Validar a Web UI com providers mockados.
5. Revisar README e documentação contra o código realmente entregue.
6. Publicar o repositório.
7. Gravar o vídeo de demonstração.

## Equipe

- Leticia
- Luane
- Luca
- Felipe
