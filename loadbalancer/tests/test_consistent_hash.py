"""Unit tests for the Task 2 consistent hash map. No Docker/Flask needed."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "loadbalancer_service"))

from consistent_hash import ConsistentHashMap, request_hash, virtual_server_hash  # noqa: E402


def test_request_hash_matches_spec_formula():
    # H(i) = i^2 + 2i + 17
    assert request_hash(0, 512) == 17
    assert request_hash(1, 512) == 20
    assert request_hash(10, 512) == (100 + 20 + 17) % 512


def test_virtual_server_hash_matches_spec_formula():
    # Phi(i, j) = i^2 + j^2 + 2j + 25
    assert virtual_server_hash(0, 0, 512) == 25
    assert virtual_server_hash(1, 2, 512) == (1 + 4 + 4 + 25) % 512


def test_add_server_creates_expected_number_of_virtual_slots():
    ring = ConsistentHashMap(num_slots=512, num_virtual_servers=9)
    ring.add_server("server1")
    assert len(ring._server_slots["server1"]) == 9
    assert ring.servers == ["server1"]


def test_adding_same_server_twice_is_a_no_op():
    ring = ConsistentHashMap()
    ring.add_server("server1")
    slots_before = list(ring._server_slots["server1"])
    ring.add_server("server1")
    assert ring._server_slots["server1"] == slots_before


def test_get_server_returns_none_when_ring_empty():
    ring = ConsistentHashMap()
    assert ring.get_server(123456) is None


def test_get_server_routes_consistently_for_same_request_id():
    ring = ConsistentHashMap()
    ring.add_server("server1")
    ring.add_server("server2")
    first = ring.get_server(555555)
    second = ring.get_server(555555)
    assert first == second
    assert first in ring.servers


def test_get_server_only_returns_known_servers():
    ring = ConsistentHashMap()
    ring.add_server("server1")
    ring.add_server("server2")
    ring.add_server("server3")
    seen = {ring.get_server(rid) for rid in range(100000, 100200)}
    assert seen <= set(ring.servers)


def test_remove_server_frees_its_slots():
    ring = ConsistentHashMap()
    ring.add_server("server1")
    slots = list(ring._server_slots["server1"])
    ring.remove_server("server1")
    assert ring.servers == []
    assert all(ring.ring[slot] is None for slot in slots)


def test_remove_unknown_server_is_a_no_op():
    ring = ConsistentHashMap()
    ring.add_server("server1")
    ring.remove_server("does-not-exist")
    assert ring.servers == ["server1"]


def test_collision_is_resolved_with_quadratic_probing_in_a_tiny_ring():
    ring = ConsistentHashMap(num_slots=4, num_virtual_servers=1)
    ring.add_server("A")
    ring.add_server("B")
    occupied = ring._server_slots["A"] + ring._server_slots["B"]
    assert len(set(occupied)) == 2  # both servers land on distinct slots


def test_ring_full_raises_when_no_slot_available():
    ring = ConsistentHashMap(num_slots=2, num_virtual_servers=1)
    ring.add_server("A")
    ring.add_server("B")
    try:
        ring.add_server("C")
        assert False, "expected RuntimeError when the ring has no free slot"
    except RuntimeError:
        pass
