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
| `GNEWS_API_KEY` | Chave opcional; quando configurada, ativa notícias reais do GNews. Mantenha-a somente no `.env` local. |
| `ANALYSIS_PROVIDER` | Seleção explícita `gemini` ou `mock`; padrão e `.env.example` usam `mock`. |
| `GEMINI_MODEL` | Modelo Gemini usado na análise; padrão `gemini-3.8-flash` no código e no Compose. Ajuste para um modelo disponível na conta usada. |
| `GEMINI_API_KEY` | Chave opcional, necessária quando `ANALYSIS_PROVIDER=gemini`; nunca a registre ou inclua em imagens/documentos. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Inicialização do banco pelo Compose |

A aplicação lê `backend/.env`; variáveis do processo têm prioridade. Mantenha a URL consistente com as credenciais usadas para inicializar o volume. Alterar os valores no `.env` não altera usuários/senhas de um volume já criado. Os valores do `.env.example` destinam-se somente ao desenvolvimento local.

`backend/.env` não deve ser versionado. `.env.example` não contém chaves reais; `GNEWS_API_KEY` e `GEMINI_API_KEY` são tratados como `SecretStr`. Não inclua seus valores em logs, respostas, documentação ou imagens. O serviço `migrate` recebe apenas a configuração de banco e não depende de Gemini. Após alterar variáveis no `.env`, recrie o serviço para atualizar seu ambiente: `docker compose --env-file .env up -d --force-recreate app`.

## Fluxo demonstrável e modo mock

Para executar sem credenciais externas, deixe `GNEWS_API_KEY` vazio e selecione `ANALYSIS_PROVIDER=mock`.

1. Abra `/ui/analyses` e selecione **Nova análise** (`/ui/analyses/new`).
2. Preencha as cinco etapas: **Análise**, **Empresa principal / TARGET**, **Concorrentes**, **Período** e **Revisão**. Nome/site são necessários; `search_term` é opcional e usa o nome como fallback. O wizard exige ao menos um concorrente.
3. Escolha **1 semana**, **1 mês**, **3 meses** ou **Personalizado** e confirme **Criar e analisar**. A ação cria os dados e executa a coleta inicial; não chama Gemini. Uma falha de coleta mantém a análise criada e é informada no workspace.
4. No workspace, use **Visão geral**, **Timeline** e **Empresas**. Timeline filtra por empresa, fonte e período, em ordem `published_at DESC`, com desempate `collected_at DESC`; os filtros HTMX mantêm uma URL navegável.
5. Use **Setup** (`/ui/analyses/{id}/setup`) para nome da análise, concorrentes, nome/site das empresas, perfil manual opcional e `search_term`. Alterar `Company` afeta todas as análises que a compartilham.
6. **Atualizar monitoramento** leva ao formulário de período na Visão geral. A coleta informa sucesso, sucesso parcial ou falha e quantidade de novos eventos.

O wizard inicia em **1 semana** como preset de UX. Cada coleta recebe datas concretas; nenhum período é persistido em `Analysis`. Semana inclui hoje e os seis dias anteriores; mês e trimestre usam subtração de meses de calendário. Datas inicial/final são inclusivas para o usuário, convertidas internamente ao intervalo UTC com fim exclusivo no dia seguinte. O cabeçalho informa evento mais recentemente recebido, não “última coleta”; não há registro de tentativas de coleta.

A Visão geral deriva a distribuição de eventos por empresa e destaca até cinco eventos com análise Gemini, ordenados por relevância e publicação; sem eles, usa os cinco mais recentes. Não cria scores nem chama Gemini automaticamente. O contador “Acontecimentos” mostra o total de eventos do recorte consultado.

Quando `GNEWS_API_KEY` estiver configurada em `backend/.env`, `GNewsProvider` consulta notícias reais. A chave é enviada no cabeçalho `X-Api-Key`, não na URL. O `search_term` da empresa (ou nome como fallback) é escapado e envolvido em aspas como frase exata: `q="Mercado Pago"`. HTTPX codifica os parâmetros; a consulta envia `in=title,description`, `sortby=publishedAt`, `from` e `to`, preservando o intervalo solicitado. Isso reduz matches amplos em nomes compostos sem aplicar classificação por IA ou filtros adicionais de relevância.

O provider normaliza título, descrição, URL e publicação, com `is_mock=false`. A implementação solicita até 10 resultados por consulta, limita a query final a 200 caracteres e espaça requisições em pelo menos 1,05 segundo por instância, respeitando o limite documentado para o plano gratuito. Não há paginação da busca externa; intervalos amplos não garantem cobertura exaustiva das notícias. Referências: [autenticação](https://docs.gnews.io/authentication), [endpoint de busca](https://docs.gnews.io/endpoints/search-endpoint) e [limites e erros](https://docs.gnews.io/error-handling).

Sem `GNEWS_API_KEY`, `MockNewsProvider` (fonte `GNEWS`) continua ativo. `MockXProvider` (fonte `X`) permanece ativo em qualquer configuração. Os mocks funcionam sem credenciais, produzem conteúdo previsível dentro do intervalo informado e persistem `is_mock=true`; a interface os identifica como **Demonstração · mock**. Se a chamada real ao GNews falhar, a coleta informa falha para essa fonte em vez de substituir silenciosamente o resultado por um mock; o provider X mockado continua sendo tentado. Repetir a coleta não duplica eventos com a mesma empresa, fonte e URL.

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
| `POST` | `/events/{event_id}/analysis?force=false` |
| `GET` | `/events/{event_id}/analysis` |

Exemplo mínimo de criação:

```json
{
  "name": "Concorrência financeira",
  "target": { "name": "Empresa Alfa", "website": "https://alfa.example" }
}
```

Na REST API, a análise é criada com exatamente um TARGET e pode começar sem concorrentes; o wizard exige ao menos um antes da confirmação. O endpoint de adicionar empresa cadastra somente COMPETITOR. A edição de Company é compartilhada entre análises. Veja os schemas completos em `/docs` e [app/schemas.py](app/schemas.py).

## Extensão opcional pós-MVP: análise de eventos por IA

A análise por IA é uma extensão opcional posterior ao MVP base e não altera o critério de aceite original. Na timeline, selecione **Analisar com IA** em um evento já coletado. A operação é individual e síncrona; não ocorre durante coleta ou carregamento da timeline. Um resultado existente é reutilizado, e **Reanalisar** solicita explicitamente uma nova chamada.

Configure `ANALYSIS_PROVIDER=gemini`, `GEMINI_API_KEY` e `GEMINI_MODEL` no `.env` para chamar Gemini. Chave ausente, erro de rede, quota ou resposta inválida produzem erro controlado, sem fallback para resultado simulado. Para execução local sem credencial, selecione `ANALYSIS_PROVIDER=mock`; a UI e API identificam o resultado como simulado. Não coloque a chave em documentação, logs ou respostas.

A integração Gemini foi validada em execução real. A suíte automatizada usa cliente mockado e não faz chamadas externas.

`EventAnalysis` armazena o resumo, categoria, intensidade de impacto, sentimento, relevância e justificativa separadamente do `Event` original. A coleta e a timeline permanecem disponíveis independentemente do provider de análise.

`AnalysisProvider` é independente de `SourceProvider`. Gemini usa o SDK `google-genai` e schema Pydantic para saída estruturada; recebe somente empresa, título, descrição, fonte e publicação. Não persiste a resposta bruta. A análise é genérica do acontecimento, sem comparação com um TARGET específico. O fragmento expansível identifica **Análise Gemini** ou **Análise simulada**; `Event.is_mock` e `EventAnalysis.is_mock` distinguem, respectivamente, origem do acontecimento e origem do enriquecimento.

POST reutiliza a análise existente; `force=true` reanalisa e só substitui o resultado após resposta válida. A unicidade usa `event_id` como PK/FK, com bloqueio do evento no PostgreSQL. Erros REST: evento/resultado inexistente `404`, configuração ausente `503`, falha do provider `502`, conflito de persistência concorrente `409`. O resultado anterior permanece disponível em falha de reanálise.

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

Os testes padrão usam SQLite temporário e clientes/providers externos mockados; não os trate como prova de integração com PostgreSQL, GNews ou Gemini. Para testar um banco PostgreSQL isolado, configure `DATABASE_URL` e `TEST_POSTGRES_URL` com uma base de teste dedicada, aplique as migrações e execute:

```powershell
uv run --locked alembic upgrade head
uv run --locked pytest -q tests/test_postgres_integration.py
```

O teste opt-in percorre persistência, Web UI, coleta e assets, mas ainda envia o formulário anterior ao wizard; precisa ser adaptado antes de validar o fluxo atual (ver abaixo). Não execute contra um banco com dados de usuário.

## Limitações conhecidas

- **Contagens após a coleta HTMX:** a resposta da coleta calcula o contador, os destaques e a distribuição por empresa a partir de todos os eventos da análise, enquanto a URL enviada em `HX-Push-Url` contém o intervalo coletado. Ao recarregar essa URL, o filtro de período é aplicado e as contagens podem mudar. Ver [Web Routes](app/web/routes.py).
- **Teste PostgreSQL opt-in:** o [teste](tests/test_postgres_integration.py) envia `name`, `target_name` e `target_website` diretamente para `/ui/analyses`, mas a rota atual espera `wizard_state`. O teste também contém expectativas da interface anterior.

Esses pontos são limitações concretas da implementação e da validação atuais, não funcionalidades futuras nem decisões arquiteturais pendentes. X real, paginação e coordenação de coletas concorrentes permanecem fora da implementação.

## Encerrar

No modo host, encerre o Uvicorn com `Ctrl+C` e pare o banco com `docker compose --env-file .env stop db`. No modo containerizado, use `docker compose --env-file .env down`; o volume PostgreSQL persiste. Não rode os dois modos ao mesmo tempo.
