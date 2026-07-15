"""
Task 4 analysis script.

Requires a running stack (`make up` from the loadbalancer/ folder first).
Fires many async requests at the load balancer's /home endpoint, tallies how
many were served by each backend replica, and renders the charts required by
the assignment:

  A-1: bar chart of requests handled per replica at N=3
  A-2: line chart of average load per replica as N grows from 2 to 6

Usage:
    python3 analysis/analyze.py --requests 10000
    python3 analysis/analyze.py --requests 10000 --skip-scaling
"""
import argparse
import asyncio
import collections
import os
import re

import aiohttp
import matplotlib
import requests

matplotlib.use("Agg")  # headless: just save PNGs, don't try to open a display
import matplotlib.pyplot as plt  # noqa: E402

LB_URL = os.environ.get("LB_URL", "http://localhost:5000")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


async def _fire_one(session: aiohttp.ClientSession):
    async with session.get(f"{LB_URL}/home") as resp:
        if resp.status != 200:
            return None
        body = await resp.json()
        match = re.search(r"Server:\s*(\S+)", body.get("message", ""))
        return match.group(1) if match else None


async def fire_requests(n: int) -> "collections.Counter[str]":
    counts: collections.Counter = collections.Counter()
    async with aiohttp.ClientSession() as session:
        tasks = [_fire_one(session) for _ in range(n)]
        for result in await asyncio.gather(*tasks):
            if result:
                counts[result] += 1
    return counts


def set_replica_count(target_n: int) -> None:
    """Scale the running load balancer up/down to exactly target_n replicas via /add and /rm."""
    current = requests.get(f"{LB_URL}/rep").json()["message"]["N"]
    if target_n > current:
        requests.post(f"{LB_URL}/add", json={"n": target_n - current, "hostnames": []})
    elif target_n < current:
        requests.delete(f"{LB_URL}/rm", json={"n": current - target_n, "hostnames": []})


def plot_bar_chart(counts: "collections.Counter[str]") -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "a1_bar_chart.png")

    servers = sorted(counts)
    values = [counts[s] for s in servers]

    plt.figure()
    plt.bar(servers, values)
    plt.xlabel("Server replica")
    plt.ylabel("Requests handled")
    plt.title(f"A-1: Request distribution across N={len(servers)} replicas")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def plot_line_chart(n_values, averages) -> str:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "a2_line_chart.png")

    plt.figure()
    plt.plot(list(n_values), averages, marker="o")
    plt.xlabel("Number of replicas (N)")
    plt.ylabel("Average load per replica")
    plt.title("A-2: Scalability as N increases")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    return out_path


def run_scaling_experiment(n_values, requests_per_run: int):
    averages = []
    for n in n_values:
        set_replica_count(n)
        counts = asyncio.run(fire_requests(requests_per_run))
        active_n = requests.get(f"{LB_URL}/rep").json()["message"]["N"]
        avg = sum(counts.values()) / active_n if active_n else 0
        averages.append(avg)
        print(f"N={n}: average load per replica = {avg:.1f}")
    return averages


def main() -> None:
    parser = argparse.ArgumentParser(description="Load balancer analysis (Task 4)")
    parser.add_argument("--requests", type=int, default=10000, help="Requests to fire for A-1")
    parser.add_argument("--skip-scaling", action="store_true", help="Skip the A-2 scaling experiment")
    args = parser.parse_args()

    print(f"A-1: firing {args.requests} requests at N=3 ...")
    counts = asyncio.run(fire_requests(args.requests))
    print("Requests handled per replica:", dict(counts))
    print("Saved", plot_bar_chart(counts))

    if not args.skip_scaling:
        print("\nA-2: scaling N from 2 to 6 ...")
        n_values = range(2, 7)
        averages = run_scaling_experiment(n_values, args.requests)
        print("Saved", plot_line_chart(n_values, averages))
        # Restore the default replica count for anyone re-running the stack afterwards.
        set_replica_count(3)


if __name__ == "__main__":
    main()
