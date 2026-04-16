from starlette.middleware.cors import CORSMiddleware

from main import app
from middleware.auth import JWTAuthMiddleware
from middleware.service_token import ServiceTokenMiddleware


def test_main_registers_new_middleware_only() -> None:
    classes = [m.cls for m in app.user_middleware]
    assert CORSMiddleware in classes
    assert ServiceTokenMiddleware in classes
    assert JWTAuthMiddleware in classes
    for m in classes:
        assert m.__name__ != "APIKeyAuthMiddleware"
