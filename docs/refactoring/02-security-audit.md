# Refactoring — Auditoria de segurança

Auditoria executada na branch `refactor/felipe-core`, sobre o código já desacoplado, conforme a seção 8 do plano de refactoring. Registra as verificações sem achado e o achado corrigido.

## Resumo

| Área | Resultado |
| --- | --- |
| Segredos versionados | Nenhum encontrado |
| `.env` e `.env.example` | `.env` ignorado; exemplo só com valores de desenvolvimento |
| `SecretStr` e logs | Segredos tipados e mascarados; sem vazamento em logs ou respostas |
| URLs e mensagens de providers | Chave do GNews fora da URL; erros externos genéricos |
| SQL | Sem SQL concatenado |
| Templates e links | **1 achado corrigido:** links com esquema `javascript:` |
| Dependências Python e npm | Nenhuma vulnerabilidade conhecida |
| Docker | Sem segredos na imagem; usuário não-root; portas apenas em `127.0.0.1` |
| Tratamento de exceções | Mensagens controladas; sem stack trace na resposta |

## Verificações sem achado

- **Segredos no histórico:** `git log --all -p` procurado por padrões de chave (`AIza…`, `sk-…`, `ghp_…`, chaves privadas PEM, `GNEWS_API_KEY=`/`GEMINI_API_KEY=` com valor); nenhuma ocorrência. Os valores reais das chaves do `backend/.env` local foram buscados literalmente em todo o histórico (`--all --reflog`) e no stash, sem exibi-los: 0 ocorrências.
- **`.env`:** `backend/.env` é ignorado (`.gitignore`: `.env`, `.env.*`, exceto `.env.example`) e excluído do contexto Docker (`.dockerignore`). `backend/.env.example` contém apenas a senha de desenvolvimento `local_dev_only` e chaves vazias.
- **`SecretStr`:** `DATABASE_URL`, `GNEWS_API_KEY` e `GEMINI_API_KEY` são `SecretStr` em `Settings`, com `hide_input_in_errors=True`. O engine usa `hide_parameters=True`, então parâmetros SQL não aparecem em logs de erro.
- **Logs:** `collection.py` registra fonte e id da empresa com `logger.exception`; a mensagem devolvida ao cliente é genérica. O readiness registra apenas "Banco indisponível". Os testes `test_gnews_preserves_transport_errors_without_exposing_key`, `test_gemini_provider_error_does_not_expose_key` e `test_readiness_failure_does_not_leak_details` cobrem esses pontos.
- **URLs de providers:** a chave do GNews vai no header `X-Api-Key`, nunca na query (`test_gnews_*`). A chave da Gemini é usada só na criação do cliente e não entra no prompt (`test_gemini_uses_structured_schema_with_mock_client`).
- **Mensagens externas:** falhas de provider viram `"Não foi possível consultar ou persistir os resultados desta fonte."` na coleta e `"O provider de análise não conseguiu gerar um resultado válido."` na análise de evento; `GeminiAnalysisProvider` relança com `from None` para não encadear a resposta do provider (`test_rest_collection_contract_reports_each_pair` confirma que o texto da exceção do provider não chega à resposta).
- **SQL:** todas as consultas usam expressões SQLAlchemy parametrizadas. Os únicos `text()` são literais fixos: `SELECT 1` no readiness e `role = 'TARGET'` no índice parcial (modelo e migração).
- **Templates:** autoescape do Jinja2 ativo (`Jinja2Templates` com extensão `.html`); nenhum `|safe`, `Markup` ou `autoescape false`. O rascunho do wizard é serializado com `tojson|forceescape` em atributo. `HX-Push-Url` é montado com `urlencode`, que codifica CR/LF.
- **Entrada:** `CompanyInput.model_dump()` só expõe os campos declarados ao criar `Company`. `wizard_state` é lido com `json.loads` e rejeitado com 400 quando não é objeto.
- **Dependências:**
  - `npm audit` → `found 0 vulnerabilities` (também com `--omit=dev`).
  - Python: `uvx pip-audit -r <export>` sobre as 49 dependências fixadas por `uv export --locked --all-groups --no-hashes --no-emit-project` → `No known vulnerabilities found` (pip-audit 2.10.1). Executado de forma efêmera, sem alterar `pyproject.toml` ou `uv.lock`.
- **Docker:** imagem multi-stage; `uv sync --locked --no-dev`; processo como `appuser` (uid 10001); `.env` e `tests/` fora do contexto. O Compose publica app e banco apenas em `127.0.0.1`. Credenciais do banco vêm do `.env` local.
- **Superfície das rotas:** não há autenticação nem sessão por decisão de escopo (ADR-001 e regras de negócio), portanto não há credenciais ambientes para CSRF explorar. `/docs` permanece exposto como parte do MVP.

## Achado corrigido — esquemas executáveis em links

- **Problema:** `workspace/companies.html` renderizava `href="{{ company.website }}"` e `partials/timeline.html` renderizava `href="{{ event.url }}"`. O autoescape impede a quebra do atributo, mas não bloqueia esquemas como `javascript:`. `Company.website` aceita qualquer texto pela REST API e pela Web UI, que não têm autenticação; `Event.url` vem de provider externo. Um valor `javascript:…` executava script no domínio da aplicação ao clicar no link (CWE-79, XSS armazenado por esquema de URL).
- **Evidência:** um teste exploratório criou a empresa com site `javascript:alert(document.domain)` e um evento com `url="javascript:alert(1)"`; as views Empresas e Timeline continham `href="javascript:alert(document.domain)"` e `href="javascript:alert(1)"`.
- **Correção:** filtro Jinja `safe_href` registrado no ambiente de templates da Web (`app/web/routes.py`; após a integração com a Web Layer, `app/web/templating.py`) e aplicado aos quatro links dinâmicos. O filtro mantém valores com esquema `http`, `https` ou sem esquema e troca qualquer outro por `#`. Antes de identificar o esquema, remove espaços e caracteres de controle, que os navegadores ignoram (`java\tscript:`). Valores que `urlsplit` não interpreta também viram `#`.
- **Comportamento preservado:** links `http(s)` e sites sem esquema (`alfa.example`) são emitidos exatamente como antes; nenhuma URL, rota, template novo ou classe CSS mudou. O CSS compilado permanece idêntico. Único efeito em entrada legítima rara: um site sem esquema com porta (`alfa.example:8080`) é interpretado pelo `urlsplit` como esquema `alfa.example` e passa a `#`; antes o navegador também o tratava como esquema desconhecido.
- **Testes:** `tests/test_security_links.py` — 8 variações inseguras (`javascript:` com caixa mista, espaço inicial, tab, quebra de linha e caractere de controle; `data:`; `vbscript:`) e 3 casos de preservação. Sem a correção: 8 falhas e 3 aprovações; com a correção: 11 aprovações.
- **Validação:** `pytest -q` → 176 passed, 1 skipped; teste PostgreSQL opt-in → 1 passed; `ruff check`, `ruff format --check` e `alembic check` sem apontamentos; `npm run build` com `app.css` e `htmx.min.js` idênticos aos versionados.

## Fora do escopo desta auditoria

- Validar o formato de `website` na entrada (por exemplo, aceitar só domínios ou `http(s)`) mudaria o contrato da REST API e foi deixado para decisão do grupo; a proteção foi aplicada na saída.
- Sites sem esquema continuam gerando link relativo à aplicação (`href="alfa.example"`), comportamento herdado que não é vulnerabilidade.
