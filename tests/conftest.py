from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock.ping.return_value = True
    mock.llen.return_value = 0
    mock.lrange.return_value = []
    mock.get.return_value = None

    monkeypatch.setattr("app.api.get_redis", lambda: mock)
    return mock


@pytest.fixture
def client(mock_redis: MagicMock):
    from app.api import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
