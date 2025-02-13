from starlette.applications import Starlette
from starlette_jwt import JWTAuthenticationBackend, JWTUser
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from starlette.middleware.authentication import AuthenticationMiddleware
import jwt
from starlette.authentication import requires


@requires('authenticated')
async def with_auth(request):
    return JSONResponse({'auth': {"username": request.user.display_name}})


async def without_auth(request):
    return JSONResponse({'auth': None})


def create_app():
    app = Starlette()
    app.add_route("/auth", with_auth, methods=["GET"])
    app.add_route("/no-auth", without_auth, methods=["GET"])
    return app


def test_header_parse():
    secret_key = 'example'
    app = create_app()
    app.add_middleware(AuthenticationMiddleware, backend=JWTAuthenticationBackend(secret_key=secret_key))
    client = TestClient(app)

    # No token for auth endpoint
    response = client.get("/auth")
    assert response.text == 'Forbidden'
    assert response.status_code == 403

    # Without prefix
    response = client.get("/auth",
                          headers=dict(Authorization=jwt.encode(dict(username="user"), secret_key, algorithm='HS256').decode()))
    assert response.text == 'Could not separate Authorization scheme and token'
    assert response.status_code == 400

    # Wrong prefix
    response = client.get("/auth",
                          headers=dict(Authorization=f'WRONG {jwt.encode(dict(username="user"), secret_key, algorithm="HS256").decode()}'))
    assert response.text == 'Authorization scheme WRONG is not supported'
    assert response.status_code == 400

    # Good headers
    response = client.get("/auth", headers=dict(Authorization=f'JWT {jwt.encode(dict(username="user"), secret_key, algorithm="HS256").decode()}'))
    assert response.json() == {"auth": {"username": "user"}}
    assert response.status_code == 200

    # Wrong secret key
    response = client.get("/auth",
                          headers=dict(Authorization=f'JWT {jwt.encode(dict(username="user"), "BAD SECRET", algorithm="HS256").decode()}'))
    assert response.text == 'Signature verification failed'
    assert response.status_code == 400


def test_get_token_from_header():
    token = jwt.encode(dict(username="user"), 'secret', algorithm="HS256").decode()
    assert token == JWTAuthenticationBackend.get_token_from_header(authorization=f'JWT {token}', prefix='JWT')


def test_user_object():
    payload = dict(username="user")
    token = jwt.encode(payload, "BAD SECRET", algorithm="HS256").decode()
    user_object = JWTUser(username="user", payload=payload, token=token)
    assert user_object.is_authenticated == True
    assert user_object.display_name == 'user'
    assert user_object.token == token
    assert user_object.payload == payload
