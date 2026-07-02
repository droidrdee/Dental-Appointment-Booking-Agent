from app.main import app
from app.routes.health import health_check


def test_health_check() -> None:
    assert health_check()["status"] == "ok"


def test_health_route_registered() -> None:
    routes = set(app.openapi()["paths"])

    assert "/health" in routes
