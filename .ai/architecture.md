# Contexto de arquitetura — MVP funcional

Revisão documental de 29/09/2026. Fonte principal: [arquitetura oficial da Aula 1](../docs/arquitetura.md); referência estratégica: [discovery e roadmap](../competitive_monitor_mvp.md). A inspeção do repositório determina o estado de implementação, não redefine o escopo.

## Produto e hipótese

O Competitive Monitor acompanha uma empresa-alvo e seus concorrentes em uma timeline única de notícias e publicações do X/Twitter.

Hipótese a validar: “Dada uma empresa-alvo e uma lista de concorrentes definida pelo analista, é possível coletar acontecimentos de diferentes fontes, normalizá-los, persistir os resultados e apresentá-los em uma timeline comparativa.”

A solução permanece deliberadamente pequena. O único perfil funcional é Analista; não há autenticação, autorização ou entidade de usuário.

## Componentes e responsabilidades planejadas

O MVP é um **monólito modular FastAPI**, com Web UI e REST API como duas interfaces para os mesmos serviços. Não há aplicação frontend independente.

| Componente | Responsabilidade no MVP |
| --- | --- |
| Web UI | Renderizada pelo FastAPI com Jinja2 e HTML5, estilizada com Tailwind CSS e interativa com HTMX; JavaScript vanilla apenas quando necessário |
| Web Routes | Receber navegação, formulários e requisições HTMX; chamar diretamente os serviços e retornar páginas completas ou fragmentos HTML |
| REST API Routes | Preservar os endpoints REST oficiais e retornar contratos HTTP/API, utilizando a mesma camada de serviços |
| Application / Services | Concentrar a coordenação das regras de negócio, coleta e persistência, compartilhada por Web Routes e API Routes |
| PostgreSQL | Persistir Analysis, Company, AnalysisCompany e Event |
| Source Providers | Consultar notícias/X ou gerar dados mockados, retornando resultados normalizados para o domínio |

Web Routes e REST API Routes chamam diretamente Application / Services. **Web Routes/Jinja2 não devem chamar a própria REST API via HTTP interno apenas para reutilizar lógica.** Os serviços coordenam banco e providers; contratos externos ficam isolados nos providers. Diagramas e endpoints oficiais estão em [docs/arquitetura.md](../docs/arquitetura.md).

A interface planejada possui abas Monitoramento e Perfil da empresa para criar/consultar análises, manter concorrentes, editar perfil manual e `search_term`, executar coleta e consultar timeline com filtros. Deve identificar visualmente eventos mockados e preservar navegação por teclado, foco visível, responsividade e estados de carregamento, vazio e erro.

## Fluxo funcional completo

1. O analista cria uma análise com exatamente uma empresa-alvo.
2. Informa concorrentes manualmente, na criação ou depois. A demonstração completa exige ao menos um concorrente.
3. Opcionalmente preenche perfil básico e `search_term`; sem termo informado, a coleta usa o nome da empresa.
4. Aciona a coleta das empresas vinculadas à análise.
5. O backend consulta providers de notícias e X, reais ou mockados.
6. Os providers normalizam os resultados para o domínio; o backend persiste `Event`, identifica mocks e evita duplicações básicas.
7. Se uma fonte falhar, preserva os resultados das demais e informa o status por fonte.
8. O analista consulta a timeline da análise e filtra por empresa, fonte e período.

O perfil manual não bloqueia a coleta. Integrações reais não são obrigatórias: providers mockados compatíveis devem permitir execução local e demonstração quando credenciais, custo ou disponibilidade impedirem o acesso externo.

### Fluxo da Web UI com Jinja2 e HTMX

Browser → Web Route → Application / Service → banco/providers → Web Route → página ou fragmento Jinja2 retornado ao Browser.

HTMX é utilizado desde o início para executar coleta, aplicar filtros, adicionar/remover concorrentes e atualizar partes relevantes da interface quando isso simplificar a experiência. As requisições chegam a Web Routes dedicadas a respostas HTML completas ou parciais. A renderização permanece no servidor; a aplicação não se torna uma SPA.

Clientes REST acessam as API Routes oficiais, que reutilizam os mesmos serviços e retornam contratos de API em vez de HTML.

## Critério de aceite do MVP

O MVP funcional é considerado concluído quando o Analista consegue:

1. Criar uma análise.
2. Informar exatamente uma empresa `TARGET`.
3. Ter ao menos um `COMPETITOR` para validar o fluxo competitivo.
4. Executar uma coleta usando providers reais ou mockados.
5. Normalizar e persistir os eventos por meio do sistema.
6. Consultar a timeline da análise.

O perfil manual e `search_term` são opcionais e não bloqueiam esse fluxo. Quando o termo de busca não é informado, utiliza-se o nome da empresa.

## Domínio e API

Preservar as quatro entidades e seus relacionamentos: `Analysis` reúne empresas por `AnalysisCompany`; `Company` pode participar de várias análises e possuir vários `Event`. O papel `TARGET` ou `COMPETITOR` pertence a `AnalysisCompany.role`.

A API planejada cobre criação/listagem/consulta de análises, adição/remoção de concorrentes, edição de empresa/perfil, coleta e consulta dos eventos. Usar a tabela oficial de endpoints, sem criar contratos paralelos neste contexto. Regras consolidadas: [business-rules.md](business-rules.md).

## Já implementado — evidências no repositório

- Base FastAPI, configuração por ambiente, engine e sessões SQLAlchemy síncronas, health checks, OpenAPI e Swagger.
- Entidades `Analysis`, `Company`, `AnalysisCompany` e `Event`, TARGET único por análise, índice de deduplicação e migração Alembic.
- Application / Services compartilhados por Web Routes e REST API Routes, sem HTTP interno à própria API.
- Web UI Jinja2 com abas Monitoramento e Perfil da empresa, HTMX local e Tailwind compilado localmente.
- Providers mockados para notícias e X, coleta com falha parcial, persistência de eventos e timeline com filtros.
- PostgreSQL via Compose, testes funcionais com SQLite isolado e teste opt-in de fluxo Web UI com PostgreSQL real.

O diretório `frontend/` contém documentação da interface; o código Web UI está em `backend/app/web/` e os assets servidos em `backend/app/static/`.

## Planejado para o MVP — pendente de integração

- Provider real definitivo de notícias (GNews ou equivalente).
- Provider real do X, condicionado à viabilidade de acesso.

O fluxo mockado local não depende dessas integrações. Comandos e evidências verificadas estão no [README do backend](../backend/README.md); não confundir código planejado com integração externa validada.

## Fora do MVP e roadmap

Mapa Competitivo, crawling completo, perfil automático, descoberta/classificação de concorrentes, análise/enriquecimento por IA, alertas, workers, filas e processamento contínuo ficam fora. Autenticação e autorização também estão excluídas; não são dependências do MVP.

SPA, React, Vue, Next.js e aplicação frontend independente não fazem parte da arquitetura adotada.

A visão estratégica reserva V2 para enriquecimento automático do perfil, V3 para descoberta/classificação, V4 para IA e V5 para monitoramento contínuo/alertas. Nenhuma dessas versões deve ser antecipada nesta entrega.

## Pendências do produto e da arquitetura

- Período padrão de coleta pendente; 7 dias é somente uma proposta.
- Contratos detalhados, validações e decisões operacionais ainda não especificados estão listados em [business-rules.md](business-rules.md).
- Escolha do provider de notícias e viabilidade dos providers reais, incluindo acesso ao X. Providers mockados compatíveis devem permitir o fluxo completo sem integrações externas.
