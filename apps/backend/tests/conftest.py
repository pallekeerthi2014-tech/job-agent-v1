from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_db
from app.db import crud
from app.db.base import Base
from app.main import app, settings
from app.schemas.user import UserCreate
from app import models  # noqa: F401


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    original_scheduler_enabled = settings.scheduler_enabled
    settings.scheduler_enabled = False

    with TestClient(app) as test_client:
        yield test_client

    settings.scheduler_enabled = original_scheduler_enabled
    app.dependency_overrides.clear()


@pytest.fixture()
def super_admin(db_session: Session):
    return crud.create_user(
        db_session,
        UserCreate(
            name="Test Admin",
            email="admin@example.com",
            password="Admin123!",
            role="super_admin",
            is_active=True,
            employee_id=None,
        ),
    )


@pytest.fixture()
def auth_headers(client: TestClient, super_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": super_admin.email,
            "password": "Admin123!",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
