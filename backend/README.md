# Backend e Web UI

O backend é um monólito modular FastAPI que serve a REST API e a Web UI Jinja2/HTMX. A interface HTML é servida em `/ui/analyses`; `/` redireciona para a lista. Os endpoints REST estão em `/docs` e seguem [docs/arquitetura.md](../docs/arquitetura.md). Ambas as interfaces chamam os mesmos serviços Python, sem HTTP interno para a própria API.

## Requisitos e modos de execução

O projeto oferece dois modos locais: aplicação e PostgreSQL em containers Docker, ou aplicação no host com somente o PostgreSQL em Docker Compose. Docker Desktop com containers Linux é necessário para ambos. O modo no host também requer Python 3.14, uv e Node.js/npm para compilar assets; Node não é runtime da aplicação.

Na primeira configuração, a partir de `backend/`, copie o exemplo sem sobrescrever um `.env` existente:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### Aplicação e PostgreSQL em Docker Compose

```powershell
docker compose --env-file .env up -d --build
```

O Compose constrói a imagem da aplicação, compila Tailwind e disponibiliza HTMX como asset local, aguarda o PostgreSQL ficar saudável, executa as migrações Alembic e inicia o FastAPI. A Web UI fica em `http://127.0.0.1:7778/`, a REST API em `/docs` e o PostgreSQL em `127.0.0.1:5433`. O endereço publicado da aplicação é apenas local. Acompanhe os serviços com `docker compose --env-file .env ps` e `docker compose --env-file .env logs -f app`.

O serviço `migrate` executa antes da aplicação. O container do backend conecta-se ao banco pelo endereço interno `db:5432`; a configuração `DATABASE_URL` no `.env` continua apontando para `127.0.0.1:5433` no modo host. O volume `postgres_data` preserva os dados ao remover os containers com `docker compose down`.

### Aplicação no host e PostgreSQL em Docker

```powershell
uv sync --locked
npm ci
npm run build
docker compose --env-file .env up -d --wait db
uv run --locked alembic upgrade head
uv run --locked uvicorn app.main:app --reload --port 7778
```

A Web UI fica em `http://127.0.0.1:7778/`, a REST API em `/docs` e o PostgreSQL em `127.0.0.1:5433`. `npm run build` compila `app/static/css/input.css` e copia HTMX e sua licença para `app/static/js/`; os arquivos são servidos por `/static/` sem depender de CDN.

Não execute os dois modos simultaneamente: ambos usam o mesmo volume e publicam a porta 7778.

## Configuração

| Variável | Uso |
| --- | --- |
| `APP_NAME` | Nome da aplicação; padrão `Competitive Monitor` |
| `ENVIRONMENT` | Ambiente; padrão `development` |
| `LOG_LEVEL` | Nível de log; padrão `INFO` |
| `DATABASE_URL` | URL PostgreSQL `postgresql+psycopg://`; obrigatória |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Inicialização do banco pelo Compose |

A aplicação lê `backend/.env`; variáveis do processo têm prioridade. Mantenha a URL consistente com as credenciais usadas para inicializar o volume. Alterar os valores no `.env` não altera usuários/senhas de um volume já criado. Os valores do `.env.example` destinam-se somente ao desenvolvimento local.

## Fluxo demonstrável e modo mock

1. Abra a Web UI e crie uma análise informando nome, empresa-alvo e site.
2. Adicione ao menos um concorrente com site na lateral da aba **Monitoramento**.
3. Na aba **Perfil da empresa**, preencha opcionalmente mercado, produtos, público-alvo e termo de busca. Um termo vazio usa o nome da empresa.
4. Informe as datas inicial/final na coleta e execute-a. Nenhum período padrão é imposto.
5. Consulte e filtre a timeline por empresa, fonte e intervalo.

O projeto implementa `MockNewsProvider` (fonte `GNEWS`) e `MockXProvider` (fonte `X`). Eles funcionam sem credenciais externas, retornam um acontecimento previsível dentro do intervalo informado e persistem `is_mock=true`. A interface marca cada resultado como **Demonstração · mock**. Repetir a coleta não duplica eventos com a mesma empresa, fonte e URL. Providers reais GNews/X ainda não estão integrados.

A coleta tenta cada provider para cada empresa e persiste cada resultado bem-sucedido independentemente das demais tentativas. A resposta REST informa `success`, `partial` ou `failure` e o estado por fonte/empresa.

Exemplo de uso REST com período explícito:

```json
POST /analyses/{id}/collect
{
  "from_date": "2026-09-25",
  "to_date": "2026-10-01"
}
```

## API REST

Os contratos OpenAPI ficam em `/openapi.json` e Swagger em `/docs`.

| Método | Rota |
| --- | --- |
| `POST` | `/analyses` |
| `GET` | `/analyses` |
| `GET` | `/analyses/{id}` |
| `POST` | `/analyses/{id}/companies` |
| `DELETE` | `/analyses/{id}/companies/{companyId}` |
| `PUT` | `/companies/{id}` |
| `POST` | `/analyses/{id}/collect` |
| `GET` | `/analyses/{id}/events?company=&source=&from=&to=` |
| `GET` | `/companies/{id}/events` |

Exemplo mínimo de criação:

```json
{
  "name": "Concorrência financeira",
  "target": { "name": "Empresa Alfa", "website": "https://alfa.example" }
}
```

A análise é criada com exatamente um TARGET e pode começar sem concorrentes. O endpoint de adicionar empresa cadastra somente COMPETITOR. A edição de Company é compartilhada entre análises. Veja os schemas completos em `/docs`.

## Verificações

Na pasta `backend/`:

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic upgrade head
uv run --locked alembic check
npm run build
```

Os testes padrão usam SQLite temporário e providers mockados; não os trate como prova de integração PostgreSQL. Para testar um banco PostgreSQL isolado, configure `DATABASE_URL` e `TEST_POSTGRES_URL` com uma base de teste dedicada, aplique as migrações e execute:

```powershell
uv run --locked alembic upgrade head
uv run --locked pytest -q tests/test_postgres_integration.py
```

O teste real percorre a Web UI, a coleta mockada, os assets servidos e a timeline, e remove os registros temporários criados. Não execute contra um banco com dados de usuário.

## Encerrar

No modo host, encerre o Uvicorn com `Ctrl+C` e pare o banco com `docker compose --env-file .env stop db`. No modo containerizado, use `docker compose --env-file .env down`; o volume PostgreSQL persiste. Não rode os dois modos ao mesmo tempo.
