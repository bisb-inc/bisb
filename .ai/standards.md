# Padrões de desenvolvimento

Contexto da Aula 2, revisado por inspeção do repositório em 29/09/2026.

## Fontes e limites

A ordem de referência é: [arquitetura oficial](../docs/arquitetura.md), [visão estratégica](../competitive_monitor_mvp.md) e estado real do repositório. A arquitetura define o estado-alvo; o código comprova o estado atual. Os requisitos consolidados pelo [Prompt 1](../prompts/context-generation.md) complementam esse contexto.

Diferencie sempre **já implementado**, **planejado para o MVP** e **roadmap futuro**. Documentação e testes existentes não provam execução bem-sucedida. Registre divergências e pendências em vez de inventar regras.

## Convenções adotadas na base

- Documentação em português; identificadores técnicos e nomes das entidades preservados.
- Python tipado, rotas REST em `app/api/`, configuração em `app/core/` e infraestrutura de persistência em `app/db/`.
- FastAPI com `create_app`, ciclo de vida para o engine e dependência de sessão síncrona encerrada por requisição.
- SQLAlchemy e Alembic compartilham a configuração e o metadata. Migrações são explícitas; não criar tabelas na inicialização da API.
- Configuração por Pydantic Settings: variáveis do processo têm prioridade sobre `backend/.env`. `DATABASE_URL` é obrigatória e usa `postgresql+psycopg://`.
- Preservar segredos fora do versionamento e das mensagens de erro/log. Documentar variáveis em `.env.example` com valores apenas de desenvolvimento.
- Preservar `uv.lock`; não atualizar dependências sem necessidade da tarefa. As versões verificadas estão em [tech-stack.md](tech-stack.md).
- Ruff: Python 3.14, linhas de até 100 caracteres e regras `E, F, I, UP, B`, conforme [pyproject.toml](../backend/pyproject.toml).

## Diretrizes para a implementação planejada

- Rotas cuidam da interface HTTP; regras de negócio coordenam operações; persistência mantém os dados; providers isolam fontes externas.
- Adicionar serviços, modelos e providers quando houver comportamento concreto, sem camadas vazias ou substituição desnecessária da base existente.
- Providers reais e mockados devem atender à mesma abstração e retornar dados normalizados para o domínio. Não propagar contratos externos pelas regras de negócio.
- Identificar eventos simulados por `is_mock`, inclusive na apresentação. Garantir demonstração local com mocks compatíveis quando integrações reais forem inviáveis.
- Preservar resultados de fontes bem-sucedidas quando outra falhar; informar a falha parcial. Os detalhes transacionais e o contrato dessa resposta ainda precisam ser definidos.
- Seguir os endpoints oficiais e as [regras de negócio](business-rules.md). Não adicionar autenticação, workers ou funcionalidades do roadmap.
- Seguir a Web UI server-rendered integrada ao FastAPI, com Jinja2, HTML5, Tailwind CSS e HTMX, conforme a arquitetura oficial e as convenções abaixo.

## Organização da Web UI

Templates Jinja2 e arquivos estáticos pertencem à própria aplicação FastAPI. Não existe frontend independente. Web Routes ficam separadas das REST API Routes; ambas reutilizam `Application / Services`.

Organização conceitual a adaptar à estrutura real durante a implementação:

```text
app/
├── api/
│   └── routes/
├── web/
│   ├── routes/
│   └── templates/
├── services/
├── providers/
├── db/
└── static/
```

Essa organização não exige criar diretórios vazios nem substituir os módulos existentes. Introduzir módulos somente quando houver responsabilidades concretas.

## Separação entre Web Routes, REST API e serviços

- REST API Routes retornam contratos de API; Web Routes retornam páginas completas ou fragmentos HTML.
- Nenhuma das duas concentra a regra de negócio principal: ambas chamam diretamente a mesma camada `Application / Services`.
- Não duplicar regras de negócio entre Web e API.
- Web Routes não fazem chamadas HTTP para a própria REST API apenas para reutilizar lógica.

## Templates Jinja2

- Utilizar `base.html` como layout principal.
- Usar herança, includes e macros somente quando reduzirem duplicação real.
- Templates não contêm regras de negócio; recebem dados já preparados pelas rotas e serviços.
- Evitar consultas ao banco diretamente a partir da camada de apresentação; manter acesso aos dados nas responsabilidades de serviços e persistência.
- Preservar nomes técnicos no código e escrever os textos da interface em português.

## HTMX e JavaScript

Usar HTMX para interações localizadas, como executar coleta, atualizar timeline, aplicar filtros, adicionar/remover concorrentes e atualizar perfil quando isso simplificar a experiência.

- Web Routes HTMX podem retornar fragmentos HTML.
- Respostas parciais reutilizam templates/partials Jinja2; não montar HTML em strings Python.
- Manter o funcionamento compreensível e simples. Preferir navegação tradicional quando ela atender melhor a uma página ou formulário; não usar HTMX apenas por obrigação.
- Não usar HTMX para simular uma SPA nem introduzir estado global complexo no navegador.
- Preferir HTML + HTMX. JavaScript vanilla somente quando necessário, evitando dependências JS adicionais.
- Não introduzir React, Vue, Alpine ou frameworks semelhantes sem nova decisão arquitetural.

## Tailwind CSS e assets

- Usar Tailwind CSS para estilizar a interface e compilá-lo localmente para um asset CSS estático.
- Disponibilizar HTMX como asset local; servir os arquivos estáticos pela aplicação FastAPI.
- Evitar CDN em runtime e dependência de internet para executar a demonstração do MVP com providers mockados.
- Não adicionar framework de componentes ou biblioteca visual sem necessidade. Priorizar classes utilitárias e componentes/templates reutilizáveis quando houver repetição relevante.
- Manter a interface simples e consistente, sem inventar um design system complexo para o MVP.
- Não fixar ferramenta ou versão de build além do que estiver documentado na stack ou no repositório. Utilizar somente a compilação de assets necessária.

## Acessibilidade e UX mínima

- HTML semântico e labels associados aos inputs.
- Navegação por teclado e foco visível.
- Estados de carregamento, vazio e mensagens de erro compreensíveis.
- Responsividade e indicação explícita de conteúdo mockado.
- Interações HTMX devem preservar o feedback de carregamento e erro necessário ao usuário, inclusive nas atualizações parciais.

## Testes e evidências

A base possui testes de configuração, health, readiness simulado e OpenAPI em [backend/tests](../backend/tests). Nesta revisão documental, eles foram inspecionados, não executados.

Na implementação funcional, validar o fluxo de análise até a timeline, TARGET único, concorrentes adicionados depois, perfil opcional, fallback de busca, identificação de mocks, deduplicação, filtros, falha parcial e preservação dos eventos. Tratar estados vazios, carregamento e erro na interface conforme a arquitetura.

Usar mocks para isolar fontes externas nos testes. Validar persistência real separadamente; testes com sessões simuladas não comprovam integração com PostgreSQL. Registrar comandos, resultados e limitações, sem alegar sucesso em verificações não executadas.

Além dos testes de backend, incluir testes básicos das Web Routes críticas, validando status HTTP e conteúdo essencial renderizado. Testar pelo menos os fragmentos HTMX relevantes do fluxo principal. Testes end-to-end de navegador não são condição do MVP, salvo decisão posterior do grupo.

Comandos existentes, a partir de `backend/`:

```text
uv run --locked pytest -q
uv run --locked ruff check .
uv run --locked ruff format --check .
```

## Manutenção do contexto

Atualizar documentação afetada quando a tarefa autorizar mudanças de comportamento. Se o escopo não permitir corrigir um documento, registrar a divergência. Não apresentar funcionalidades planejadas como entregues.
