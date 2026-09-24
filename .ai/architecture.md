# Contexto de arquitetura

A arquitetura proposta é composta por frontend, backend REST, banco de dados e providers de fontes externas.

- **Frontend:** criação de análises, cadastro de empresas e concorrentes, acionamento da coleta e apresentação da timeline.
- **Backend:** regras de negócio, endpoints REST, persistência e orquestração da coleta.
- **Providers:** busca por empresa em GNews ou equivalente e no X, com alternativa mock para o X.
- **Persistência:** entidades `Analysis`, `Company`, `AnalysisCompany` e `Event`.

O papel `TARGET` ou `COMPETITOR` pertence ao vínculo `AnalysisCompany`, conforme o modelo de dados da seção 7 da proposta. Assim, o papel da empresa depende da análise.

A coleta é acionada pelo usuário. Agendamento contínuo, descoberta automática de concorrentes e classificação por IA pertencem a versões futuras.

Consulte [docs/arquitetura.md](../docs/arquitetura.md) para os diagramas, o modelo inicial e os endpoints propostos. A stack está pendente em [tech-stack.md](tech-stack.md).
