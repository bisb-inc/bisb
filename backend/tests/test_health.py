from sqlalchemy.exc import OperationalError


def test_health_does_not_access_database(client, session):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    session.execute.assert_not_called()


def test_readiness_checks_database(client, session):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert str(session.execute.call_args.args[0]) == "SELECT 1"


def test_readiness_failure_does_not_leak_details(client, session, caplog):
    session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("secret-password"))
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert "secret-password" not in response.text + caplog.text
    assert client.get("/health").status_code == 200


def test_documentation_is_available(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "503" in schema["paths"]["/health/ready"]["get"]["responses"]
