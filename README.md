# Distributed Systems (ICS 4104) — Coursework

This repository contains the programming project and lab assignments for the
Distributed Systems course.


## Programming project

**[Customizable Load Balancer](loadbalancer/README.md)** — a Dockerized load balancer
that distributes requests across backend replicas using consistent hashing, with a
full test suite and a Task 4 performance-analysis script. See
[`loadbalancer/README.md`](loadbalancer/README.md) for setup, usage, testing, and
deployment instructions.

## Labs

- **Mutual Exclusion (Assignment 6):** `labs/Mutual Exclusion/` — a 3-process
  UDP token-ring demo (`TokenServer1`, `TokenClient1`, `TokenClient2`).
- **Web Services (Assignment 8):** `labs/Web Services/` — a JAX-WS `Calculator`
  service, run without NetBeans/GlassFish (see the WSL guide below for the
  command-line workaround).

## Working in WSL

[`docs/WSL_CLI_Guide.md`](docs/WSL_CLI_Guide.md) has copy-paste-ready commands for
setting up WSL, running the Mutual Exclusion lab across multiple terminals,
self-hosting the Web Services lab without an IDE/app-server, and building/running
the Load Balancer project with Docker.

## License

[MIT](LICENSE)
