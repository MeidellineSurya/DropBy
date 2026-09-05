from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_dashboard_origin_gets_cors_preflight_approval() -> None:
    # Without CORSMiddleware configured, the dashboard (a different origin —
    # its own Vite dev server port) can't call the API from a browser at all;
    # this would previously have returned a plain 400 with no CORS headers.
    response = client.options(
        "/api/v1/business/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unlisted_origin_is_not_granted_cors_access() -> None:
    response = client.options(
        "/api/v1/business/auth/login",
        headers={
            "Origin": "https://not-dropby.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in response.headers
