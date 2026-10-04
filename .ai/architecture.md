# Contexto de arquitetura

Contexto operacional para agentes que trabalham no repositório. Fonte principal: [arquitetura oficial](../docs/arquitetura.md); visão e roadmap: [competitive_monitor_mvp.md](../competitive_monitor_mvp.md). O código em `backend/` é a evidência do estado atual; este arquivo descreve o que **já existe**, para que não seja reimplementado.

## Produto e hipótese

O Competitive Monitor acompanha uma empresa-alvo (`TARGET`) e seus concorrentes (`COMPETITOR`) em uma timeline única de notícias e publicações do X/Twitter.

Hipótese: “Dada uma empresa-alvo e uma lista de concorrentes definida pelo analista, é possível coletar acontecimentos de diferentes fontes, normalizá-los, persistir os resultados e apresentá-los em uma timeline comparativa.”

Perfil funcional único: Analista. Não há autenticação, autorização ou entidade de usuário.

## Componentes implementados

Monólito modular FastAPI. Web UI e REST API são duas interfaces para os mesmos serviços; não há frontend independente.

| Componente | Local | Responsabilidade |
| --- | --- | --- |
| Web Routes | `app/web/routes.py` | Navegação, formulários e HTMX; retornam páginas ou fragmentos Jinja2 |
| Templates | `app/web/templates/` (`workspace/`, `partials/`) | Apresentação; sem regra de negócio nem acesso ao banco |
| REST API Routes | `app/api/routes/` | Contratos REST oficiais e da extensão de análise |
| Application / Services | `app/services/` | Análises, empresas, coleta, eventos e análise de eventos |
| Modelos e persistência | `app/models.py`, `app/db/`, `migrations/` | SQLAlchemy síncrono, PostgreSQL e Alembic |
| SourceProvider | `app/providers/base.py`, `gnews.py`, `mock.py` | `fetch(company, start, end)` → eventos normalizados |
| AnalysisProvider | `app/providers/analysis.py` | Gemini ou mock para enriquecer um `Event` |
| Configuração | `app/core/config.py` | Pydantic Settings; segredos como `SecretStr` |

Web Routes e REST API Routes chamam diretamente os serviços. **Nunca fazer HTTP interno para a própria REST API.** Contratos externos ficam isolados nos providers.

Seleção de providers, feita em `create_app`:

- notícias: `GNewsProvider` quando `GNEWS_API_KEY` não está vazia; caso contrário, `MockNewsProvider` (fonte `GNEWS`, `is_mock=true`);
- X: `MockXProvider` sempre; não existe provider real do X;
- análise: `ANALYSIS_PROVIDER=gemini` → `GeminiAnalysisProvider`; `mock` → `MockAnalysisProvider`. Não há fallback automático entre eles.

## Web UI implementada

- **Lista de análises** (`/ui/analyses`) com a ação **Nova análise**.
- **Wizard** (`/ui/analyses/new`) em cinco etapas: Análise → Empresa principal / TARGET → Concorrentes → Período → Revisão. O estado do rascunho trafega no campo `wizard_state` e só é persistido na confirmação. **Criar e analisar** cria a análise, executa a coleta inicial e redireciona para a Visão geral. O wizard exige ao menos um concorrente.
- **Workspace** (`/ui/analyses/{id}?view=overview|timeline|companies`):
  - **Visão geral**: contador de acontecimentos, distribuição de eventos por empresa e até cinco destaques. Os destaques priorizam eventos com análise Gemini, ordenados por relevância; sem ela, usam recência. A tela também traz o formulário de coleta (**Atualizar monitoramento**).
  - **Timeline**: filtros por empresa, fonte e período via HTMX, com URL navegável (`HX-Push-Url`). Mostra mocks identificados, link para a fonte original e **Analisar com IA** por evento.
  - **Empresas**: TARGET e concorrentes, com link para o Setup.
- **Setup** (`/ui/analyses/{id}/setup`): nome da análise, adição/remoção de concorrentes, nome/site, perfil manual e `search_term` de cada empresa.

Os parâmetros antigos `?tab=profile` e `?tab=monitoring` apenas redirecionam para Setup e Timeline; as antigas abas “Monitoramento” e “Perfil da empresa” não existem mais.

## Fluxos

**Coleta:** Web Route ou API → `collect_analysis` → para cada empresa e cada provider, `fetch` com o intervalo UTC. Cada par empresa/provider tem commit próprio, com deduplicação por `(company_id, source, url)`. Falha de um provider gera rollback apenas daquele par e é registrada no resultado (`success`/`partial`/`failure`). Erro do GNews real não troca para mock.

**Período:** cada coleta recebe `from_date`/`to_date`. Os presets da Web UI (1 semana, 1 mês, 3 meses, Personalizado) são convertidos em datas concretas nas Web Routes. Não há período persistido em `Analysis` nem padrão de domínio.

**Análise de evento (extensão pós-MVP):** ação explícita → `analyze_event` → `AnalysisProvider.analyze` → saída validada por `EventAnalysisContent` → `EventAnalysis` (1:1 com `Event`). O resultado existente é reutilizado; `force=true` reanalisa e só substitui após resposta válida. Nunca roda na coleta ou no carregamento da timeline.

## Critério de aceite do MVP base

O Analista cria uma análise, define exatamente um `TARGET`, tem ao menos um `COMPETITOR`, executa coleta com providers reais ou mockados, persiste os eventos e consulta a timeline com filtros. Perfil manual e `search_term` são opcionais. A análise por IA não faz parte desse critério.

## Extensões implementadas após o MVP base

Docker Compose; GNews real com busca por frase exata; enriquecimento individual por Gemini (`EventAnalysis`); redesign da Web UI com wizard, Visão geral e Setup separado. Essas extensões estão implementadas e não devem ser tratadas como trabalho futuro.

## Fora do escopo implementado

X real, autenticação/autorização, agendamento, workers, filas, alertas, crawling, análise automática ou em lote por IA, monitoramento contínuo, descoberta/classificação de concorrentes, perfil automático, Mapa Competitivo, paginação e coordenação de coletas concorrentes. SPA, React, Vue, Next.js e frontend independente não fazem parte da arquitetura. Não antecipar o roadmap (V2–V5) sem nova decisão do grupo.

## Limitações conhecidas

As limitações da implementação atual estão registradas em [backend/README.md](../backend/README.md#limitações-conhecidas): o contador inicial da Visão geral, a resposta HTMX da coleta e o teste PostgreSQL opt-in desatualizado. Não são decisões arquiteturais pendentes.
