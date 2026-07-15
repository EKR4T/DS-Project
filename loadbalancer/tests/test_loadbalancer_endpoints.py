"""
Unit tests for the Task 3 load balancer's HTTP endpoints.

`spawn_server`/`remove_server` are monkeypatched to fakes that only touch the
in-memory consistent hash ring, so these tests never require a Docker daemon.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadbalancer_service"))

import app as lb_app  # noqa: E402
from consistent_hash import ConsistentHashMap  # noqa: E402


def _client(monkeypatch):
    """Reset the ring and stub out anything that would touch Docker/network."""
    lb_app.hash_map = ConsistentHashMap()
    spawned, removed = [], []

    def fake_spawn(hostname):
        spawned.append(hostname)
        lb_app.hash_map.add_server(hostname)

    def fake_remove(hostname):
        removed.append(hostname)
        lb_app.hash_map.remove_server(hostname)

    monkeypatch.setattr(lb_app, "spawn_server", fake_spawn)
    monkeypatch.setattr(lb_app, "remove_server", fake_remove)
    return lb_app.app.test_client(), spawned, removed


def test_rep_reports_current_replicas(monkeypatch):
    client, _, _ = _client(monkeypatch)
    lb_app.spawn_server("server1")

    resp = client.get("/rep")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["message"]["N"] == 1
    assert body["message"]["replicas"] == ["server1"]
    assert body["status"] == "successful"


def test_rep_on_empty_ring(monkeypatch):
    client, _, _ = _client(monkeypatch)

    resp = client.get("/rep")

    assert resp.get_json()["message"]["N"] == 0


def test_add_spawns_requested_hostnames(monkeypatch):
    client, spawned, _ = _client(monkeypatch)

    resp = client.post("/add", json={"n": 2, "hostnames": ["s4", "s5"]})

    assert resp.status_code == 200
    assert set(spawned) == {"s4", "s5"}
    assert resp.get_json()["message"]["N"] == 2


def test_add_fills_in_random_hostnames_when_fewer_names_given(monkeypatch):
    client, spawned, _ = _client(monkeypatch)

    resp = client.post("/add", json={"n": 3, "hostnames": ["s4"]})

    assert resp.status_code == 200
    assert "s4" in spawned
    assert len(spawned) == 3
    assert resp.get_json()["message"]["N"] == 3


def test_add_rejects_hostname_list_longer_than_n(monkeypatch):
    client, spawned, _ = _client(monkeypatch)

    resp = client.post("/add", json={"n": 1, "hostnames": ["s4", "s5"]})

    assert resp.status_code == 400
    assert resp.get_json()["status"] == "failure"
    assert spawned == []


def test_rm_removes_requested_hostname(monkeypatch):
    client, _, removed = _client(monkeypatch)
    lb_app.spawn_server("s4")

    resp = client.delete("/rm", json={"n": 1, "hostnames": ["s4"]})

    assert resp.status_code == 200
    assert removed == ["s4"]
    assert resp.get_json()["message"]["N"] == 0


def test_rm_rejects_hostname_list_longer_than_n(monkeypatch):
    client, _, removed = _client(monkeypatch)
    lb_app.spawn_server("s4")
    lb_app.spawn_server("s5")

    resp = client.delete("/rm", json={"n": 1, "hostnames": ["s4", "s5"]})

    assert resp.status_code == 400
    assert removed == []


def test_route_request_forwards_to_selected_server(monkeypatch):
    client, _, _ = _client(monkeypatch)
    lb_app.spawn_server("server1")

    class FakeResponse:
        status_code = 200
        content = b'{"message": "Hello from Server: server1", "status": "successful"}'
        headers = {"Content-Type": "application/json"}

    def fake_get(url, timeout=5):
        assert url == "http://server1:5000/home"
        return FakeResponse()

    monkeypatch.setattr(lb_app.requests, "get", fake_get)

    resp = client.get("/home")

    assert resp.status_code == 200
    assert b"server1" in resp.data


def test_route_request_with_no_replicas_returns_400(monkeypatch):
    client, _, _ = _client(monkeypatch)

    resp = client.get("/home")

    assert resp.status_code == 400
    assert resp.get_json()["status"] == "failure"


def test_route_request_unreachable_server_returns_400(monkeypatch):
    client, _, _ = _client(monkeypatch)
    lb_app.spawn_server("server1")

    def fake_get(url, timeout=5):
        raise lb_app.requests.RequestException("connection refused")

    monkeypatch.setattr(lb_app.requests, "get", fake_get)

    resp = client.get("/other")

    assert resp.status_code == 400
    assert "does not exist" in resp.get_json()["message"]
