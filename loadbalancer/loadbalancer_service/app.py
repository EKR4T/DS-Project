"""
Load balancer container (Assignment 1, Task 3).

Routes client requests to one of N backend replicas (Task 1 servers) using
the consistent hash map (Task 2), and exposes management endpoints to
inspect/scale the replica set. New replicas are spawned as sibling Docker
containers on the same network, so this container must run with access to
the host's Docker socket (see docker-compose.yml).

The Docker client is created lazily (get_docker_client) and the initial
replica bootstrap only runs under `__main__`, so this module can be safely
imported by the test suite without a Docker daemon present.
"""
import os
import random
import threading

import requests
from flask import Flask, jsonify, request

from consistent_hash import ConsistentHashMap, DEFAULT_SLOTS, DEFAULT_VIRTUAL_SERVERS

NETWORK_NAME = os.environ.get("LB_NETWORK", "net1")
SERVER_IMAGE = os.environ.get("SERVER_IMAGE", "loadbalancer-server:latest")
DEFAULT_N = int(os.environ.get("LB_N", "3"))

app = Flask(__name__)
lock = threading.Lock()
hash_map = ConsistentHashMap(DEFAULT_SLOTS, DEFAULT_VIRTUAL_SERVERS)

_docker_client = None


def get_docker_client():
    """Lazily create the Docker client so importing this module never requires a Docker daemon."""
    global _docker_client
    if _docker_client is None:
        import docker  # local import: keeps `docker` optional for pure unit tests
        _docker_client = docker.DockerClient(base_url="unix://var/run/docker.sock")
    return _docker_client


def _random_hostname() -> str:
    existing = set(hash_map.servers)
    while True:
        candidate = f"s{random.randint(1000, 9999)}"
        if candidate not in existing:
            return candidate


def spawn_server(hostname: str) -> None:
    """Start a new backend container named `hostname` on the shared network and register it."""
    get_docker_client().containers.run(
        SERVER_IMAGE,
        name=hostname,
        hostname=hostname,
        network=NETWORK_NAME,
        environment={"SERVER_ID": hostname},
        detach=True,
    )
    hash_map.add_server(hostname)


def remove_server(hostname: str) -> None:
    """Deregister `hostname` from the ring and stop/remove its container."""
    hash_map.remove_server(hostname)
    import docker
    try:
        container = get_docker_client().containers.get(hostname)
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass


def bootstrap(n: int) -> None:
    for _ in range(n):
        spawn_server(_random_hostname())


@app.route("/rep", methods=["GET"])
def rep():
    with lock:
        replicas = hash_map.servers
    return jsonify(message={"N": len(replicas), "replicas": replicas}, status="successful"), 200


@app.route("/add", methods=["POST"])
def add():
    payload = request.get_json(silent=True) or {}
    n = payload.get("n")
    hostnames = payload.get("hostnames", [])

    if not isinstance(n, int) or n <= 0:
        return jsonify(message="<Error> 'n' must be a positive integer", status="failure"), 400
    if len(hostnames) > n:
        return jsonify(
            message="<Error> Length of hostname list is more than newly added instances",
            status="failure",
        ), 400

    with lock:
        chosen = list(hostnames)
        while len(chosen) < n:
            chosen.append(_random_hostname())
        for hostname in chosen:
            spawn_server(hostname)
        replicas = hash_map.servers

    return jsonify(message={"N": len(replicas), "replicas": replicas}, status="successful"), 200


@app.route("/rm", methods=["DELETE"])
def rm():
    payload = request.get_json(silent=True) or {}
    n = payload.get("n")
    hostnames = payload.get("hostnames", [])

    if not isinstance(n, int) or n <= 0:
        return jsonify(message="<Error> 'n' must be a positive integer", status="failure"), 400
    if len(hostnames) > n:
        return jsonify(
            message="<Error> Length of hostname list is more than removable instances",
            status="failure",
        ), 400

    with lock:
        to_remove = list(hostnames)
        remaining_pool = [s for s in hash_map.servers if s not in to_remove]
        while len(to_remove) < n and remaining_pool:
            to_remove.append(remaining_pool.pop(random.randrange(len(remaining_pool))))
        for hostname in to_remove:
            remove_server(hostname)
        replicas = hash_map.servers

    return jsonify(message={"N": len(replicas), "replicas": replicas}, status="successful"), 200


@app.route("/<path:path>", methods=["GET"])
def route_request(path):
    with lock:
        server = hash_map.get_server(random.randint(100000, 999999))

    if server is None:
        return jsonify(message="<Error> No server replicas available", status="failure"), 400

    try:
        upstream = requests.get(f"http://{server}:5000/{path}", timeout=5)
        return upstream.content, upstream.status_code, dict(upstream.headers)
    except requests.RequestException:
        return jsonify(
            message=f"<Error> '/{path}' endpoint does not exist in server replicas",
            status="failure",
        ), 400


if __name__ == "__main__":
    bootstrap(DEFAULT_N)
    app.run(host="0.0.0.0", port=5000)
