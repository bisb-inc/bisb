"""Tradução dos erros de aplicação para respostas HTTP.

Registrada em `create_app`, vale para a REST API e para as Web Routes. O corpo segue o
formato das respostas de erro do FastAPI: `{"detail": "<mensagem>"}`.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.services.errors import ApplicationError, BusinessRuleError, ConflictError, NotFoundError

STATUS_BY_ERROR: dict[type[ApplicationError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    BusinessRuleError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    for error_type, status_code in STATUS_BY_ERROR.items():
        app.add_exception_handler(error_type, _json_error(status_code))


def _json_error(status_code: int):
    async def handler(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": exc.message})

    return handler
