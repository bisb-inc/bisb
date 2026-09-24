# Regras de negócio do MVP

Baseada na [proposta original](../competitive_monitor_mvp.md), sujeita à revisão pelo grupo.

1. Uma análise contém nome, empresa-alvo e concorrentes informados manualmente.
2. As empresas são cadastradas com nome e site.
3. O vínculo `AnalysisCompany` registra o papel `TARGET` ou `COMPETITOR` da empresa em cada análise.
4. A coleta busca acontecimentos das empresas vinculadas à análise, utilizando seus nomes nas pesquisas.
5. Notícias e publicações são normalizadas para a entidade `Event`, mantendo empresa, fonte, título, descrição, URL e datas de publicação e coleta.
6. A timeline consolida acontecimentos da empresa-alvo e dos concorrentes. Filtros por empresa, fonte e período são desejáveis.
7. O funcionamento do MVP não depende do acesso à API do X; um provider mock pode ser utilizado.
8. Crawling completo, descoberta automática de concorrentes, classificação por IA, alertas e processamento contínuo ficam fora do MVP.

## Detalhes a definir na implementação

- Validações dos campos e cardinalidade mínima de concorrentes.
- Período padrão da coleta e ordenação/paginação da timeline.
- Tratamento de eventos repetidos e falhas parciais dos providers.
- Identificação dos eventos mockados no contrato da API e na interface.
