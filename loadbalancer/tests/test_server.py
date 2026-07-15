"""Unit tests for the Task 1 backend server's Flask routes."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

import server as server_module  # noqa: E402


def test_home_reports_configured_server_id(monkeypatch):
    monkeypatch.setenv("SERVER_ID", "server7")
    client = server_module.app.test_client()

    resp = client.get("/home")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"] == "Hello from Server: server7"
    assert body["status"] == "successful"


def test_home_falls_back_to_unknown_without_server_id(monkeypatch):
    monkeypatch.delenv("SERVER_ID", raising=False)
    client = server_module.app.test_client()

    resp = client.get("/home")

    assert resp.get_json()["message"] == "Hello from Server: unknown"


def test_heartbeat_returns_empty_200():
    client = server_module.app.test_client()

    resp = client.get("/heartbeat")

    assert resp.status_code == 200
    assert resp.data == b""
