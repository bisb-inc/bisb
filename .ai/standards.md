# Padrões de desenvolvimento

Base inicial para revisão pelo grupo. Padrões específicos de linguagem, formatação e ferramentas serão definidos após a escolha da stack.

- Manter as entregas focadas no MVP descrito em [competitive_monitor_mvp.md](../competitive_monitor_mvp.md).
- Utilizar português na documentação e preservar os nomes técnicos de entidades e endpoints da proposta.
- Separar interface, regras de negócio, persistência e integração com fontes externas.
- Encapsular cada fonte externa em um provider e normalizar os resultados para `Event`.
- Manter credenciais fora do código e do versionamento; documentar as variáveis necessárias quando as integrações forem implementadas.
- Identificar dados mockados na demonstração.
- Documentar instalação, execução e testes conforme cada componente for implementado.
- Validar o fluxo principal, estados vazios e falhas das fontes externas.
- Atualizar a documentação quando decisões de implementação alterarem a proposta inicial.
