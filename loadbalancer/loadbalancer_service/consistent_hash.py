"""
Consistent hash map used by the load balancer (Assignment 1, Task 2).

Implements the circular hash structure described in the assignment appendix:
requests are mapped onto a ring of `num_slots` slots via H(i); servers are
placed on the ring (as `num_virtual_servers` virtual copies each) via
Phi(i, j); collisions on server placement are resolved with quadratic
probing; requests are routed clockwise to the nearest occupied slot.
"""
import math

DEFAULT_SLOTS = 512
DEFAULT_VIRTUAL_SERVERS = int(math.log2(DEFAULT_SLOTS))  # K = log2(512) = 9


def request_hash(request_id: int, num_slots: int = DEFAULT_SLOTS) -> int:
    """H(i) = i^2 + 2i + 17 (mod num_slots)."""
    return (request_id * request_id + 2 * request_id + 17) % num_slots


def virtual_server_hash(server_id: int, replica_id: int, num_slots: int = DEFAULT_SLOTS) -> int:
    """Phi(i, j) = i^2 + j^2 + 2j + 25 (mod num_slots)."""
    return (server_id * server_id + replica_id * replica_id + 2 * replica_id + 25) % num_slots


class ConsistentHashMap:
    """A circular hash map mapping server names onto a fixed-size ring."""

    def __init__(self, num_slots: int = DEFAULT_SLOTS, num_virtual_servers: int = DEFAULT_VIRTUAL_SERVERS):
        self.num_slots = num_slots
        self.num_virtual_servers = num_virtual_servers
        self.ring = [None] * num_slots           # slot index -> server name
        self._server_slots = {}                  # server name -> [slot indices]
        self._server_ids = {}                     # server name -> assigned integer id
        self._next_server_id = 0

    def _probe(self, start_slot: int) -> int:
        """Quadratic probing to the next free slot, starting at start_slot."""
        for probe in range(self.num_slots):
            slot = (start_slot + probe * probe) % self.num_slots
            if self.ring[slot] is None:
                return slot
        raise RuntimeError("Consistent hash ring is full: no free slot for new server")

    def add_server(self, name: str) -> None:
        """Place `num_virtual_servers` virtual replicas of `name` onto the ring."""
        if name in self._server_slots:
            return
        server_id = self._next_server_id
        self._next_server_id += 1
        self._server_ids[name] = server_id

        slots = []
        for replica_id in range(self.num_virtual_servers):
            preferred_slot = virtual_server_hash(server_id, replica_id, self.num_slots)
            slot = self._probe(preferred_slot)
            self.ring[slot] = name
            slots.append(slot)
        self._server_slots[name] = slots

    def remove_server(self, name: str) -> None:
        """Remove all virtual replicas of `name` from the ring, freeing their slots."""
        for slot in self._server_slots.pop(name, []):
            self.ring[slot] = None
        self._server_ids.pop(name, None)

    def get_server(self, request_id: int):
        """Return the server name owning the nearest occupied slot clockwise of H(request_id)."""
        if not self._server_slots:
            return None
        start = request_hash(request_id, self.num_slots)
        for offset in range(self.num_slots):
            slot = (start + offset) % self.num_slots
            if self.ring[slot] is not None:
                return self.ring[slot]
        return None

    @property
    def servers(self):
        """Server names currently on the ring, in the order they were added."""
        return list(self._server_slots.keys())
