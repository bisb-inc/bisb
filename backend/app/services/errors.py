"""Erros esperados das regras de aplicação, independentes do protocolo de entrega.

A mensagem de cada erro é segura para exibição ao usuário. A tradução para respostas HTTP
fica em `app.http_errors`.
"""


class ApplicationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ApplicationError):
    """O recurso solicitado não existe ou não pertence ao contexto informado."""


class ConflictError(ApplicationError):
    """A operação conflita com o estado atual dos dados."""


class BusinessRuleError(ApplicationError):
    """Os dados informados violam uma regra de negócio ou de validação."""
