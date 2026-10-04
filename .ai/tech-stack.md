# Stack técnica

Referência técnica do projeto. Prioridade: [arquitetura oficial](../docs/arquitetura.md), [visão estratégica](../competitive_monitor_mvp.md) e evidências do repositório.

## Estados da stack

| Área | Decisão | Estado |
| --- | --- | --- |
| Backend | Python 3.14, FastAPI e Uvicorn | Implementado/configurado |
| Configuração | Pydantic Settings, variáveis de ambiente e arquivo local .env | Implementado/configurado |
| Persistência — infraestrutura | PostgreSQL 16, SQLAlchemy síncrono e psycopg | Implementado/configurado |
| Migrações | Alembic com revisão das entidades do MVP | Implementado/configurado |
| Dependências | uv, pyproject.toml e uv.lock | Implementado/configurado |
| Testes da base | pytest e HTTPX/TestClient | Implementado/configurado |
| Lint/formatação | Ruff | Implementado/configurado |
| Ambiente local | Aplicação FastAPI e PostgreSQL via Docker Compose; execução alternativa da API no host com Uvicorn | Implementado/configurado |
| Comunicação — base | API REST com health checks | Implementado/configurado |
| Documentação | Markdown e Mermaid | Implementado/configurado |
| Persistência de negócio | Modelos e migrações das entidades do MVP | Implementado/configurado |
| Endpoints de negócio | API REST para análises, empresas, coleta e eventos | Implementado/configurado |
| Web UI — renderização | Jinja2 e HTML5, renderizados pelo próprio FastAPI | Implementado/configurado |
| Web UI — estilização | Tailwind CSS compilado para CSS estático | Implementado/configurado |
| Web UI — interações | HTMX local; JavaScript vanilla apenas quando necessário | Implementado/configurado |
| Notícias | GNews real quando `GNEWS_API_KEY` está configurada; mock como fallback local | GNews implementado; chave fornecida pelo ambiente |
| X/Twitter | Mock X; X Provider real opcional conforme viabilidade | Mock implementado; provider real pendente |
| Assets da Web UI | Compilação Tailwind e cópia local de HTMX por ferramentas npm | Implementado/configurado |
| API do X | Viabilidade de acesso e uso da integração real | Pendente de decisão |
| Período padrão da coleta | 7 dias é apenas uma proposta | Pendente de decisão |

Frontend: Web UI server-rendered pelo próprio FastAPI, com Jinja2, HTML5, Tailwind CSS e HTMX. JavaScript vanilla apenas quando necessário. Não há SPA, aplicação frontend independente, React, Vue ou Next.js.

Mock Providers fazem parte da estratégia técnica do MVP e atendem à mesma abstração dos providers reais; não são uma tecnologia externa separada. Devem garantir execução local e demonstração sem credenciais externas, independentemente da viabilidade das integrações reais.

## Arquitetura da interface

- Web Routes retornam páginas completas ou fragmentos HTML renderizados com Jinja2.
- HTMX realiza interações e atualizações parciais por meio das Web Routes.
- A REST API permanece disponível com seus endpoints oficiais.
- Web Routes e REST API Routes reutilizam diretamente a mesma camada `Application / Services`.
- A aplicação não deve fazer HTTP interno para sua própria REST API apenas para reutilizar lógica.

Web UI e REST API são duas interfaces para os mesmos serviços no monólito modular FastAPI.

## Assets da Web UI

- Compilar Tailwind CSS para CSS estático.
- Servir os arquivos estáticos pela aplicação FastAPI.
- Disponibilizar HTMX como asset local para execução e demonstração.
- Evitar dependência de CDN em runtime.

A compilação de assets deve usar somente a ferramenta de build necessária, sem introduzir uma estrutura mais complexa ou um frontend independente. Node.js não é runtime nem componente arquitetural da aplicação; a escolha da ferramenta de compilação não altera essa decisão.

## Versões verificadas nos arquivos

Python: `3.14` em [.python-version](../backend/.python-version), com faixa `>=3.14,<3.15` em [pyproject.toml](../backend/pyproject.toml). Esses arquivos não fixam a versão de patch do interpretador.

PostgreSQL: imagem `postgres:16` no [compose.yaml](../backend/compose.yaml). A tag não fixa patch ou digest.

Versões abaixo registradas em [uv.lock](../backend/uv.lock), não inferidas da instalação local:

| Pacote | Versão no lockfile |
| --- | --- |
| fastapi | 0.141.1 |
| uvicorn | 0.54.0 |
| pydantic-settings | 2.15.0 |
| sqlalchemy | 2.0.54 |
| psycopg | 3.3.6 |
| alembic | 1.20.0 |
| pytest | 9.1.1 |
| httpx | 0.28.1 |
| ruff | 0.16.9 |

Versões dos assets confirmadas no [package-lock.json](../backend/package-lock.json): Tailwind CSS `4.3.0`, `@tailwindcss/cli` `4.3.0` e HTMX `2.0.11`. Versões de Jinja2 `3.1.6` e `python-multipart` `0.0.32` estão no `uv.lock`.

A imagem da aplicação instala uv `0.10.4`, fixado no Dockerfile. Não há versão exata de Docker Compose fixada no repositório. Não inventar outras versões. Não alterar dependências sem necessidade técnica e manter o lockfile consistente.

Jinja2, Tailwind CSS e HTMX estão configurados como dependências/assets da Web UI. HTML5 e JavaScript vanilla compõem a interface; JavaScript adicional não é requisito do MVP. Node/npm são ferramentas de build, não runtime da aplicação.

## Configuração existente a preservar

- Compose executa a aplicação e o PostgreSQL; o banco usa volume persistente e health check. Para execução no host, PostgreSQL é publicado em `127.0.0.1:5433`; entre containers, o backend usa `db:5432`.
- `APP_NAME`, `ENVIRONMENT`, `LOG_LEVEL` e `DATABASE_URL` no Settings; variáveis do processo precedem `backend/.env`.
- Driver `postgresql+psycopg://`; credenciais reais fora do código/versionamento.
- Sessões síncronas com encerramento por requisição; migrações explícitas.
- A aplicação publica a Web UI e a API em `127.0.0.1:7778` no host; dentro do container o Uvicorn atende na porta 8000. Swagger e OpenAPI permanecem disponíveis.

Instruções de execução: [backend/README.md](../backend/README.md).

## Execução e deployment

A execução local é requisito do MVP. Implantação/deploy permanece fora do escopo da entrega atual, sem plataforma definida.

## Pendências do grupo

- Período padrão de coleta; 7 dias ainda não confirmado.
- Plano/limites operacionais do GNews; viabilidade e credenciais do X real.
- Contratos e validações pendentes em [business-rules.md](business-rules.md).
- Cenário final de demonstração; bancos digitais permanece uma sugestão estratégica.

O modo mock deve viabilizar o MVP independentemente da viabilidade das integrações reais. Preservar a Web UI integrada definida acima, sem introduzir serviços de IA, autenticação, filas ou workers.
