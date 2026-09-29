# Competitive Monitor

MVP de monitoramento competitivo para acompanhar uma empresa e seus concorrentes em uma timeline única, reunindo notícias e publicações do X/Twitter.

O projeto está na etapa de organização inicial. A aplicação ainda não foi implementada e a stack será definida pelo grupo.

## Escopo do MVP

- Criar análises com nome, empresa-alvo, site e concorrentes informados manualmente.
- Coletar notícias com GNews ou um provider equivalente.
- Coletar publicações do X ou utilizar dados mockados quando necessário.
- Normalizar e persistir os acontecimentos.
- Exibir uma timeline comparativa, com filtros desejáveis por empresa, fonte e período.
- Preencher manualmente o perfil básico das empresas: mercado, produtos e público-alvo.

## Estrutura

```text
.
├── .ai/
│   ├── standards.md
│   ├── architecture.md
│   ├── tech-stack.md
│   └── business-rules.md
├── backend/
│   └── README.md
├── frontend/
│   └── README.md
├── docs/
│   └── arquitetura.md
├── prompts/
│   ├── architecture.md
│   ├── context-generation.md
│   └── implementation.md
├── competitive_monitor_mvp.md
└── README.md
```

## Documentação

- [Proposta original](competitive_monitor_mvp.md)
- [Arquitetura inicial](docs/arquitetura.md)
- [Contexto de arquitetura para IA](.ai/architecture.md)
- [Regras de negócio](.ai/business-rules.md)
- [Padrões de desenvolvimento](.ai/standards.md)
- [Definição da stack](.ai/tech-stack.md)
- [Backend](backend/README.md) e [frontend](frontend/README.md)
- Prompts de [arquitetura](prompts/architecture.md), [geração de contexto](prompts/context-generation.md) e [implementação](prompts/implementation.md)

## Próximos passos

1. Revisar o escopo e os documentos iniciais com o grupo.
2. Escolher a stack e registrar as decisões em `.ai/tech-stack.md`.
3. Implementar as entidades e os endpoints do backend.
4. Implementar os providers de notícias e X/mock.
5. Implementar o frontend e validar o fluxo completo.

Os comandos de instalação, execução e testes serão documentados após a criação das aplicações.
