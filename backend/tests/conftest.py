import os
import tempfile

import pytest

_DB = os.path.join(tempfile.mkdtemp(), "fenrix-test.db")
os.environ["FENRIX_DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["FENRIX_LIVE_FEEDS"] = "false"
os.environ["FENRIX_LLM_ENABLED"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

from fenrix.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth(client):
    r = client.post("/api/auth/login", json={"email": "analyst@fenrix.dev", "password": "fenrix-demo"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}
