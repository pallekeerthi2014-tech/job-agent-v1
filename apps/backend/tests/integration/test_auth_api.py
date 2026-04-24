from app.db import crud
from app.schemas.user import UserCreate


def test_forgot_and_reset_password_flow(client, db_session) -> None:
    user = crud.create_user(
        db_session,
        UserCreate(
            name="Reset User",
            email="reset.user@example.com",
            password="Original123!",
            role="employee",
            is_active=True,
            employee_id=None,
        ),
    )

    forgot_response = client.post("/api/v1/auth/forgot-password", json={"email": user.email})
    assert forgot_response.status_code == 200
    forgot_payload = forgot_response.json()
    assert forgot_payload["delivery"] == "preview"
    assert forgot_payload["reset_token"]

    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": forgot_payload["reset_token"], "password": "NewPassword123!"},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password updated successfully."

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "NewPassword123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["email"] == user.email
