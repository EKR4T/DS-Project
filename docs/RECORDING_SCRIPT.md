# Recording Script — Customizable Load Balancer (ICS 4104, Assignment 1)

A 3-presenter video script covering all four tasks. Each presenter's section
lists **SAY** (narration — paraphrase in your own words), **SHOW** (what to
have on screen), and **RUN** (exact command to execute). Commands are
PowerShell, verified against the repo as of this recording.

## Segment overview

| Segment | Presenter | Covers | Grading weight | Target time |
|---|---|---|---|---|
| 1 | **A** | Intro + Task 1 (Server) + Task 2 (Consistent Hashing) | 20% + 30% | ~5 min |
| 2 | **B** | Task 3 (Load Balancer) — build, deploy, endpoints, failure recovery | 30% | ~5–6 min |
| 3 | **C** | Task 4 (Analysis) — A-1 / A-2 / A-3 recap / A-4 + wrap-up | 20% | ~4–5 min |

**Total runtime target:** ~15 minutes.

## Pre-flight checklist (run once, before recording starts)

```powershell
git status                      # confirm the requirements.txt fix is committed
docker compose down 2>$null
docker ps -aq --filter "ancestor=loadbalancer-server:latest" | ForEach-Object { docker rm -f $_ }
docker compose build            # confirm both images still build clean
```

---

## Presenter A — Task 1 (Server) & Task 2 (Consistent Hashing)

### [0:00] Intro

> **SAY:** "Hi, we're [names], and this is our submission for ICS 4104
> Assignment 1 — a customizable load balancer built with consistent hashing.
> I'm [name], and I'll walk through Task 1, the backend server, and Task 2,
> the consistent hashing implementation. [Name] will cover Task 3, the load
> balancer itself, and [name] will finish with our Task 4 performance
> analysis."

**RUN** (prove the environment is real before touching code):
```powershell
cd loadbalancer
docker version
docker compose version
```

> **SAY:** "We're running this natively on Windows with Docker Desktop — no
> WSL needed. Let's start with Task 1."

### [0:45] Task 1 — the server

**SHOW:** `server/server.py`

> **SAY:** "Task 1 asks for a minimal web server on port 5000 with two
> endpoints: `/home` and `/heartbeat`. Ours is a small Flask app."

**Point at lines 16–19:**
```python
@app.route("/home", methods=["GET"])
def home():
    server_id = os.environ.get("SERVER_ID", "unknown")
    return jsonify(message=f"Hello from Server: {server_id}", status="successful"), 200
```
> **SAY:** "`/home` reads a `SERVER_ID` environment variable — that's how
> each replica container identifies itself — and returns it in the JSON the
> spec asks for: `Hello from Server: <id>`, status successful, code 200."

**Point at lines 22–24:**
```python
@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    return "", 200
```
> **SAY:** "`/heartbeat` just returns an empty 200. The load balancer polls
> this to detect a dead replica — you'll see that in Task 3."

**Point at line 31:**
```python
app.run(host="0.0.0.0", port=5000, threaded=True)
```
> **SAY:** "One thing we caught during testing: Flask's dev server is
> single-threaded by default, which would serialize every request through
> one replica at a time. Since the assignment requires handling requests
> *asynchronously*, we run with `threaded=True`."

**SHOW:** `server/Dockerfile`

> **SAY:** "And it's containerized with a simple Dockerfile — Python
> 3.11-slim, install `flask`, copy `server.py`, expose port 5000."

### [2:00] Task 2 — consistent hashing

**SHOW:** `loadbalancer_service/consistent_hash.py`

> **SAY:** "Task 2 is the consistent hash map. Per the spec: 512 slots
> total, N=3 server containers, and K = log2(512) = 9 virtual servers per
> container."

**Point at lines 12–13 and 16–23:**
```python
DEFAULT_SLOTS = 512
DEFAULT_VIRTUAL_SERVERS = int(math.log2(DEFAULT_SLOTS))  # K = log2(512) = 9

def request_hash(request_id: int, num_slots: int = DEFAULT_SLOTS) -> int:
    """H(i) = i^2 + 2i + 17 (mod num_slots)."""
    return (request_id * request_id + 2 * request_id + 17) % num_slots

def virtual_server_hash(server_id: int, replica_id: int, num_slots: int = DEFAULT_SLOTS) -> int:
    """Phi(i, j) = i^2 + j^2 + 2j + 25 (mod num_slots)."""
    return (server_id * server_id + replica_id * replica_id + 2 * replica_id + 25) % num_slots
```
> **SAY:** "The two hash functions are exactly as specified: `H(i) = i² + 2i
> + 17 mod 512` for mapping requests onto the ring, and `Φ(i,j) = i² + j² +
> 2j + 25 mod 512` for placing virtual servers, where `i` is the server ID
> and `j` is the virtual replica index."

**Point at lines 37–43 (`_probe`):**
```python
def _probe(self, start_slot: int) -> int:
    """Quadratic probing to the next free slot, starting at start_slot."""
    for probe in range(self.num_slots):
        slot = (start_slot + probe * probe) % self.num_slots
        if self.ring[slot] is None:
            return slot
    raise RuntimeError("Consistent hash ring is full: no free slot for new server")
```
> **SAY:** "When two virtual servers hash to the same slot, we resolve the
> collision with quadratic probing — `(start + probe²) mod num_slots` —
> exactly what the assignment's hint suggests."

**Point at lines 45–59 (`add_server`) and 67–76 (`get_server`):**
> **SAY:** "`add_server` places all K virtual copies of a server on the
> ring. `get_server` takes a request ID, hashes it with H, and walks
> clockwise to the nearest occupied slot — that's the core routing rule
> from the appendix."

### [3:15] Prove it with tests

**RUN:**
```powershell
.\.venv\Scripts\python.exe -m pytest -v tests/test_server.py tests/test_consistent_hash.py
```
> **SAY:** "Instead of just trusting the code, we wrote unit tests covering
> both tasks — the hash formulas match the spec exactly, virtual servers
> land where expected, quadratic probing resolves collisions correctly, and
> the `/home`/`/heartbeat` routes behave as specified. All passing, no
> Docker daemon needed for these."

### [4:00] Handoff

> **SAY:** "So that's the server and the ring in isolation. Now over to
> [name] to show the load balancer that actually uses this ring to route
> real traffic."

---

## Presenter B — Task 3 (Load Balancer)

### [0:00] Intro + architecture

**SHOW:** `loadbalancer_service/app.py` (top of file), and `docker-compose.yml`

> **SAY:** "Thanks [name]. I'm covering Task 3 — the load balancer container
> that manages N server replicas and routes client traffic to them using
> that consistent hash ring."

**Point at `docker-compose.yml` lines 10–14:**
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
privileged: true
```
> **SAY:** "One important detail: the load balancer needs to spawn and kill
> sibling containers on failure or on scale up/down. To do that from inside
> a container, we mount the host's Docker socket and run this container as
> `privileged: true`, per the assignment's Appendix C."

**Point at `app.py` lines 24–28:**
```python
NETWORK_NAME = os.environ.get("LB_NETWORK", "net1")
SERVER_IMAGE = os.environ.get("SERVER_IMAGE", "loadbalancer-server:latest")
DEFAULT_N = int(os.environ.get("LB_N", "3"))
HEARTBEAT_INTERVAL = float(os.environ.get("LB_HEARTBEAT_INTERVAL", "2"))
HEARTBEAT_TIMEOUT = float(os.environ.get("LB_HEARTBEAT_TIMEOUT", "2"))
```
> **SAY:** "Defaults come from environment variables: network `net1`,
> server image `loadbalancer-server:latest`, N=3, and a 2-second heartbeat
> interval and timeout."

### [1:00] Build the images

**RUN:**
```powershell
docker build -t loadbalancer-server:latest .\server
docker compose build
docker images | Select-String "loadbalancer"
```
> **SAY:** "First we build the server image from Task 1, then the load
> balancer image itself."

### [1:45] Start the stack

**RUN:**
```powershell
docker compose up -d
docker compose ps
docker ps --filter "ancestor=loadbalancer-server:latest"
```
> **SAY:** "Bringing the stack up. The load balancer bootstraps N=3
> replicas itself on startup — you can see the `lb` container plus three
> server containers with randomly generated hostnames."

### [2:15] `/rep` — inspect replicas

**SHOW:** `app.py` lines 113–117

**RUN:**
```powershell
curl http://localhost:5000/rep
```
> **SAY:** "`/rep` just reports the current replica count and hostnames —
> straight off the ring."

### [2:35] Routed request

**SHOW:** `app.py` lines 171–193

**RUN:**
```powershell
curl http://localhost:5000/home
```
> **SAY:** "Any path other than the management endpoints gets routed
> through the ring. `route_request` generates a random request ID, asks
> the hash map for the owning server, and forwards the call. Notice it also
> special-cases a 404 from upstream into the spec's JSON error format —
> that's a real bug we caught during testing, where an unregistered path
> was leaking a raw Flask HTML 404 instead of this JSON."

### [3:00] `/add` — scale up

**SHOW:** `app.py` lines 120–142

**RUN:**
```powershell
curl -X POST http://localhost:5000/add `
  -H "Content-Type: application/json" `
  -d '{"n": 2, "hostnames": ["s_custom"]}'
```
> **SAY:** "`/add` scales up. We ask for 2 new replicas, one with a chosen
> hostname — the rest get randomly generated ones."

**RUN** (sanity check the spec requires):
```powershell
curl -X POST http://localhost:5000/add `
  -H "Content-Type: application/json" `
  -d '{"n": 1, "hostnames": ["a","b"]}'
```
> **SAY:** "And here's the validation the assignment asks for — if the
> hostname list is longer than `n`, it's a 400 error, not a crash."

### [3:45] `/rm` — scale down

**SHOW:** `app.py` lines 145–168

**RUN:**
```powershell
curl -X DELETE http://localhost:5000/rm `
  -H "Content-Type: application/json" `
  -d '{"n": 2, "hostnames": ["s_custom"]}'
```
> **SAY:** "`/rm` mirrors `/add` — removes named hosts first, then picks
> the rest randomly if `n` is larger than the named list, with the same
> length validation."

### [4:15] Unregistered path

**RUN:**
```powershell
curl -v http://localhost:5000/other
```
> **SAY:** "And requesting a path the backend doesn't implement returns the
> spec's exact JSON error with a 400, thanks to that upstream-404 check I
> mentioned."

### [4:35] Task 3's centerpiece — failure recovery

**SHOW:** `app.py` lines 84–110 (`_is_alive`, `_check_replicas_once`, `heartbeat_monitor`)

> **SAY:** "The core requirement of Task 3 is that N replicas are *always*
> maintained. A background thread polls every replica's `/heartbeat` every
> 2 seconds. If one fails to respond, it's deregistered from the ring and
> immediately replaced with a freshly spawned instance."

**RUN:**
```powershell
curl http://localhost:5000/rep
```
> **SAY:** "Let's note a hostname here — say `s7045` — and kill it to
> simulate a crash."

**RUN:**
```powershell
docker kill s7045
```

**RUN** (poll a couple times, a second or two apart):
```powershell
curl http://localhost:5000/rep
curl http://localhost:5000/rep
```
> **SAY:** "Within a couple of seconds, N is still 3 — `s7045` is gone, and
> a brand new hostname has already been spawned and registered, with no
> manual `/add` call. That's the self-healing behavior the assignment
> requires."

### [5:30] Handoff

> **SAY:** "That covers routing, scaling, and failure recovery for Task 3.
> Now [name] will show how well this actually distributes load under real
> traffic, for Task 4."

---

## Presenter C — Task 4 (Analysis) + Wrap-up

### [0:00] Intro + reset to a clean baseline

**SHOW:** `analysis/analyze.py`

> **SAY:** "Thanks [name]. I'm covering Task 4 — testing and analyzing how
> well the load balancer distributes traffic, and how it scales."

**RUN** (reset since the stack was scaled up/down in the last segment):
```powershell
docker compose down
docker ps -aq --filter "ancestor=loadbalancer-server:latest" | ForEach-Object { docker rm -f $_ }
docker compose up -d
Start-Sleep -Seconds 3
curl http://localhost:5000/rep
```
> **SAY:** "Resetting to a clean N=3 baseline before running the
> experiments."

### [0:45] A-1 and A-2

**Point at `analyze.py` argparse block (lines 135–138):**
```python
parser = argparse.ArgumentParser(description="Load balancer analysis (Task 4)")
parser.add_argument("--requests", type=int, default=10000, help="Requests to fire for A-1")
parser.add_argument("--skip-scaling", action="store_true", help="Skip the A-2 scaling experiment")
```
> **SAY:** "Our analysis script fires async requests using aiohttp and
> produces two experiments in one run: A-1 fires 10,000 requests at N=3
> and charts the load per replica; A-2 then scales N from 2 to 6, firing
> 10,000 requests at each step, charting the average load per replica as N
> grows."

**RUN:**
```powershell
.\.venv\Scripts\python.exe analysis\analyze.py --requests 10000
```
> **SAY:** "This takes a minute or two — it's really hitting the running
> Docker stack, not simulating anything."

**SHOW:** `analysis/results/a1_bar_chart.png`

> **SAY:** "For A-1 — with the assignment's specified hash functions — the
> load is very unevenly distributed. One replica absorbed about 94% of all
> 10,000 requests. That traces back to a property of `H(i) = i² + 2i + 17
> mod 512`: because 512 is a power of two, squaring modulo a power of two
> isn't a good bijection, so almost every request hash collapses onto a
> small cluster of slots near one server's virtual nodes."

**SHOW:** `analysis/results/a2_line_chart.png`

> **SAY:** "For A-2, average load per replica trends down as N grows — the
> right direction — but it isn't smooth; N=4's average is actually higher
> than N=3's. Same root cause: the request hash isn't exploring the ring
> uniformly, so adding a replica doesn't reliably redistribute load."

### [2:15] A-3 — already demonstrated

> **SAY:** "A-3 — failure recovery — [name] already demonstrated live in
> the Task 3 segment: killing a replica and watching the load balancer
> replace it within about a second while N stayed constant."

### [2:30] A-4 — modified hash function

**SHOW:** a diff of `consistent_hash.py`'s two hash functions (multiplicative hash)

> **SAY:** "For A-4 we swap in a different hash function to test whether
> the skew is caused by the ring logic or by the specific formulas. We used
> a multiplicative hash — `H(i) = 2654435761·i + 17 mod 512` — since an odd
> multiplier makes multiplication modulo a power of two a true bijection,
> unlike squaring."

**RUN:**
```powershell
docker compose build loadbalancer
docker compose down
docker ps -aq --filter "ancestor=loadbalancer-server:latest" | ForEach-Object { docker rm -f $_ }
docker compose up -d
Start-Sleep -Seconds 3
.\.venv\Scripts\python.exe analysis\analyze.py --requests 10000
Move-Item analysis\results\a1_bar_chart.png analysis\results\a4_bar_chart_modified.png -Force
Move-Item analysis\results\a2_line_chart.png analysis\results\a4_line_chart_modified.png -Force
```

**SHOW:** `analysis/results/a4_bar_chart_modified.png` and `a4_line_chart_modified.png` next to the originals

> **SAY:** "With the same ring and virtual-server code, just a
> better-mixing hash function, the spread drops from a 62-to-1 worst case
> down to about 1.7-to-1, and the scaling curve is much smoother. That
> confirms it: the mandated hash formulas — not our routing logic — are the
> cause of the skew in A-1 and A-2."

**RUN** (revert so the delivered code matches the spec):
```powershell
docker compose build loadbalancer
docker compose down
docker ps -aq --filter "ancestor=loadbalancer-server:latest" | ForEach-Object { docker rm -f $_ }
docker compose up -d
```
> **SAY:** "We've reverted `consistent_hash.py` back to the assignment's
> exact H and Φ — the delivered code you'll grade uses the specified
> formulas, and A-4's alternate hash was only for this comparison."

### [4:30] Wrap-up

**RUN** (teardown, on camera, to show it's clean):
```powershell
docker compose down
docker ps -aq --filter "ancestor=loadbalancer-server:latest" | ForEach-Object { docker rm -f $_ }
```

> **SAY:** "To summarize: Task 1 gives us a minimal, containerized server
> with `/home` and `/heartbeat`. Task 2 implements the consistent hash ring
> exactly per spec, with quadratic probing and virtual servers. Task 3 is
> the load balancer — routing, scaling via `/add`/`/rm`, and automatic
> failure recovery. And Task 4 shows the load balancer works correctly but
> that the *assigned* hash function skews load — which we diagnosed and
> confirmed with an alternate hash in A-4. Everything's version-controlled
> and shared at our GitHub repo, [repo URL on screen]. Thanks for watching."

---

## Appendix: tasks completed vs. assignment spec

| Task | Requirement | Status | Where |
|---|---|---|---|
| Task 1 | `/home` returns `Hello from Server: [ID]` JSON | ✅ | `server/server.py` |
| Task 1 | `/heartbeat` returns empty 200 | ✅ | `server/server.py` |
| Task 1 | Dockerfile for server | ✅ | `server/Dockerfile` |
| Task 2 | 512 slots, N=3, K=9 virtual servers | ✅ | `loadbalancer_service/consistent_hash.py` |
| Task 2 | `H(i) = i² + 2i + 17`, `Φ(i,j) = i² + j² + 2j + 25` | ✅ | `loadbalancer_service/consistent_hash.py` |
| Task 2 | Collision handling via probing | ✅ (quadratic) | `_probe` in `consistent_hash.py` |
| Task 3 | `/rep` GET | ✅ | `loadbalancer_service/app.py` |
| Task 3 | `/add` POST with validation | ✅ | `loadbalancer_service/app.py` |
| Task 3 | `/rm` DELETE with validation | ✅ | `loadbalancer_service/app.py` |
| Task 3 | `/<path>` routed via consistent hashing | ✅ | `loadbalancer_service/app.py` |
| Task 3 | Maintains N replicas on failure | ✅ (heartbeat monitor thread) | `loadbalancer_service/app.py` |
| Task 3 | Dockerfile, docker-compose.yml, Makefile | ✅ | `loadbalancer_service/Dockerfile`, `docker-compose.yml`, `Makefile` |
| Task 4 | A-1: 10k requests at N=3, bar chart | ✅ | `analysis/analyze.py`, `analysis/results/a1_bar_chart.png` |
| Task 4 | A-2: N=2→6, line chart of average load | ✅ | `analysis/analyze.py`, `analysis/results/a2_line_chart.png` |
| Task 4 | A-3: endpoint tests + failure recovery demo | ✅ | Demonstrated live (Segment 2) |
| Task 4 | A-4: modified hash functions, re-report A-1/A-2 | ✅ | `analysis/results/a4_*_modified.png` |

## Note on individual contribution

The assignment states commit logs are inspected to award marks per group
member. If each of the 3 presenters hasn't already committed under their own
GitHub account, have each person make at least one real commit to their
segment's files (`server/`, `loadbalancer_service/`, or `analysis/`) before
the deadline — not just narrate ownership in the video.
