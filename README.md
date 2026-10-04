# Competitive Monitor

**Competitive Monitor** é um MVP de monitoramento competitivo para acompanhar uma empresa-alvo e seus concorrentes em uma timeline única de notícias e publicações do X/Twitter.

## Problema e hipótese

Acompanhar concorrentes exige consultar várias fontes e comparar acontecimentos dispersos. O projeto testa a hipótese de que, dada uma empresa-alvo e uma lista de concorrentes definida pelo analista, é possível coletar acontecimentos de fontes diferentes, normalizá-los, persistir os resultados e apresentá-los em uma timeline comparativa.

O Analista informa as empresas manualmente. Cada empresa pode ter um perfil manual opcional (mercado, produtos e público-alvo) e um termo de busca (`search_term`); sem termo, usa-se o nome da empresa.

## MVP base e extensões implementadas

O **MVP base**, definido na arquitetura da Aula 1, cobre este fluxo:

```text
Criar análise
→ definir TARGET
→ adicionar COMPETITOR
→ executar coleta
→ persistir eventos
→ consultar timeline comparativa
```

Esse fluxo funciona com providers reais ou mockados.

Depois do MVP base, foram implementadas as seguintes **extensões**:

- execução da aplicação e do banco em Docker Compose;
- notícias reais pela GNews API;
- enriquecimento individual de eventos por Gemini (`EventAnalysis`);
- redesign guiado da Web UI, com wizard de criação, Visão geral e Setup separado.

Essas extensões já estão em funcionamento. O Gemini é opcional e não faz parte do critério de aceite original.

## Arquitetura

A solução é um **monólito modular FastAPI** composto por:

- Web UI server-rendered;
- Web Routes;
- REST API Routes;
- `Application / Services` compartilhados;
- PostgreSQL;
- providers desacoplados: `SourceProvider` para as fontes de acontecimentos e `AnalysisProvider` para o enriquecimento opcional.

Web Routes retornam HTML Jinja2 (páginas ou fragmentos HTMX); API Routes retornam contratos REST. Ambas chamam diretamente os mesmos serviços, sem HTTP interno da Web UI para a REST API.

Consulte a [arquitetura oficial](docs/arquitetura.md) para componentes, modelo de dados, endpoints, fluxos e decisões técnicas.

## Stack

### Backend

- Python 3.14, FastAPI, Uvicorn e Pydantic Settings;
- PostgreSQL 16, SQLAlchemy síncrono, psycopg e Alembic;
- HTTPX para o GNews e SDK `google-genai` para o Gemini;
- uv, pytest, HTTPX/TestClient e Ruff;
- Docker Compose para a aplicação FastAPI e o PostgreSQL locais.

As versões Python estão registradas em [backend/uv.lock](backend/uv.lock).

### Web UI

- Jinja2 e HTML5, renderizados pelo FastAPI;
- Tailwind CSS compilado em CSS estático;
- HTMX servido localmente;
- JavaScript vanilla apenas quando necessário.

Não existe SPA nem aplicação frontend independente. Node/npm serve somente como ferramenta local de compilação/cópia dos assets, nunca como runtime da aplicação. A execução da demonstração não depende de CDN.

## Estado implementado

- Entidades `Analysis`, `Company`, `AnalysisCompany`, `Event` e `EventAnalysis`, com migrações Alembic e deduplicação de eventos por `(company_id, source, url)`;
- `TARGET` único por análise, `COMPETITOR` adicionado/removido manualmente e `Company` compartilhada entre análises;
- REST API para análises, empresas, coleta, eventos e análise de eventos;
- Web UI com lista de análises, wizard em cinco etapas e workspace com **Visão geral**, **Timeline** e **Empresas**; manutenção separada em **Setup**;
- Coleta por empresa e provider, com falha parcial por provider sem descartar resultados bem-sucedidos;
- Filtros por empresa, fonte e período; ordenação por `published_at DESC` e `collected_at DESC`;
- Identificação de `is_mock` na interface, com resultados reais e mockados claramente diferenciados.

Cada coleta recebe um intervalo de datas. A Web UI oferece os presets **1 semana**, **1 mês**, **3 meses** e **Personalizado**; o wizard começa em 1 semana por conveniência. Esses presets são de interface: não há período persistido em `Analysis` nem regra de período padrão no domínio.

### Jornada pela Web UI

1. Na lista de análises, selecione **Nova análise**.
2. Percorra **Análise → Empresa principal / TARGET → Concorrentes → Período → Revisão**. Informe nome e site das empresas e ao menos um concorrente; perfil e termo de busca são opcionais.
3. **Criar e analisar** cria os registros, executa a coleta inicial e abre o workspace. Essa ação não chama o Gemini. Uma falha parcial ou total da coleta não desfaz a criação.
4. No workspace:
   - **Visão geral** mostra a distribuição de eventos por empresa e os acontecimentos em destaque. Os destaques priorizam a relevância de análises Gemini já existentes e, sem elas, a recência. Essa tela não faz nova chamada de IA.
   - **Timeline** permite explorar e filtrar os eventos.
   - **Empresas** lista o TARGET e os concorrentes.
5. **Atualizar monitoramento** leva ao formulário de coleta. **Setup** concentra o nome da análise, os concorrentes, os dados das empresas, o perfil manual e o `search_term`.

Na Timeline, cada evento mostra empresa e papel, fonte, data de publicação e marcação de mock, e dá acesso à fonte original. A ação opcional **Analisar com IA** fica em cada evento, e o resultado aparece em uma área recolhível.

### Integrações reais e simuladas

| Fonte | Com credencial | Sem credencial |
| --- | --- | --- |
| Notícias (`GNEWS`) | `GNewsProvider` real, ativado por `GNEWS_API_KEY`, com `is_mock=false` | `MockNewsProvider`, com `is_mock=true` |
| X (`X`) | — (integração real não implementada) | `MockXProvider`, com `is_mock=true` |
| Análise de evento | `GeminiAnalysisProvider`, com `ANALYSIS_PROVIDER=gemini` e `GEMINI_API_KEY` | `MockAnalysisProvider`, com `ANALYSIS_PROVIDER=mock` e resultado marcado como simulado |

O GNews usa `Company.search_term`, com fallback para `Company.name`, como frase exata: `Mercado Pago` gera `q="Mercado Pago"`. A consulta envia `in=title,description`, `sortby=publishedAt` e o intervalo da coleta. A chave vai no header `X-Api-Key`, nunca na URL. A busca exata reduz correspondências amplas em nomes compostos, sem garantir classificação semântica.

Se a chamada real ao GNews falhar, a coleta informa a falha dessa fonte e não troca para mock. Da mesma forma, o modo Gemini sem chave, ou com erro, retorna erro controlado em vez de resultado simulado.

### Extensão opcional pós-MVP: análise de eventos por IA

O analista pode pedir a análise individual de um evento já persistido. O resultado fica em `EventAnalysis`, separado de `Event`, com resumo, categoria, intensidade do impacto, sentimento, relevância de 0 a 100 e justificativa. A análise:

- é síncrona, disparada pela ação do usuário;
- não roda durante a coleta, de forma automática, em lote ou em background;
- reutiliza o resultado existente;
- só gera uma nova chamada com **Reanalisar**;
- preserva o resultado anterior quando a reanálise falha.

A integração com o Gemini foi validada em execução real; a suíte automatizada usa cliente mockado. Configuração e endpoints estão em [backend/README.md](backend/README.md).

## Executar localmente

Requisito: Docker Desktop com suporte a containers Linux. Os comandos abaixo são PowerShell, executados em `backend/`:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose --env-file .env up -d --build
```

O Compose compila os assets, inicia o PostgreSQL, aplica as migrações e sobe a aplicação. A Web UI fica em <http://127.0.0.1:7778/> e a REST API em <http://127.0.0.1:7778/docs>. O PostgreSQL também fica acessível no host em `127.0.0.1:5433`. Para rodar a aplicação no host com apenas o banco em Docker, veja os comandos alternativos no [README do backend](backend/README.md).

### Segredos e configuração

- `backend/.env` é local e não deve ser versionado.
- `.env.example` contém apenas valores de desenvolvimento e chaves vazias.
- `GNEWS_API_KEY` e `GEMINI_API_KEY` são tratadas como segredo: nunca as copie para documentação, imagens, logs ou commits.
- O Gemini só é usado quando selecionado explicitamente com `ANALYSIS_PROVIDER=gemini`.
- Para demonstrar sem credenciais, deixe `GNEWS_API_KEY` vazio e use `ANALYSIS_PROVIDER=mock`.

## Critério de aceite

O MVP funcional é demonstrável pela Web UI: criar uma análise, definir exatamente um TARGET, adicionar ao menos um COMPETITOR, executar coleta real ou mockada, persistir eventos e consultar a timeline com filtros. Perfil manual e `search_term` são opcionais. A análise por IA não faz parte deste critério.

## Estrutura do repositório

```text
.ai/                  # contexto operacional para agentes
├── architecture.md
├── business-rules.md
├── standards.md
└── tech-stack.md

backend/              # aplicação FastAPI (API, Web UI, serviços, providers)
├── app/
├── migrations/
├── tests/
└── README.md

frontend/
└── README.md         # apenas orientação; a Web UI está em backend/app/web/

docs/
└── arquitetura.md    # arquitetura oficial

prompts/              # registro histórico dos prompts
├── prompt_architecture.md
├── context-generation.md
└── implementation.md

competitive_monitor_mvp.md   # discovery, visão e roadmap
README.md
```

## Documentação e prompts

- [Arquitetura oficial](docs/arquitetura.md)
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

O processo de documentação seguiu uma ordem:

1. A [proposta](competitive_monitor_mvp.md) registra discovery e escopo.
2. A [arquitetura oficial](docs/arquitetura.md) define o MVP e registra o estado implementado.
3. Os arquivos `.ai/` servem de contexto operacional atualizado para agentes.
4. Os arquivos em `prompts/` preservam, como evidência histórica, os prompts usados em cada etapa. Por isso, não descrevem as extensões posteriores.

## Uso de agentes de IA

| Ferramenta | Uso |
| --- | --- |
| ChatGPT | Discovery, alternativas de produto, redução de escopo e estruturação inicial da arquitetura |
| Codex | Agente no repositório: consolidação da arquitetura, geração do contexto `.ai/` e implementação do MVP e das extensões |
| Claude Code | Agente no repositório: verificação de consistência entre documentação e código, correções e documentação de entrega |
| Mermaid | Diagramas de componentes, entidades e fluxos |

Fluxo de trabalho:

1. Arquitetura definida com apoio de chat.
2. Prompt de geração de contexto, que produz os quatro arquivos `.ai/`.
3. Prompt de implementação, executado por agente com acesso ao repositório.

Os arquivos `.ai/` são o contexto compartilhado por qualquer agente que atue no repositório: escopo, regras de negócio, stack permitida, decisões arquiteturais (ADRs) e o que **não** deve ser implementado. Decisões e prompts versionados tornam o trabalho independente do histórico de conversas de uma ferramenta específica.

### Controles adotados sobre o trabalho dos agentes

| Risco | Controle |
| --- | --- |
| Integração tecnicamente correta, mas com resultados de baixa qualidade | Validação com dados reais, além dos testes. Exemplo: o GNews busca o termo como frase exata, apenas em título e descrição, para evitar correspondências amplas em nomes compostos (`Mercado Pago`) |
| Documentação divergente do código | Afirmações sobre o estado implementado conferidas no código, com separação explícita entre MVP base e extensões pós-MVP |
| Expansão de escopo | Limites explícitos em `.ai/` (sem autenticação, workers, SPA ou análise automática) e ADRs que exigem nova decisão do grupo para serem revertidos |
| Exposição de segredos | Chaves apenas no `.env` local, tratadas como `SecretStr`, fora de URLs e logs; sem troca silenciosa de integração real por mock |
| Regressões | Testes automatizados com clientes externos mockados como critério de aceite de cada alteração, incluindo testes de regressão para defeitos corrigidos |

## Verificações

Em `backend/`:

```powershell
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked alembic check
npm run build
```

Os testes padrão usam SQLite temporário e clientes/providers externos mockados. Por isso, não comprovam integração real com PostgreSQL, GNews ou Gemini. O teste PostgreSQL opt-in precisa ser atualizado para o wizard antes de servir como evidência do fluxo atual. As limitações conhecidas estão no [README do backend](backend/README.md#limitações-conhecidas).

## Entregáveis da disciplina

- Documento de arquitetura;
- contexto `.ai/`;
- prompts utilizados;
- implementação em repositório, com acesso ao avaliador e publicação conforme a exigência da disciplina;
- MVP executável localmente;
- vídeo de demonstração de 3 a 10 minutos.

## Pendências atuais

- Definir o cenário final e gravar o vídeo de demonstração de 3 a 10 minutos.
- Confirmar o acesso/visibilidade do repositório exigido para a entrega.
- Atualizar e executar o teste PostgreSQL opt-in para o fluxo do wizard.
- Corrigir as limitações conhecidas registradas no [README do backend](backend/README.md#limitações-conhecidas), se o grupo decidir tratá-las antes da entrega.

A integração real com o X é uma evolução opcional não implementada e não bloqueia o MVP: os providers mockados permitem executar localmente e demonstrar o fluxo completo sem credenciais externas.

## Equipe

- Leticia
- Luane
- Luca
- Felipe
