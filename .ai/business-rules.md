# Regras de negócio — MVP funcional

Fontes: [arquitetura oficial da Aula 1](../docs/arquitetura.md), [discovery e roadmap](../competitive_monitor_mvp.md) e requisitos confirmados no [Prompt 1 da Aula 2](../prompts/context-generation.md). As regras definem o produto; o estado atual da implementação é documentado no [README principal](../README.md) e no [backend/README.md](../backend/README.md).

## Produto e usuário

O Competitive Monitor consolida notícias e publicações do X/Twitter sobre uma empresa-alvo e concorrentes em uma timeline comparativa.

A hipótese do MVP é que uma lista manual de empresas permite coletar, normalizar, persistir e comparar acontecimentos de fontes diferentes. A solução permanece pequena, sem depender de integrações reais para a demonstração.

O único perfil funcional é **Analista**, que cria/consulta análises, cadastra/adiciona/remove concorrentes, edita perfil básico e termo de busca, executa coleta e consulta/filtra a timeline. Não há autenticação, autorização, múltiplos níveis de acesso ou entidades de usuário.

## Entidades e papéis

| Entidade | Conceito e dados definidos na arquitetura |
| --- | --- |
| Analysis | Análise competitiva: id, nome e data de criação |
| Company | Empresa: id, nome, site, search_term e perfil manual opcional (market, products, audience) |
| AnalysisCompany | Vínculo entre análise e empresa, com analysis_id, company_id e role |
| Event | Acontecimento: id, company_id, source, title, description, url, is_mock, published_at e collected_at |

- Uma análise possui exatamente uma empresa `TARGET`.
- `TARGET` e `COMPETITOR` pertencem a `AnalysisCompany.role`; não existe `Company.type` para esses papéis.
- Uma empresa pode participar de várias análises com papéis diferentes e possuir vários eventos.
- Concorrentes são definidos manualmente e podem ser adicionados ou removidos depois da criação.
- A criação inicial admite ausência de concorrentes; o fluxo competitivo completo exige ao menos um `COMPETITOR`. Não impor esse critério como obrigatoriedade no cadastro inicial.
- Reaproveitar a empresa identificada pelo mesmo site, conforme a regra mínima de comparação abaixo, sem fusão automática em caso de conflito ou ambiguidade.
- Nome e site são informados no cadastro. Mercado, produtos e público-alvo são opcionais e preenchidos/editados manualmente.
- `search_term` é opcional e usa `Company.name` como fallback.
- O perfil não exige confirmação nem bloqueia a coleta.

## Decisões mínimas de implementação

### Identificação por site

O site é utilizado para identificar e reaproveitar empresas quando disponível. A comparação ignora diferenças triviais de protocolo (`http/https`), barra final e prefixo `www`. Outras regras de canonicalização ficam fora do MVP.

Se houver conflito ou ambiguidade, não fundir empresas automaticamente. Essa comparação não altera os campos exigidos no cadastro pela arquitetura oficial.

### Company compartilhada entre análises

Alterações em nome, site, `search_term` ou perfil básico afetam a mesma `Company` em todas as análises em que ela participa. Frontend e API devem tratar `Company` como entidade compartilhada, não como cópia por análise. Não há versionamento nem histórico de perfil no MVP.

### Datas

Datas persistidas devem representar timestamps com timezone. A API trabalha de forma consistente com UTC internamente; a conversão para horário local é responsabilidade da apresentação/frontend. Não há política avançada de timezone no MVP.

### Coleta e providers

1. O analista aciona a coleta, que deve tentar todos os providers configurados para todas as empresas vinculadas à análise.
2. A busca utiliza o `search_term` de cada empresa ou seu nome.
3. Prever provider de notícias GNews ou equivalente, provider do X se viável e providers mockados compatíveis.
4. Os providers retornam dados normalizados para o domínio. Contratos externos ficam isolados das regras de negócio.
5. Persistir os resultados como `Event`, preservando origem, empresa, URL e datas.
6. Eventos simulados devem persistir `is_mock=true` no `Event`, ser claramente identificáveis na interface e nunca ser apresentados como acontecimentos reais.
7. Aplicar deduplicação básica por `(company_id, source, url)`.
8. Se um provider falhar, continuar as demais tentativas e preservar os resultados das fontes bem-sucedidas. A falha não deve desfazer eventos persistidos com sucesso por outros providers.
9. A resposta informa o status por fonte e permite distinguir sucesso total, sucesso parcial e falha total. O schema HTTP detalhado permanece a definir.

As fontes previstas são `GNEWS` e `X` conforme a arquitetura. Se for escolhido outro provider de notícias, o mapeamento de fonte deve ser definido antes da implementação dependente; não inventar novos valores silenciosamente.

Credenciais, custo ou indisponibilidade externa não podem impedir a demonstração: deve existir alternativa mock compatível. O contrato detalhado dos providers e a seleção do modo real/mock ainda precisam ser especificados.

### Timeline e interface

A timeline reúne eventos das empresas vinculadas à análise, com filtros por empresa, fonte e período. Empresas fora da lista não aparecem na timeline da análise.

A ordenação padrão é `published_at DESC`, com desempate por `collected_at DESC`. Não é necessário implementar paginação no MVP; sua adoção futura permanece em aberto.

As abas Monitoramento e Perfil da empresa devem permitir os fluxos previstos, incluindo acessibilidade por teclado, foco visível, responsividade e estados de carregamento, vazio e erro. Dados simulados precisam ser reconhecíveis na apresentação.

O período padrão permanece pendente: 7 dias é proposta, não regra definitiva.

## Critério de aceite

O MVP funcional é considerado concluído quando o analista consegue criar uma análise, informar empresa-alvo e ao menos um concorrente, executar uma coleta com providers reais ou mockados, persistir os eventos e consultar a timeline.

O perfil manual e `search_term` são opcionais e não bloqueiam esse fluxo. A timeline deve permitir os filtros definidos acima. Health checks ou integração ao banco isoladamente não satisfazem o critério funcional.

## Extensão opcional posterior ao MVP base: análise de eventos por IA

O enriquecimento individual de `Event` é uma extensão implementada posteriormente, não requisito do critério de aceite original. A saída é armazenada em `EventAnalysis`, separada do acontecimento coletado. A análise é solicitada pelo Analista para um evento persistido, nunca durante a coleta ou carregamento da timeline.

`EventAnalysis` é 1:1 com `Event` e contém resumo, categoria, intensidade de impacto competitivo, sentimento, relevância de 0 a 100, justificativa, provider, modelo, `is_mock` e timestamps. Categorias: `PRODUCT`, `PRICING`, `PARTNERSHIP`, `EXPANSION`, `FINANCIAL_RESULTS`, `REGULATORY`, `M_AND_A`, `PEOPLE`, `TECHNOLOGY`, `OTHER`. Impacto: `LOW`, `MEDIUM`, `HIGH` (intensidade, sem direção). Sentimento: `NEGATIVE`, `NEUTRAL`, `POSITIVE`.

O resultado existente é reutilizado por padrão. Reanálise exige ação explícita; a atualização ocorre somente após resposta validada, preservando o resultado anterior em caso de falha. Gemini usa saída estruturada validada por schema. `ANALYSIS_PROVIDER=gemini` sem `GEMINI_API_KEY`, ou com erro de provider/validação, retorna erro controlado sem fallback simulado. `ANALYSIS_PROVIDER=mock` seleciona saída determinística identificada como simulada. Essa extensão não altera `Event` nem depende da coleta.

## Fora do MVP base e roadmap

Mapa Competitivo, crawling completo, geração automática de perfil, descoberta e classificação de concorrentes, análise em lote, alertas, workers, filas, processamento contínuo, autenticação e autorização.

Enriquecimento automático do perfil, descoberta/classificação, outras funcionalidades de IA e monitoramento contínuo pertencem às versões futuras. O perfil manual já pertence à V1; o enriquecimento individual de eventos descrito acima é opcional e posterior ao MVP base.

## Pendências que podem permanecer abertas

- Período padrão de coleta.
- Escolha definitiva e viabilidade dos providers reais.
- Detalhes exatos dos corpos/respostas HTTP, incluindo a representação dos resultados da coleta.
- Limites de quantidade de empresas.
- Política para coletas concorrentes.
- Paginação futura, não exigida no MVP.
- Cenário final da demonstração.

Essas pendências não bloqueiam o avanço das partes independentes da implementação; decisões necessárias a uma etapa específica devem ser explicitadas antes do trabalho dependente. Não inventar políticas nem tratar como pendentes as regras já fechadas de ordenação, UTC, comparação mínima de sites, Company compartilhada, deduplicação, falha parcial, identificação dos mocks e cardinalidade do fluxo de aceite.
