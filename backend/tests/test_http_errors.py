import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.http_errors import register_error_handlers
from app.services.errors import BusinessRuleError, ConflictError, NotFoundError


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (NotFoundError("Análise não encontrada"), 404),
        (ConflictError("A empresa TARGET não pode ser removida."), 409),
        (BusinessRuleError("O nome da análise é obrigatório"), 422),
    ],
)
def test_application_errors_map_to_fastapi_error_responses(error, status_code):
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/failure")
    def failure():
        raise error

    response = TestClient(app).get("/failure")

    assert response.status_code == status_code
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"detail": error.message}
