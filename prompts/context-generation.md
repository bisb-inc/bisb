# Prompt 1 oficial — Aula 2: geração de contexto do MVP funcional

Este prompt gera ou revisa os quatro arquivos de contexto `.ai/` que orientarão
posteriormente o Prompt 2 na implementação do MVP funcional completo. Ele não
implementa a aplicação nem se limita à infraestrutura do backend.

Use o bloco abaixo com um agente que tenha acesso ao repositório. As fontes de
verdade devem estar disponíveis; informações ausentes devem ser tratadas como
pendências, sem inventar regras ou decisões.

```text
Atue como responsável pela consolidação do contexto técnico e funcional do
Competitive Monitor. Produza documentação explícita, coerente e suficiente para
que outro agente, sem acesso às discussões anteriores, possa implementar o MVP
completo a partir do Prompt 2.

1. FONTES DE VERDADE E INSPEÇÃO

Leia as fontes nesta ordem de prioridade:
1. docs/arquitetura.md: arquitetura oficial da Aula 1.
2. competitive_monitor_mvp.md: visão estratégica, escopo e roadmap.
3. Estado real do repositório: evidências do que está implementado ou planejado.

Inspecione os arquivos .ai/ existentes, código, configurações, manifests, lockfile
e testes pertinentes. Use os documentos oficiais para o estado-alvo e o código
para confirmar o estado atual. Documentação de uma funcionalidade não comprova
sua implementação; a existência de um teste não comprova sua execução.

Registre divergências entre as fontes, respeitando a arquitetura oficial para
o escopo e o desenho do MVP. Os requisitos confirmados neste prompt devem ser
consolidados no contexto; se houver incompatibilidade com as fontes, explicite-a
no relatório, sem editar os documentos de origem ou inventar uma solução.

2. VISÃO DO PRODUTO E HIPÓTESE

O Competitive Monitor é um MVP de inteligência competitiva para acompanhar uma
empresa-alvo e seus concorrentes em uma timeline única, consolidando acontecimentos
provenientes de notícias e publicações do X/Twitter.

Hipótese a validar pelo MVP:
“Dada uma empresa-alvo e uma lista de concorrentes definida pelo analista, é possível
coletar acontecimentos de diferentes fontes, normalizá-los, persistir os resultados
e apresentá-los em uma timeline comparativa.”

A solução deve permanecer deliberadamente pequena.

3. CRITÉRIO DO MVP FUNCIONAL COMPLETO

O contexto deve orientar a implementação posterior deste fluxo:
1. Criar uma análise.
2. Informar uma empresa-alvo.
3. Informar ao menos um concorrente.
4. Opcionalmente preencher perfil básico e search_term.
5. Executar uma coleta.
6. Consultar providers reais ou mockados.
7. Normalizar e persistir Event.
8. Consultar a timeline da análise.

Integrações externas não são obrigatórias para considerar o MVP funcional.
Quando credenciais, custo ou disponibilidade impedirem uma integração real,
deverá existir provider mock compatível para execução local e demonstração.

A base técnica do backend é um ponto de partida, não o limite desta entrega
funcional futura. Este prompt apenas prepara seu contexto, sem implementá-la.

4. DOMÍNIO E REGRAS CONFIRMADAS

Preserve Analysis, Company, AnalysisCompany e Event.

- TARGET e COMPETITOR pertencem a AnalysisCompany.role, não a Company.
- Uma análise possui exatamente uma empresa TARGET.
- Para validar o fluxo competitivo completo, deve existir ao menos um COMPETITOR.
  Concorrentes podem ser adicionados após a criação da análise; não transforme
  o critério de demonstração em obrigatoriedade no cadastro inicial.
- Company possui nome, site, search_term e perfil básico manual opcional:
  mercado, produtos e público-alvo.
- search_term usa o nome da empresa como fallback.
- O perfil manual não bloqueia a coleta; não há confirmação obrigatória de perfil.
- Eventos mockados devem ser identificados por is_mock.
- Evitar duplicação básica de eventos por (company_id, source, url).
- A timeline deve permitir filtros por empresa, fonte e período.
- Se um provider falhar, preserve os resultados das outras fontes e informe
  a falha parcial no status da coleta.

Preserve os relacionamentos, endpoints e demais decisões válidas da arquitetura
oficial. Não invente regras adicionais de produto, contratos ou validações:
registre lacunas como pendências para decisão antes da implementação dependente.

5. USUÁRIO

O único perfil funcional é Analista, que pode:
- Criar e consultar análises.
- Adicionar e remover concorrentes.
- Editar perfil básico e termo de busca.
- Executar coleta.
- Consultar e filtrar a timeline.

Autenticação, autorização e entidades de usuário ficam fora do MVP.
Analista descreve o uso do produto, não um sistema de controle de acesso.

6. PROVIDERS

A arquitetura abstrai fontes externas. Preveja:
- Provider de notícias: GNews ou equivalente.
- Provider do X, caso viável.
- Provider mock compatível para garantir execução local e demonstração.

Os providers devem retornar dados normalizados para o domínio, sem espalhar
contratos de APIs externas pelas regras de negócio. Reais e mockados devem
atender à mesma abstração de coleta. Identifique os dados simulados e preserve
a regra de falha parcial, sem exigir credenciais externas para demonstrar o MVP.

7. LIMITES DO PRODUTO

Não incorporar ao MVP:
- Mapa Competitivo.
- Crawling completo.
- Geração automática de perfil.
- Descoberta automática de concorrentes.
- Classificação de concorrentes.
- Análise ou enriquecimento por IA.
- Alertas.
- Workers, filas ou processamento contínuo.
- Autenticação e autorização.

Trate esses elementos como fora do MVP e, quando pertinentes, possibilidades
de roadmap. Não os transforme em dependências da entrega atual.

8. STACK CONFIRMADA E PENDÊNCIAS

Preserve as decisões confirmadas para o backend:
- Python, FastAPI e Uvicorn.
- Pydantic Settings para configuração.
- PostgreSQL, SQLAlchemy síncrono, psycopg e Alembic.
- uv para gerenciamento de dependências.
- pytest, HTTPX/TestClient e Ruff.
- Banco local via Docker Compose.

Não invente versões. Registre versões exatas somente quando verificáveis nos
arquivos do repositório ou no lockfile, indicando a origem da informação.
Não substitua as tecnologias existentes nem atualize dependências nesta etapa.

Preserve a arquitetura confirmada de monólito modular FastAPI:
- Web UI server-rendered pelo próprio FastAPI, com Jinja2 e HTML5.
- Tailwind CSS para estilização.
- HTMX desde o início para interações localizadas e atualizações parciais.
- JavaScript vanilla apenas quando necessário.
- Sem SPA, aplicação frontend independente, React, Vue ou Next.js.

Web Routes ficam separadas das REST API Routes. Web Routes retornam páginas ou
fragmentos HTML Jinja2; a REST API retorna contratos de API. Ambas reutilizam
diretamente Application / Services, sem duplicar regras e sem chamadas HTTP
internas para a própria REST API apenas para reutilizar lógica.

Fluxo da Web UI: Browser → Web Route → Application / Service → banco/providers
→ Web Route → página ou fragmento HTML Jinja2. HTMX mantém esse modelo server-rendered,
sem simular uma SPA.

Decisões de assets:
- Tailwind compilado localmente para CSS estático.
- HTMX disponível como asset local.
- Assets estáticos servidos pelo FastAPI.
- Evitar dependência de CDN em runtime para a demonstração.

Não imponha versão ou ferramenta de build que não esteja verificada no repositório.
A stack da Web UI está decidida; isso não significa que esteja instalada,
configurada ou implementada. Registre cada estado com base em evidências.

Período padrão de coleta: pendente de confirmação pelo grupo. “7 dias” é uma
proposta, não uma regra definitiva. Permanecem pendentes a escolha definitiva
do provider real de notícias, a viabilidade do X Provider real, os contratos e
validações ainda abertos e o cenário final da demonstração. Preserve outras
pendências válidas das fontes sem reabrir a decisão da Web UI nem preencher
lacunas por suposição.

9. ARQUIVOS A PRODUZIR OU REVISAR

Altere exclusivamente estes quatro arquivos:

.ai/standards.md
Registre convenções concretas, coerentes com a base existente: separação entre
rotas, regras de negócio, persistência e providers; configuração por ambiente;
proteção de segredos; testes dos fluxos e falhas; uso e identificação de mocks;
atualização da documentação. Diferencie convenções adotadas de sugestões pendentes.
Inclua convenções permanentes de Jinja2/templates, Web Routes, HTMX, Tailwind,
assets locais, acessibilidade e separação Web/API/services. Preveja testes básicos
das Web Routes críticas e dos fragmentos HTMX relevantes do fluxo principal.

.ai/architecture.md
Descreva o monólito modular FastAPI, os componentes e suas responsabilidades:
Web UI + REST API, Web Routes e API Routes separadas, Application / Services
compartilhados, persistência e abstração dos providers. Inclua o fluxo completo
do MVP e Browser → Web Route → Service → DB/providers → HTML, com renderização
Jinja2 e HTMX sem SPA. Preserve a arquitetura oficial e a base técnica existente,
sem impor funcionalidades do roadmap.

.ai/tech-stack.md
Liste tecnologias confirmadas, versões verificáveis e fontes dessas versões.
Registre Jinja2, HTML5, Tailwind CSS, HTMX e JavaScript vanilla quando necessário
como decisões confirmadas. Diferencie tecnologia decidida de tecnologia já
instalada/configurada e de integração apenas planejada. Preserve as decisões
de assets locais e destaque somente as pendências ainda abertas.

.ai/business-rules.md
Consolide entidades, TARGET/COMPETITOR por análise, empresa-alvo única,
concorrentes, perfil manual opcional, search_term, coleta, eventos mockados,
deduplicação, filtros, falha parcial e limites do produto.
Registre o critério de aceite do fluxo completo e o período de coleta pendente.
Preserve as regras de produto e interface já definidas; não acrescente regras
de negócio específicas de framework nem reabra decisões mínimas já confirmadas.

Os quatro documentos devem orientar um agente que não participou das conversas.
Utilize referências relativas válidas à arquitetura oficial e evite duplicações
contraditórias ou instruções que dependam de memória da conversa.

10. ESTADO ATUAL VERSUS ESTADO-ALVO

Diferencie explicitamente:
- Já implementado: infraestrutura atual do backend, confirmada por inspeção do
  código e da configuração.
- Planejado para o MVP: Web UI Jinja2/HTMX/Tailwind, Web Routes, entidades,
  Application / Services, endpoints REST de negócio, providers, coleta,
  persistência de eventos e timeline, enquanto ausentes do código.
- Roadmap futuro: fora do escopo da primeira versão.

Preserve a base técnica existente. Não descreva cadastros, coleta, persistência
de eventos ou interface como entregues sem evidência no repositório.
Não apresente intenção, configuração ou documentação como prova de funcionamento.
A decisão da stack de frontend não comprova implementação. Se o código evoluir,
atualize a classificação somente com evidência do estado real.

11. CRITÉRIOS DE ACEITE E RELATÓRIO

Ao finalizar, verifique:
- Os quatro arquivos .ai/ estão coerentes entre si e com docs/arquitetura.md.
- O contexto descreve o MVP funcional completo, não apenas a infraestrutura.
- As pendências permanecem explicitamente marcadas.
- A Web UI integrada e sua stack estão registradas como decisões confirmadas,
  sem confundir essa confirmação com implementação.
- Nenhuma funcionalidade do roadmap virou requisito do MVP.
- Implementado, planejado e futuro estão diferenciados.
- Links e referências são válidos.
- Nenhum código de negócio foi implementado.

Não altere código, dependências, docs/arquitetura.md, competitive_monitor_mvp.md,
README.md, prompts/implementation.md ou qualquer arquivo fora dos quatro .ai/
indicados. Não faça commit ou push.

Apresente:
1. Arquivos alterados.
2. Decisões consolidadas.
3. Pendências que ainda dependem do grupo.
4. Divergências encontradas entre documentação e estado real do repositório.
```
