"""
Unit tests for the Task 3 self-healing heartbeat monitor.

`_is_alive`/`spawn_server`/`remove_server` are monkeypatched so these tests
never touch Docker or the network.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadbalancer_service"))

import app as lb_app  # noqa: E402
from consistent_hash import ConsistentHashMap  # noqa: E402


def _client(monkeypatch):
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
    return spawned, removed


def test_dead_replica_is_replaced_keeping_n_constant(monkeypatch):
    spawned, removed = _client(monkeypatch)
    lb_app.spawn_server("alive1")
    lb_app.spawn_server("dead1")
    spawned.clear()

    monkeypatch.setattr(lb_app, "_is_alive", lambda h: h != "dead1")
    monkeypatch.setattr(lb_app, "_random_hostname", lambda: "replacement1")

    lb_app._check_replicas_once()

    assert removed == ["dead1"]
    assert spawned == ["replacement1"]
    assert set(lb_app.hash_map.servers) == {"alive1", "replacement1"}
    assert len(lb_app.hash_map.servers) == 2


def test_all_healthy_replicas_are_left_untouched(monkeypatch):
    spawned, removed = _client(monkeypatch)
    lb_app.spawn_server("alive1")
    lb_app.spawn_server("alive2")
    spawned.clear()

    monkeypatch.setattr(lb_app, "_is_alive", lambda h: True)

    lb_app._check_replicas_once()

    assert removed == []
    assert spawned == []
    assert set(lb_app.hash_map.servers) == {"alive1", "alive2"}


def test_multiple_dead_replicas_are_each_replaced(monkeypatch):
    spawned, removed = _client(monkeypatch)
    lb_app.spawn_server("dead1")
    lb_app.spawn_server("dead2")
    spawned.clear()

    monkeypatch.setattr(lb_app, "_is_alive", lambda h: False)
    names = iter(["fresh1", "fresh2"])
    monkeypatch.setattr(lb_app, "_random_hostname", lambda: next(names))

    lb_app._check_replicas_once()

    assert set(removed) == {"dead1", "dead2"}
    assert set(spawned) == {"fresh1", "fresh2"}
    assert len(lb_app.hash_map.servers) == 2
