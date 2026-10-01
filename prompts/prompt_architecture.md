# Prompts de arquitetura — Aula 1

Os prompts abaixo são **consolidações retrospectivas das interações realizadas**:
preservam a intenção e as decisões dos principais checkpoints, sem constituir
transcrições literais completas ou um log de todas as tentativas.

Ferramentas utilizadas:

- **ChatGPT** — discovery do produto, exploração de alternativas, redução de escopo e estruturação inicial.
- **Codex** — inspeção do repositório, identificação de inconsistências e consolidação técnica da arquitetura.
- **Mermaid** — representação dos diagramas.

## 1. Exploração de ideias de sistema

**Ferramenta:** ChatGPT.

```text
Com base no exercício de arquitetura proposto pelo professor e no exemplo da
GNews API, sugira alternativas de sistemas que permitam trabalhar funcionalidades,
usuários, arquitetura, entidades, endpoints REST, tecnologias e fluxos principais.
```

## 2. Definição do domínio

**Ferramenta:** ChatGPT.

```text
Quero focar em um sistema de monitoramento competitivo de empresas. Estruture a
ideia considerando empresa-alvo, mercado de atuação, posicionamento, produtos,
proposta de valor, concorrentes e monitoramento de acontecimentos relevantes.
```

## 3. Redução do escopo para MVP

**Ferramenta:** ChatGPT.

```text
Considerando as funcionalidades discutidas pelo grupo e os requisitos do trabalho,
reduza significativamente o escopo para um MVP demonstrável. O foco inicial deve
ser acompanhar empresa-alvo e concorrentes por notícias e publicações no
X/Twitter, deixando funcionalidades avançadas como roadmap.
```

## 4. Estruturação da arquitetura

**Ferramentas:** ChatGPT + Mermaid.

```text
Organize o MVP definindo funcionalidades essenciais, funcionalidades fora do
escopo, roadmap, arquitetura inicial, entidades, endpoints REST, tecnologias e
fluxos principais, mantendo a solução pequena o suficiente para implementação
com agentes de IA.
```

## 5. Revisão e consolidação técnica

**Ferramentas:** Codex + Mermaid.

```text
Inspecione o estado atual do repositório e revise docs/arquitetura.md contra os
requisitos da atividade. Identifique inconsistências entre proposta, entidades,
endpoints e arquivos .ai/; preserve o escopo reduzido do MVP e consolide uma
arquitetura coerente e implementável.
```

Os refinamentos posteriores esclareceram e consolidaram:

- `TARGET` e `COMPETITOR` em `AnalysisCompany.role`, definindo o papel da empresa por análise.
- `search_term` para a coleta, com o nome da empresa como padrão.
- `is_mock` para identificar eventos mockados.
- Deduplicação básica de eventos por `(company_id, source, url)`.
- Continuidade da coleta em caso de falha parcial dos providers, informando o status de cada fonte.
- Perfil básico manual e opcional: mercado, produtos e público-alvo.
- Critério de aceite: criar uma análise com empresa-alvo e ao menos um concorrente,
  executar coleta real ou mockada, persistir eventos e consultar a timeline.

A arquitetura final está registrada em [docs/arquitetura.md](../docs/arquitetura.md).

## Encerramento

Este arquivo documenta os principais prompts utilizados na **definição da arquitetura
da Aula 1**. [context-generation.md](context-generation.md) e
[implementation.md](implementation.md) são os dois prompts específicos da **Aula 2**.

Detalhes intermediários descartados, como experimentações com Mapa Competitivo, não
representam o escopo final e não são apresentados como etapas centrais da solução.

