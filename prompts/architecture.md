# Prompts de arquitetura

Prompts usados para revisar e evoluir o `docs/arquitetura.md` a partir do estado do repositório no commit `4081642` (estrutura inicial). Ferramentas: **Claude Code** (Claude Opus 5.5) e **Mermaid** para os diagramas, validados com `@mermaid-js/mermaid-cli`.

| # | Etapa | Resultado |
| --- | --- | --- |
| 1 | Revisão do repositório | Lacunas em relação ao enunciado e ao modelo |
| 2 | Comparação com o Mapa competitivo | 16 funcionalidades ausentes no MVP do repositório |
| 3 | Incorporação do Mapa competitivo | Arquitetura unindo Monitoramento e Mapa competitivo |
| 4 | Simplificação para MVP | 6 entidades e 11 endpoints |
| 5 | Revisão dos métodos HTTP | `PUT` para dados e `POST` para ações, sem `PATCH` |
| 6 | Seleção de empresas monitoradas | Seção 7.1, `search_term` e rota para remover concorrente |
| 7 | Revisão de escopo | Mapa competitivo removido; MVP com perfil básico manual, 4 entidades e 9 endpoints |

---

## 1. Revisão do repositório

```text
O repositório https://github.com/bisb-inc/bisb é a versão mais atual do projeto.
Leia docs/arquitetura.md e todos os arquivos que ele referencia
(competitive_monitor_mvp.md, README.md, .ai/ e prompts/).

Avalie o docs/arquitetura.md contra o enunciado da atividade, que pede:
funcionalidades principais, tipos de usuários e permissões, diagrama de arquitetura
por camadas, entidades e relacionamentos, endpoints REST, tecnologias sugeridas,
fluxos principais e os prompts utilizados com a ferramenta.

Entregue:
1. Uma tabela com cada item do enunciado, sua situação no documento e uma sugestão.
2. Problemas técnicos no modelo de dados e na API (chaves, duplicidade, filtros,
   rotas que faltam, tratamento de falhas).
3. Inconsistências entre os arquivos do repositório.

Valide a sintaxe dos diagramas Mermaid. Não altere nem commite nada nesta etapa.
```

## 2. Comparação com o Mapa competitivo

```text
O docs/arquitetura.md do GitHub está simples demais, e o nosso documento local do
Mapa competitivo (atualizacoes_mapa_competitivo.md) está complexo demais. Queremos
chegar a um meio-termo.

Liste, em uma tabela, cada funcionalidade do atualizacoes_mapa_competitivo.md que
não está no MVP do GitHub, indicando onde ela aparece hoje na proposta
(fora do MVP, evolução futura ou ausente).

Aponte também o caminho inverso: o que o GitHub tem que o documento local não tem.
Termine com uma proposta de meio-termo, separando o que entra, o que é opcional e o
que fica para depois do MVP.
```

## 3. Incorporação do Mapa competitivo

```text
Decisão: tudo o que está no atualizacoes_mapa_competitivo.md precisa fazer parte do
MVP do GitHub, sem perder o que já existe (análises, coleta de notícias e X, timeline).

Atualize o docs/arquitetura.md para unir os dois módulos, Monitoramento e
Mapa competitivo, cobrindo todos os itens do enunciado. Regras:
- Mostre como os módulos se conectam: uma candidata aprovada vira COMPETITOR da
  análise e passa a aparecer na timeline.
- Preserve os nomes técnicos existentes (Analysis, Company, AnalysisCompany, Event).
- Mantenha a arquitetura simples: sem filas, cache ou workers.
- Não apresente decisões pendentes (stack, período de coleta) como tomadas.

Depois, alinhe README.md, .ai/architecture.md, .ai/business-rules.md, os READMEs de
backend e frontend e a seção 4 da proposta, para que nenhum arquivo continue tratando
essas funcionalidades como futuras. Não altere a evolução futura nem a divisão do grupo:
apenas aponte o que precisa ser decidido. Valide os diagramas e não commite.
```

## 4. Simplificação para MVP

```text
O documento ficou grande demais. Revise entidades e endpoints com foco no MVP:
nem o mínimo do GitHub, nem tudo o que é possível.

Nenhuma funcionalidade do Mapa competitivo pode ser perdida, mas cada entidade e
cada endpoint precisa justificar sua existência:
- Junte entidades com estrutura quase igual (por exemplo, fontes do perfil e
  evidências das candidatas).
- Transforme em colunas o que for 1:1 e não tiver ciclo de vida próprio
  (perfil, decisão).
- Agrupe endpoints que fazem a mesma operação sobre o mesmo recurso.
- Explique cada simplificação em uma linha.

Atualize os arquivos de .ai/ afetados e mostre uma tabela de antes e depois com o
número de entidades, endpoints e diagramas.
```

## 5. Revisão dos métodos HTTP

```text
Avalie se o uso de PATCH faz sentido na API. Hoje um mesmo PATCH edita dados e
também muda status com regra de negócio (confirmar perfil, aprovar ou rejeitar).

Proponha e aplique uma convenção única para o documento:
- qual método edita dados;
- como expor ações com regra de negócio de forma explícita;
- quais erros cada ação retorna (por exemplo, 409 para candidata já decidida).

Mantenha a convenção coerente com as rotas que já existem (/collect, /map) e
registre-a no docs/arquitetura.md, logo abaixo da tabela de endpoints.
```

## 6. Seleção de empresas monitoradas

```text
O documento não deixa claro como o usuário escolhe quais empresas serão monitoradas
nem o que o sistema usa para buscar. Explique isso no docs/arquitetura.md, em uma
seção de fluxo, cobrindo:
1. O que o usuário informa ao criar a análise (tabela de campos, obrigatórios e
   exemplos) e um exemplo de requisição JSON com o cenário da proposta
   (Nubank, Inter, C6 Bank).
2. Como adicionar e remover concorrentes depois, inclusive pela aprovação no mapa.
3. Qual termo é usado na busca de notícias e X, e como evitar nomes ambíguos
   (por exemplo, "Inter").
4. A diferença entre a busca da coleta (por empresa) e a do mapa (pelo perfil).

Ajuste o modelo e os endpoints somente se for necessário, e deixe como pendente o
que ainda depende do grupo (período padrão da coleta).
```

## 7. Revisão de escopo

```text
Ao incluir todo o atualizacoes_mapa_competitivo.md, passamos a contradizer a seção 4
da proposta (escopo fora do MVP). Como o Mapa competitivo não aparece em nenhum
arquivo do repositório, revise o escopo para ficar só com o que é válido para o MVP.

Decisão: manter apenas o perfil da empresa, preenchido manualmente (mercado,
produtos e público-alvo), sem confirmação, sugestões de concorrentes ou mapa.

Atualize docs/arquitetura.md:
- Remova o Mapa competitivo e as entidades e endpoints ligados a ele.
- Coloque o perfil como campos opcionais da Company, editáveis por um PUT.
- Mantenha a seção 7.1, o search_term, a convenção de métodos e a acessibilidade.

Restaure a seção 4 da proposta com a lista original, indicando que o perfil manual
faz parte do MVP e que só a geração automática fica de fora. Alinhe README.md, .ai/
e os READMEs de backend e frontend. Valide os diagramas e não commite.
```

