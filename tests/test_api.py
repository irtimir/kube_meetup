from __future__ import annotations


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_ready_success(client, mock_redis):
    mock_redis.ping.return_value = True
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"


def test_ready_redis_down(client, mock_redis):
    mock_redis.ping.side_effect = Exception("Connection refused")
    response = client.get("/ready")
    assert response.status_code == 503


def test_create_task(client, mock_redis):
    response = client.post("/tasks", json={"payload": "test task"})
    assert response.status_code == 201
    data = response.get_json()
    assert "task" in data
    assert data["task"]["payload"] == "test task"
    mock_redis.lpush.assert_called_once()


def test_create_task_default_payload(client, mock_redis):
    response = client.post("/tasks", json={})
    assert response.status_code == 201
    data = response.get_json()
    assert data["task"]["payload"] == "default task"


def test_list_tasks(client, mock_redis):
    mock_redis.lrange.return_value = ['{"id": "1", "payload": "test"}']
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.get_json()
    assert "pending_tasks" in data


def test_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"tasks_created_total" in response.data
