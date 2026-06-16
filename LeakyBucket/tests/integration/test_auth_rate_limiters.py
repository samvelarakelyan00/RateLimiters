# Non-Standard libs
from fastapi.testclient import TestClient

# Own Modules
from main import app


client = TestClient(app)


URL_COMMON_PART = "http://127.0.0.1:8000/api/v1/auth"


# --------------------------------------------------------------------------------------
# Root Endpoint
# --------------------------------------------------------------------------------------
def test_root_returns_200() -> None:
    response = client.get("/")

    assert response.status_code == 200


# --------------------------------------------------------------------------------------
# Login Endpoint
# --------------------------------------------------------------------------------------
def test_login_first_request_allowed() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": "first@test.com",
            "password": "password"
        }
    )

    assert response.status_code == 200


def test_login_email_capacity_blocks_fourth_request() -> None:
    email = "blocked@test.com"

    for _ in range(3):
        client.post(
            f"{URL_COMMON_PART}/login",
            json={
                "email": email,
                "password": "password"
            }
        )

    response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": email,
            "password": "password"
        }
    )

    assert response.status_code == 429


def test_login_email_normalization() -> None:
    client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": "TestUser@gmail.com",
            "password": "password"
        }
    )

    client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": "testuser@gmail.com",
            "password": "password"
        }
    )

    client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": "TESTUSER@gmail.com",
            "password": "password"
        }
    )

    response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": "testuser@gmail.com",
            "password": "password"
        }
    )

    assert response.status_code == 429


# --------------------------------------------------------------------------------------
# Signup Endpoint
# --------------------------------------------------------------------------------------
def test_signup_first_request_allowed() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john",
            "email": "john@test.com",
            "plain_password": "password"
        }
    )

    assert response.status_code == 201


def test_signup_email_limit_blocks_second_request() -> None:
    email = "signup@test.com"

    response_1 = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john",
            "email": email,
            "plain_password": "password"
        }
    )

    response_2 = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john2",
            "email": email,
            "plain_password": "password"
        }
    )

    assert response_1.status_code == 201
    assert response_2.status_code == 429


def test_signup_different_emails_are_independent() -> None:
    response_1 = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "user1",
            "email": "user1@test.com",
            "plain_password": "password"
        }
    )

    response_2 = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "user2",
            "email": "user2@test.com",
            "plain_password": "password"
        }
    )

    assert response_1.status_code == 201
    assert response_2.status_code == 201


# --------------------------------------------------------------------------------------
# Endpoint Isolation
# --------------------------------------------------------------------------------------
def test_login_limiter_does_not_affect_signup() -> None:
    email = "isolation@test.com"

    for _ in range(3):
        client.post(
            f"{URL_COMMON_PART}/login",
            json={
                "email": email,
                "password": "password"
            }
        )

    login_response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": email,
            "password": "password"
        }
    )

    signup_response = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john",
            "email": email,
            "plain_password": "password"
        }
    )

    assert login_response.status_code == 429
    assert signup_response.status_code == 201


def test_signup_limiter_does_not_affect_login() -> None:
    email = "cross@test.com"

    client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john",
            "email": email,
            "plain_password": "password"
        }
    )

    signup_response = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john2",
            "email": email,
            "plain_password": "password"
        }
    )

    login_response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "email": email,
            "password": "password"
        }
    )

    assert signup_response.status_code == 429
    assert login_response.status_code == 200


# --------------------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------------------
def test_login_invalid_payload_returns_422() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/login",
        json={}
    )

    assert response.status_code == 422


def test_signup_invalid_payload_returns_422() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/signup",
        json={}
    )

    assert response.status_code == 422


def test_login_missing_email_returns_422() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/login",
        json={
            "password": "password"
        }
    )

    assert response.status_code == 422


def test_signup_missing_email_returns_422() -> None:
    response = client.post(
        f"{URL_COMMON_PART}/signup",
        json={
            "username": "john",
            "plain_password": "password"
        }
    )

    assert response.status_code == 422