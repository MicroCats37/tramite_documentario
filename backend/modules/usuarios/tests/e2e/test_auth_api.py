"""
E2E tests for Auth endpoints: login (username, DNI, email) and /me/.

Tests public login endpoints and the JWT-protected /me/ endpoint.
 Uses ninja_extra.testing.TestClient per TEST_ARCHITECTURE_CONTRACT.

URLs:
    POST /api/auth/login/username
    POST /api/auth/login/dni
    POST /api/auth/login/email
    GET  /api/auth/me/
"""
import pytest
from django.contrib.auth import get_user_model

from ninja_extra.testing import TestClient
from ninja_jwt.tokens import AccessToken
from config.api import api


def _make_auth_client(user):
    """Create a ninja_extra TestClient with JWT auth for the given user."""
    client = TestClient(api)
    token = AccessToken.for_user(user)
    client.headers.update({"Authorization": f"Bearer {token}"})
    client.user = user
    return client


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def usuario(db):
    """Create a test user for auth tests."""
    User = get_user_model()
    user = User.objects.create_user(
        username="12345678",
        dni="12345678",
        email="testuser@cip.gob.pe",
        password="testpass123",
        nombres="Test",
        apellidos="User",
        is_staff=False,
        is_superuser=False,
        is_active=True,
    )
    return user


@pytest.fixture
def inactive_usuario(db):
    """Create an inactive test user."""
    User = get_user_model()
    user = User.objects.create_user(
        username="87654321",
        dni="87654321",
        email="inactive@cip.gob.pe",
        password="testpass123",
        nombres="Inactive",
        apellidos="User",
        is_staff=False,
        is_superuser=False,
        is_active=False,
    )
    return user


# ── POST /api/auth/login/username ─────────────────────────────────────────────


@pytest.mark.django_db
def test_login_username_success(usuario):
    """
    GIVEN:  a user exists with username '12345678' and password 'testpass123'
    WHEN:   POST /auth/login/username is called with correct credentials
    THEN:   response status is 200
            AND success is True
            AND data contains access_token, refresh_token, expires_at, user
            AND user.id, user.username, user.dni, user.email match
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/username",
        json={"username": "12345678", "password": "testpass123"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True, "Response should indicate success"
    assert "data" in data, "Response should have 'data' key"

    token_data = data["data"]
    assert "access_token" in token_data, "Response should contain access_token"
    assert "refresh_token" in token_data, "Response should contain refresh_token"
    assert "expires_at" in token_data, "Response should contain expires_at"
    assert "user" in token_data, "Response should contain user data"

    user_data = token_data["user"]
    assert user_data["username"] == "12345678"
    assert user_data["dni"] == "12345678"
    assert user_data["email"] == "testuser@cip.gob.pe"
    assert user_data["nombres"] == "Test"
    assert user_data["apellidos"] == "User"
    assert user_data["is_staff"] is False
    assert user_data["is_superuser"] is False


@pytest.mark.django_db
def test_login_username_invalid_password(usuario):
    """
    GIVEN:  a user exists with username '12345678' and password 'testpass123'
    WHEN:   POST /auth/login/username is called with wrong password
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/username",
        json={"username": "12345678", "password": "wrongpassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_username_nonexistent_user():
    """
    GIVEN:  no user exists with username '00000001'
    WHEN:   POST /auth/login/username is called with that username
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/username",
        json={"username": "00000001", "password": "anypassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_username_inactive_user(inactive_usuario):
    """
    GIVEN:  an inactive user exists with username '87654321'
    WHEN:   POST /auth/login/username is called with that user credentials
    THEN:   response status is 401
            Note: Django's authenticate() returns None for inactive users, so the
            code never reaches the is_active check and returns 401 consistently.
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/username",
        json={"username": "87654321", "password": "testpass123"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


# ── POST /api/auth/login/dni ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_dni_success(usuario):
    """
    GIVEN:  a user exists with dni '12345678' and password 'testpass123'
    WHEN:   POST /auth/login/dni is called with correct credentials
    THEN:   response status is 200
            AND success is True
            AND data contains access_token, refresh_token, expires_at, user
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/dni",
        json={"dni": "12345678", "password": "testpass123"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True, "Response should indicate success"
    assert "data" in data

    token_data = data["data"]
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "expires_at" in token_data
    assert "user" in token_data

    user_data = token_data["user"]
    assert user_data["dni"] == "12345678"


@pytest.mark.django_db
def test_login_dni_invalid_password(usuario):
    """
    GIVEN:  a user exists with dni '12345678' and password 'testpass123'
    WHEN:   POST /auth/login/dni is called with wrong password
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/dni",
        json={"dni": "12345678", "password": "wrongpassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_dni_nonexistent():
    """
    GIVEN:  no user exists with dni '00000001'
    WHEN:   POST /auth/login/dni is called with that DNI
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/dni",
        json={"dni": "00000001", "password": "anypassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_dni_inactive_user(inactive_usuario):
    """
    GIVEN:  an inactive user exists with dni '87654321'
    WHEN:   POST /auth/login/dni is called with that user credentials
    THEN:   response status is 401
            Note: Django's authenticate() returns None for inactive users, so the
            code never reaches the is_active check and returns 401 consistently.
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/dni",
        json={"dni": "87654321", "password": "testpass123"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


# ── POST /api/auth/login/email ────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_email_success(usuario):
    """
    GIVEN:  a user exists with email 'testuser@cip.gob.pe' and password 'testpass123'
    WHEN:   POST /auth/login/email is called with correct credentials
    THEN:   response status is 200
            AND success is True
            AND data contains access_token, refresh_token, expires_at, user
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/email",
        json={"email": "testuser@cip.gob.pe", "password": "testpass123"},
    )

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True, "Response should indicate success"
    assert "data" in data

    token_data = data["data"]
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert "expires_at" in token_data
    assert "user" in token_data

    user_data = token_data["user"]
    assert user_data["email"] == "testuser@cip.gob.pe"


@pytest.mark.django_db
def test_login_email_invalid_password(usuario):
    """
    GIVEN:  a user exists with email 'testuser@cip.gob.pe' and password 'testpass123'
    WHEN:   POST /auth/login/email is called with wrong password
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/email",
        json={"email": "testuser@cip.gob.pe", "password": "wrongpassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_email_nonexistent():
    """
    GIVEN:  no user exists with email 'nonexistent@cip.gob.pe'
    WHEN:   POST /auth/login/email is called with that email
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/email",
        json={"email": "nonexistent@cip.gob.pe", "password": "anypassword"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_login_email_inactive_user(inactive_usuario):
    """
    GIVEN:  an inactive user exists with email 'inactive@cip.gob.pe'
    WHEN:   POST /auth/login/email is called with that user credentials
    THEN:   response status is 401
            Note: Django's authenticate() returns None for inactive users, so the
            code never reaches the is_active check and returns 401 consistently.
    """
    client = TestClient(api)
    response = client.post(
        "/auth/login/email",
        json={"email": "inactive@cip.gob.pe", "password": "testpass123"},
    )

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


# ── GET /api/auth/me/ ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_get_me_success(usuario):
    """
    GIVEN:  an authenticated user with a valid JWT
    WHEN:   GET /auth/me/ is called with the Authorization header
    THEN:   response status is 200
            AND success is True
            AND data contains id, username, dni, email, nombres, apellidos, is_staff, is_superuser
    """
    client = _make_auth_client(usuario)
    response = client.get("/auth/me/")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.content}"
    )

    data = response.json()
    assert data["success"] is True, "Response should indicate success"
    assert "data" in data, "Response should have 'data' key"

    user_data = data["data"]
    assert user_data["username"] == "12345678"
    assert user_data["dni"] == "12345678"
    assert user_data["email"] == "testuser@cip.gob.pe"
    assert user_data["nombres"] == "Test"
    assert user_data["apellidos"] == "User"
    assert user_data["is_staff"] is False
    assert user_data["is_superuser"] is False
    assert "id" in user_data, "User data should contain 'id' field"


@pytest.mark.django_db
def test_get_me_without_token():
    """
    GIVEN:  no JWT token provided
    WHEN:   GET /auth/me/ is called without Authorization header
    THEN:   response status is 401
    """
    client = TestClient(api)
    response = client.get("/auth/me/")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )


@pytest.mark.django_db
def test_get_me_with_invalid_token():
    """
    GIVEN:  an invalid JWT token
    WHEN:   GET /auth/me/ is called with a malformed Authorization header
    THEN:   response status is 401
    """
    client = TestClient(api)
    client.headers.update({"Authorization": "Bearer invalid.token.here"})
    response = client.get("/auth/me/")

    assert response.status_code == 401, (
        f"Expected 401, got {response.status_code}: {response.content}"
    )
