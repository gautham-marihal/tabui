"""The tests run against their own database (bank_test, made by docker-compose beside the real one (docker-compose.yml)): its tables are
built by the migrations, and every test starts from the seed data."""

import os

os.environ.setdefault("BANK_TEST_DATABASE_URL", "postgresql+psycopg://bank:bank@localhost:5434/bank_test")
os.environ["BANK_DATABASE_URL"] = os.environ["BANK_TEST_DATABASE_URL"]
# the CRM routes ask for a key: the tests use their own
os.environ["BANK_API_KEY"] = "test-crm-key"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from bank.app import create_app  # noqa: E402
from bank.db import SessionLocal, engine  # noqa: E402
from bank.seed import reset  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def schema():
    """An empty test database, brought to the latest migration."""
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    config = Config(os.path.join(HERE, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(HERE, "migrations"))
    command.upgrade(config, "head")
    return config


@pytest.fixture(autouse=True)
def fresh_data():
    with SessionLocal.begin() as session:
        reset(session)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(create_app("")) as test_client:
        yield test_client


def call(client, method: str, path: str, body=None):
    response = client.request(method, path, json=body)
    return response.json()
