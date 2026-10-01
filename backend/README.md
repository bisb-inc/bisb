# Backend

Base executável da API REST do Competitive Monitor, com Python 3.14, FastAPI,
SQLAlchemy 2, psycopg 3 e Alembic. Dependências gerenciadas por uv e PostgreSQL 16
executado pelo Docker Compose.

Responsabilidades de negócio previstas para as próximas entregas:

- Gerenciar análises, empresas (com perfil básico) e seus vínculos.
- Persistir `Analysis`, `Company`, `AnalysisCompany` e `Event`.
- Orquestrar a coleta por empresa.
- Integrar providers de notícias e X/mock.
- Normalizar resultados e disponibilizar eventos para a timeline.

Consulte os [endpoints e o modelo inicial](../docs/arquitetura.md).
Cadastros, tabelas de negócio, coleta e providers ainda não foram implementados.

## Executar localmente

Pré-requisitos: uv, Python 3.14 (também gerenciável pelo uv) e Docker Desktop
em execução com containers Linux. Execute os comandos abaixo na pasta `backend/`.

```powershell
Copy-Item .env.example .env
uv sync --locked
docker compose --env-file .env up -d --wait
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Copie o `.env.example` somente na primeira configuração para preservar seus ajustes.
Configure o interpretador do editor como `backend/.venv/Scripts/python.exe` no Windows.

A API atende em `http://127.0.0.1:8000`, com Swagger em `/docs` e contrato em
`/openapi.json`. O PostgreSQL atende em `127.0.0.1:5433`, com volume persistente.
O Compose cria apenas o banco; a API roda no ambiente virtual local.

## Configuração

| Variável | Uso |
| --- | --- |
| `APP_NAME` | Nome da API; padrão `Competitive Monitor` |
| `ENVIRONMENT` | Identificação do ambiente; padrão `development` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` ou `CRITICAL`; padrão `INFO` |
| `DATABASE_URL` | Obrigatória; URL com driver `postgresql+psycopg://` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Inicialização do banco pelo Compose |

A aplicação lê `backend/.env`; variáveis do processo têm prioridade. O Alembic usa
a mesma configuração. As credenciais do exemplo são apenas para desenvolvimento local.
Mantenha `DATABASE_URL` consistente com as variáveis do Compose. Alterar estas variáveis
não altera usuários/senhas de um volume PostgreSQL já inicializado.
Arquivos `.env`, ambientes virtuais e caches são ignorados pelo Git.

## Health checks

| Rota | Resultado |
| --- | --- |
| `GET /health` | HTTP 200, `{"status":"ok"}`; não acessa o banco |
| `GET /health/ready` | Executa `SELECT 1`; HTTP 200, `{"status":"ok","database":"ok"}` |
| `GET /health/ready` com falha no banco | HTTP 503, `{"status":"unavailable","database":"unavailable"}` |

A API inicia mesmo quando o banco está indisponível. A conexão e as consultas têm
limites de 3 segundos; estes limites são individuais, não um prazo total da requisição.
As sessões são fechadas ao terminar a requisição e o pool é liberado ao encerrar a API.
Os logs de readiness não incluem credenciais nem detalhes da exceção do banco.

## Migrações

O Alembic está configurado com o metadata da base SQLAlchemy. Ainda não há revisões
ou tabelas de negócio; `upgrade head` valida a conexão e prepara o controle do Alembic.
Quando os modelos forem implementados, importá-los no ambiente de migração antes
de gerar e revisar uma revisão:

```powershell
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
```

Migrações são explícitas; a aplicação não cria tabelas ao iniciar.

## Verificação

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Os testes automatizados usam sessões simuladas e não dependem do Docker. Para validar
a integração real, execute `alembic upgrade head` e consulte `/health/ready` com o banco
ativo. Depois execute `docker compose stop db`: a mesma rota deve retornar 503, enquanto
`/health` continua retornando 200. Restaure com `docker compose up -d --wait`.

Encerre a API com `Ctrl+C` e o banco com `docker compose stop db`; os dados permanecem
no volume. Autenticação, deploy, CI e integrações GNews/X pertencem às próximas etapas.

## Organização

- `app/api/`: rotas HTTP e contratos de resposta.
- `app/core/`: configuração compartilhada.
- `app/db/`: base ORM, engine e sessões.
- `migrations/`: ambiente Alembic e futuras revisões.
- `tests/`: configuração e comportamento dos health checks.

Serviços, modelos de negócio e providers serão adicionados com suas funcionalidades.
