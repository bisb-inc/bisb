# Prompt 2 oficial — Aula 2: implementação do MVP funcional

Este prompt orienta a implementação local e demonstrável do Competitive Monitor
a partir do contexto produzido pelo [Prompt 1](context-generation.md). A base técnica
existente deve ser preservada e ampliada para o fluxo funcional completo.

Cole o bloco abaixo em um agente com acesso ao repositório. A Web UI integrada ao
FastAPI é decisão definitiva e parte obrigatória da entrega. Preserve as pendências
restantes sem permitir que impeçam o fluxo mockado local.

```text
Implemente o MVP funcional completo do Competitive Monitor, preservando a base
técnica existente. Entregue código, migrações, testes e documentação coerentes
com as decisões confirmadas. Não se limite à infraestrutura do backend.

1. LEITURA OBRIGATÓRIA E FONTES DE VERDADE

Antes de alterar código, leia:
- docs/arquitetura.md.
- competitive_monitor_mvp.md.
- .ai/architecture.md.
- .ai/business-rules.md.
- .ai/standards.md.
- .ai/tech-stack.md.
- README.md, backend/README.md e frontend/README.md.
- Instruções locais aplicáveis, código, configurações, lockfile e testes existentes.

Em caso de conflito, respeite:
1. Arquitetura oficial em docs/arquitetura.md.
2. Os quatro arquivos .ai/ como contexto operacional.
3. Documento estratégico competitive_monitor_mvp.md.
4. Estado atual do código como evidência do que já existe.

A documentação define o estado-alvo; o código confirma o estado implementado.
Não reinvente regras de produto nem sobrescreva trabalho existente. Identifique
conflitos materiais e decisões pendentes antes de implementar as partes dependentes.

2. OBJETIVO E FLUXO FUNCIONAL

Entregue um MVP local e demonstrável que permita ao Analista, pela Web UI:
1. Criar uma análise.
2. Cadastrar exatamente uma empresa TARGET.
3. Adicionar ao menos um COMPETITOR.
4. Opcionalmente editar perfil básico e search_term.
5. Executar coleta.
6. Consultar providers reais ou mockados.
7. Normalizar e persistir Event.
8. Consultar a timeline da análise com filtros.

O MVP deve funcionar sem credenciais externas. A criação inicial pode ocorrer
sem concorrentes; ao menos um COMPETITOR é necessário para validar o fluxo completo.
Perfil manual e search_term não bloqueiam a coleta.

3. BACKEND, DOMÍNIO E MIGRAÇÕES

Preserve e amplie a base existente: Python, FastAPI, Uvicorn, Pydantic Settings,
PostgreSQL, SQLAlchemy síncrono, psycopg, Alembic e uv, conforme .ai/tech-stack.md.
Mantenha configuração, ciclo de vida das sessões, health checks e testes da base.
Não altere dependências sem necessidade técnica; mantenha o lockfile consistente.

Implemente Analysis, Company, AnalysisCompany e Event e suas migrações Alembic,
registrando os modelos no metadata. Migrações são explícitas, não criação automática
de tabelas na inicialização da API.

Preserve:
- Exatamente um TARGET por análise.
- TARGET | COMPETITOR em AnalysisCompany.role, nunca em Company.type.
- Concorrentes adicionados e removidos manualmente.
- Perfil básico manual opcional em Company: mercado, produtos e público-alvo.
- search_term opcional, com fallback para Company.name.
- is_mock persistido no Event.
- Deduplicação por (company_id, source, url).
- Timestamps com timezone e UTC consistente internamente; conversão para horário
  local na apresentação/frontend.

Aplique a comparação mínima de sites definida em .ai/business-rules.md: ignorar
diferenças triviais de http/https, barra final e www. Não criar canonicalização
avançada nem fundir empresas automaticamente em caso de conflito ou ambiguidade.

Company é compartilhada entre análises. Alterações em nome, site, search_term
ou perfil afetam a mesma empresa em todas as análises. Não criar cópias por análise,
versionamento ou histórico de perfil.

Separe rotas, regras de negócio, persistência e providers conforme .ai/standards.md.
Evite camadas e abstrações sem comportamento concreto. Proteja credenciais e não
sobrescreva arquivos locais de configuração existentes.

Implemente um monólito modular FastAPI com Web Routes, REST API Routes, camada
Application / Services compartilhada, persistência, providers, templates e assets.
Web Routes retornam HTML completo ou fragmentos Jinja2; API Routes retornam
contratos de API. Ambas chamam diretamente os mesmos serviços. Não realizar
chamadas HTTP internas para a própria REST API apenas para reutilizar lógica.

Adapte a estrutura real para uma organização conceitualmente equivalente a:

backend/app/
├── api/
│   └── routes/
├── web/
│   ├── routes/
│   └── templates/
├── services/
├── providers/
├── db/
└── static/

Não criar diretórios vazios ou camadas artificiais para obedecer ao desenho.
Preserve módulos existentes e adicione responsabilidades concretas.

4. ENDPOINTS REST

Implemente os endpoints definidos em docs/arquitetura.md, respeitando os métodos
HTTP e as responsabilidades oficiais. Não crie API paralela ou rotas extras
sem necessidade demonstrável.

Os fluxos devem permitir:
- Criar, listar e consultar análises.
- Adicionar e remover concorrentes.
- Editar Company, perfil e termo de busca.
- Executar coleta.
- Consultar timeline com filtros por empresa, fonte e período.
- Consultar eventos por empresa.

Detalhe os contratos mínimos necessários de forma consistente e documente-os
no OpenAPI, sem introduzir regras de produto. Se faltar uma decisão de produto
indispensável, explicite a pendência e continue as partes independentes.

5. PROVIDERS E MODO MOCK

Crie uma abstração comum SourceProvider que retorne dados normalizados para o
domínio e isole contratos de APIs externas das regras de negócio.

Implemente pelo menos providers mockados compatíveis para notícias e X/Twitter.
O modo mock deve:
- Funcionar localmente sem credenciais externas.
- Gerar dados determinísticos ou previsíveis para demonstração e testes.
- Produzir eventos com is_mock=true, persistido em Event.
- Atender ao mesmo contrato dos providers reais.
- Permitir validar deduplicação em coletas repetidas.

GNews ou equivalente e X Provider real podem coexistir com os mocks quando
viáveis sem comprometer a execução local. Não torne integrações reais requisito
de conclusão do MVP. Respeite os valores de source definidos na arquitetura;
não invente novos valores sem explicitar a decisão necessária.

Cada coleta deve tentar todos os providers configurados para todas as empresas
vinculadas à análise. Falhas não devem interromper as demais tentativas nem desfazer
eventos persistidos com sucesso por outros providers.

A resposta deve informar o status por fonte e distinguir sucesso total, sucesso
parcial e falha total. Adote somente o contrato necessário, sem criar um sistema
de jobs, filas ou histórico de execução não previsto.

O período padrão de coleta permanece pendente enquanto o grupo não o confirmar.
Não transforme a proposta de 7 dias em regra definitiva silenciosamente.

6. TIMELINE

Implemente:
- Eventos apenas das empresas vinculadas à análise.
- Filtros por empresa, fonte e período.
- Ordenação published_at DESC.
- Desempate por collected_at DESC.

Paginação não é necessária no MVP. Respeite UTC internamente e deixe conversão
para horário local para a apresentação. Não invente política avançada de timezone.

7. WEB UI OBRIGATÓRIA: JINJA2, TAILWIND CSS E HTMX

Implemente a Web UI server-rendered pelo próprio FastAPI com Jinja2, HTML5,
Tailwind CSS, HTMX desde o início e JavaScript vanilla apenas quando necessário.
A stack está confirmada: não a trate como pendência nem limite a entrega ao backend.
Não existe aplicação frontend independente nem SPA.

A interface deverá:
- Listar e criar análises.
- Visualizar uma análise.
- Adicionar e remover concorrentes.
- Editar perfil básico e search_term, respeitando Company compartilhada.
- Executar coleta e apresentar seu resultado, incluindo falhas parciais.
- Visualizar timeline e aplicar filtros por empresa, fonte e período.
- Distinguir visualmente eventos mockados, sem apresentá-los como fatos reais.
- Apresentar estados de carregamento, vazio e erro.
- Preservar as abas Monitoramento e Perfil da empresa, navegação por teclado,
  foco visível e responsividade previstos na arquitetura.

Jinja2:
- Usar base.html como layout principal.
- Reutilizar templates/partials quando reduzirem duplicação real.
- Usar HTML semântico, labels adequados e textos de interface em português.
- Receber dados preparados pelas rotas/services, sem regras de negócio nos templates.
- Templates não consultam o banco diretamente.

HTMX:
- Usar interações localizadas especialmente para executar coleta, atualizar timeline,
  aplicar filtros, adicionar/remover concorrentes e atualizar partes da interface.
- Web Routes podem retornar fragments/partials Jinja2; não montar HTML em strings Python.
- Preservar feedback de carregamento, erro e resultado nas atualizações parciais.
- Navegação tradicional e formulários HTML continuam válidos quando mais simples.
- Não simular uma SPA nem criar gerenciamento complexo de estado no navegador.

Tailwind e assets:
- Compilar Tailwind CSS para CSS estático com a ferramenta mínima necessária.
- Servir arquivos estáticos pelo FastAPI e disponibilizar HTMX como asset local.
- Garantir demonstração sem dependência de CDN em runtime.
- Se Node.js for necessário apenas para compilar assets, ele não é runtime da
  aplicação nem componente de sua arquitetura. Evitar pipeline frontend complexo.

Priorize uma interface simples e demonstrável, com navegação por teclado, foco
visível, labels, responsividade, estados de carregamento/vazio/erro e indicação
explícita de conteúdo mockado. Não invente um design system complexo.

8. TESTES E VALIDAÇÃO

Preserve os testes existentes e acrescente cobertura funcional para:
- TARGET único por análise.
- Criação sem concorrentes e concorrente adicionado posteriormente.
- Perfil opcional e fallback de search_term.
- Comparação mínima de sites e Company compartilhada.
- Deduplicação de eventos.
- Persistência de is_mock.
- Timestamps com timezone/UTC.
- Ordenação da timeline e desempate.
- Filtros e exclusão de eventos de empresas fora da análise.
- Tentativas de todos os providers para todas as empresas vinculadas.
- Sucesso total, falha parcial e falha total dos providers.
- Persistência dos resultados bem-sucedidos apesar de falhas em outras fontes.
- Fluxo principal da criação da análise até a consulta da timeline.

Inclua testes da Web UI para:
- Web Routes críticas: status HTTP e conteúdo essencial renderizado.
- Fragmentos HTMX principais do fluxo.
- Criação e consulta de análise pela interface, exercitando formulários e Web Routes.
- Apresentação explícita dos eventos mockados.

Testes E2E de navegador não são requisito obrigatório do MVP. Isso não dispensa
a validação local do fluxo da Web UI nem os testes de rotas e fragmentos.

Utilize mocks para fontes externas. Não trate sessões de banco simuladas ou testes
mockados como evidência de integração real com PostgreSQL. Use ambiente de teste
isolado para validar persistência e migrações, preservando dados locais existentes.

Execute e registre, a partir de backend/:
- uv sync --locked
- uv run --locked pytest -q
- uv run --locked ruff check .
- uv run --locked ruff format --check .
- uv run --locked alembic upgrade head

Execute as demais validações locais possíveis, incluindo o fluxo com PostgreSQL
real e providers mockados, e o fluxo completo pela Web UI. Registre resultados
observados, limitações e validações não executadas. Não invente evidências.

9. ESCOPO PROIBIDO

Não implemente:
- React, Vue, Next.js, SPA ou aplicação frontend independente.
- Mapa Competitivo.
- Crawling.
- Perfil automático.
- Descoberta ou classificação automática de concorrentes.
- IA generativa ou enriquecimento por IA.
- Alertas ou scheduler.
- Workers ou filas.
- Autenticação, autorização ou entidades de usuário.
- Funcionalidades V2–V5.

Mantenha a solução pequena e proporcional ao MVP. Execução local é requisito;
deploy permanece fora do escopo.

10. CRITÉRIO DE ACEITE

Só considere o MVP funcional quando for possível demonstrar:
Analista acessa a Web UI → cria análise → informa exatamente um TARGET
→ adiciona ao menos um COMPETITOR → executa coleta mockada ou real
→ eventos são persistidos → timeline é apresentada e filtrável.

Perfil manual e search_term continuam opcionais. Os filtros previstos devem
estar disponíveis. Health checks e banco funcionando isoladamente não satisfazem
o critério. A REST API permanece parte da entrega, mas uma API isolada sem Web UI
não satisfaz o MVP definido. Não declare conclusão sem comprovar esse fluxo.

11. DOCUMENTAÇÃO

Após implementar, atualize somente a documentação afetada pelo estado real:
- Instalação e pré-requisitos.
- Configuração e variáveis de ambiente, sem segredos.
- Execução do banco e da aplicação FastAPI que serve Web UI e REST API.
- Compilação do Tailwind e disponibilização local dos assets, incluindo HTMX.
- Execução de migrações.
- Execução de testes e verificações.
- Configuração e uso do modo mock.
- Roteiro de demonstração do fluxo principal.

Use comandos efetivamente disponíveis e registre o que foi validado.
Nunca marque como implementado algo não validado; diferencie código escrito,
comportamento verificado, partes planejadas e bloqueios.
Não reescreva decisões arquiteturais para encobrir desvios de implementação.

12. EXECUÇÃO E RELATÓRIO FINAL

Não faça commit ou push.

Não tratar frontend como pendência. Continuam abertas decisões como período
padrão da coleta, provider real definitivo de notícias, viabilidade do X real,
contratos/validações ainda não definidos e cenário final da demonstração.
Nenhuma dessas pendências deve impedir o fluxo mockado local: implemente os
contratos mínimos necessários coerentes com as regras confirmadas e registre
as escolhas técnicas, sem apresentá-las como novas decisões de produto do grupo.
Para demonstrar coleta por período, use um período informado explicitamente,
sem fixar silenciosamente um padrão ainda não aprovado. Utilize dados mockados
previsíveis sem tornar o cenário de exemplo uma escolha definitiva do grupo.

Se surgir um impedimento real de ambiente, informe-o e conclua as partes
independentes, sem inventar resultados ou encerrar prematuramente o trabalho.

Ao finalizar, informe:
1. Arquivos criados/alterados.
2. Funcionalidades implementadas.
3. Testes e comandos executados.
4. Resultados observados.
5. Partes do critério de aceite atendidas.
6. Pendências/bloqueios.
7. Decisões que ainda dependem do grupo.
```
