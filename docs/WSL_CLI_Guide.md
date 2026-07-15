# WSL CLI Guide — Load Balancer Project, Mutual Exclusion (A6), Web Services (A8)

This is a copy-paste-ready command reference for doing the Distributed Systems work in **WSL**,
while writing/reviewing code in **VS Code** on Windows. Two workflows are covered for getting
code into WSL:

- **Fast path (recommended):** edit files in VS Code on Windows, run them straight from WSL
  because your `D:\KIPWORK\DS-Project` folder is already visible inside WSL at
  `/mnt/d/KIPWORK/DS-Project` — no copy/paste needed.
- **nano path:** if you want to type/paste code directly inside the WSL terminal (e.g. testing
  a snippet quickly, or working on a machine without the repo checked out), use `nano` as shown
  below.

---

## 0. One-time WSL setup

Open **Windows Terminal / PowerShell** (not WSL yet):

```powershell
wsl --install -d Ubuntu
wsl --set-default-version 2
```

Restart if prompted, create your Ubuntu username/password, then all commands below run **inside
the WSL Ubuntu shell**.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget unzip nano tmux python3 python3-pip
```

Install Java (default-jdk is fine for Assignment 6; Assignment 8 needs JDK 8 specifically — see
section 2):

```bash
sudo apt install -y default-jdk
java -version
javac -version
```

Install Docker (needed for the Load Balancer project, section 3) — from the assignment's own
appendix:

```bash
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # then close & reopen the WSL terminal
```

> Docker Desktop for Windows with the "WSL2 integration" enabled also works instead of the
> `apt` install above — if you already have Docker Desktop, just tick Ubuntu under
> Settings → Resources → WSL Integration and skip straight to `docker version` in WSL.

### VS Code ↔ WSL (fast path)

From inside WSL, in your project folder, this opens VS Code (Windows) connected to WSL — you
edit and save normally in VS Code, and it's instantly available to `javac`/`java`/`docker` in
the WSL terminal, no copying:

```bash
cd /mnt/d/KIPWORK/DS-Project
code .
```

(Install the "WSL" extension in VS Code once if `code .` doesn't open it automatically.)

---

## 1. Lab: Mutual Exclusion — Assignment 6 (Token Ring)

Your files already exist at `labs/Mutual Exclusion/`: `TokenServer1.java`, `TokenClient1.java`,
`TokenClient2.java`. This is a 3-process UDP token-ring demo — one server + two clients, all on
`localhost`, needing **3 separate terminals** running at once.

### Fast path (files already in the repo)

```bash
cd "/mnt/d/KIPWORK/DS-Project/labs/Mutual Exclusion"
javac *.java
```

Open 3 WSL terminal panes/tabs (Windows Terminal: `Ctrl+Shift+D` to duplicate the tab, or use
`tmux`), `cd` into the same folder in each, then run one process per pane:

```bash
# Terminal 1
cd "/mnt/d/KIPWORK/DS-Project/labs/Mutual Exclusion" && java TokenServer1
```

```bash
# Terminal 2
cd "/mnt/d/KIPWORK/DS-Project/labs/Mutual Exclusion" && java TokenClient1
```

```bash
# Terminal 3
cd "/mnt/d/KIPWORK/DS-Project/labs/Mutual Exclusion" && java TokenClient2
```

`TokenClient1` and `TokenClient2` will each prompt `Do you want to enter the Data –> YES/NO`
when they hold the token — answer in that terminal to pass the token around and send data to
`TokenServer1` (listening on UDP port 8000).

Optional — one command, three panes, via `tmux` (handy for screenshots for your submission):

```bash
cd "/mnt/d/KIPWORK/DS-Project/labs/Mutual Exclusion"
tmux new-session -d -s mutex "java TokenServer1" \; \
  split-window -h "java TokenClient1" \; \
  split-window -v "java TokenClient2" \; \
  attach
```
(`Ctrl+B` then `D` to detach, `tmux attach -t mutex` to come back, `tmux kill-session -t mutex` to stop.)

### nano path (typing/pasting the code manually instead)

```bash
mkdir -p ~/ds-labs/mutex && cd ~/ds-labs/mutex
nano TokenServer1.java
```
Paste (in Windows Terminal: right-click, or `Ctrl+Shift+V`) → `Ctrl+O` then `Enter` to save →
`Ctrl+X` to exit. Repeat for `TokenClient1.java` and `TokenClient2.java`, then:

```bash
javac *.java
java TokenServer1      # in its own terminal
java TokenClient1      # in another terminal
java TokenClient2      # in a third terminal
```

---

## 2. Lab: Web Services — Assignment 8 (NetBeans + GlassFish workaround)

The lab manual assumes **NetBeans IDE + GlassFish Server** to build/deploy a JAX-WS
`@WebService`. Neither has a comfortable WSL/Linux CLI story, so the workaround is to **skip
the application server entirely** and self-host the endpoint from plain `java`, using
`javax.xml.ws.Endpoint.publish(...)` — this is the same idea shown in the referenced video
(https://youtu.be/0z-HvSfr-M4): no IDE, no app-server install, just JDK + `javac`/`java`.

**Key catch:** `javax.jws` / `javax.xml.ws` (JAX-WS) were removed from the JDK starting with
Java 11. Use **JDK 8** for this lab specifically so the annotations and `Endpoint` class work
with zero extra libraries.

### 2.1 Install JDK 8 alongside your default JDK

```bash
sudo apt install -y openjdk-8-jdk
sudo update-alternatives --config java      # pick the 1.8.x entry
sudo update-alternatives --config javac     # pick the 1.8.x entry
java -version   # confirm it now reports 1.8.x
```
(Switch back later with the same two `update-alternatives --config` commands and picking the
newer JDK entry.)

### 2.2 Project files

Your existing `labs/Web Services/Calculator.java` is the service class stub
(`package com.learn.ws;`) but has no `@WebService`/`@WebMethod` annotations and no way to start
a listener yet. Update it and add a small publisher class:

```bash
cd "/mnt/d/KIPWORK/DS-Project/labs/Web Services"
mkdir -p com/learn/ws
```

`com/learn/ws/Calculator.java` (annotated service — edit in VS Code, or `nano com/learn/ws/Calculator.java`):
```java
package com.learn.ws;

import javax.jws.WebService;
import javax.jws.WebMethod;
import javax.jws.WebParam;

@WebService(serviceName = "Calculator")
public class Calculator {

    @WebMethod(operationName = "add")
    public int add(@WebParam(name = "a") int a, @WebParam(name = "b") int b) {
        return a + b;
    }
}
```

`com/learn/ws/CalculatorPublisher.java` (replaces GlassFish — this *is* the server):
```java
package com.learn.ws;

import javax.xml.ws.Endpoint;

public class CalculatorPublisher {
    public static void main(String[] args) {
        Endpoint.publish("http://localhost:9999/ws/calculator", new Calculator());
        System.out.println("Service running at http://localhost:9999/ws/calculator?wsdl");
    }
}
```

### 2.3 Compile & run (this replaces "Deploy on GlassFish" in NetBeans)

```bash
cd "/mnt/d/KIPWORK/DS-Project/labs/Web Services"
javac com/learn/ws/*.java
java com.learn.ws.CalculatorPublisher
```

Leave that running. Because WSL2 auto-forwards `localhost` ports to Windows, you can open a
normal Windows browser and hit:

```
http://localhost:9999/ws/calculator?wsdl
```

to see the generated WSDL — this is your proof-of-deployment screenshot instead of the
NetBeans "Tester page".

### 2.4 Consume it (the "write a distributed application to consume the web service" part)

In a **second** WSL terminal, generate a client stub from the WSDL with `wsimport` (ships with
JDK 8), then write a tiny client:

```bash
cd "/mnt/d/KIPWORK/DS-Project/labs/Web Services"
mkdir -p client
wsimport -keep -p com.learn.ws.client -d client http://localhost:9999/ws/calculator?wsdl
```

`CalculatorClient.java`:
```java
import com.learn.ws.client.Calculator;
import com.learn.ws.client.CalculatorService;

public class CalculatorClient {
    public static void main(String[] args) {
        Calculator calc = new CalculatorService().getCalculatorPort();
        System.out.println("5 + 7 = " + calc.add(5, 7));
    }
}
```

```bash
javac -cp client CalculatorClient.java
java -cp .:client CalculatorClient
```

Alternative quick check without writing a client at all — raw SOAP over `curl` (useful as a
screenshot of "SOAP Request/Response" like the NetBeans tester shows):

```bash
curl -s -X POST http://localhost:9999/ws/calculator \
  -H "Content-Type: text/xml;charset=UTF-8" \
  -d '<?xml version="1.0" encoding="UTF-8"?>
<S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/">
  <S:Body>
    <ns2:add xmlns:ns2="http://ws.learn.com/">
      <a>5</a><b>7</b>
    </ns2:add>
  </S:Body>
</S:Envelope>'
```

---

## 3. Programming Project: Customizable Load Balancer (Assignment 1)

The project is fully scaffolded at `loadbalancer/` (Task 1 server, Task 2 consistent
hashing, Task 3 load balancer, Task 4 analysis script, plus a `pytest` suite) — see
[`../loadbalancer/README.md`](../loadbalancer/README.md) for the full design write-up.
This section is just the day-to-day CLI workflow.

### Run the unit tests (no Docker required)

```bash
cd /mnt/d/KIPWORK/DS-Project/loadbalancer
pip3 install -r requirements-dev.txt
pytest -v
# or:
make test
```

### Build & run the stack

```bash
cd /mnt/d/KIPWORK/DS-Project/loadbalancer
make up              # builds both images, starts the load balancer (bootstraps N=3 replicas)
docker compose ps
docker compose logs -f loadbalancer     # Ctrl+C to stop tailing
```

Hit the endpoints with `curl`:

```bash
curl http://localhost:5000/rep
curl -X POST http://localhost:5000/add -H "Content-Type: application/json" \
  -d '{"n": 2, "hostnames": ["s4","s5"]}'
curl -X DELETE http://localhost:5000/rm -H "Content-Type: application/json" \
  -d '{"n": 1, "hostnames": ["s4"]}'
curl http://localhost:5000/home
```

### Load-testing for the Task 4 analysis (bar/line charts)

With the stack still running from `make up`:

```bash
cd /mnt/d/KIPWORK/DS-Project/loadbalancer
pip3 install -r requirements-dev.txt aiohttp matplotlib
make analyze
# or directly: python3 analysis/analyze.py --requests 10000
```

Charts are written to `loadbalancer/analysis/results/` (`a1_bar_chart.png`,
`a2_line_chart.png`).

Tear down when done:
```bash
make down
```

---

## Quick reference

| Task | Command |
|---|---|
| Open project in VS Code from WSL | `code .` (run from inside `/mnt/d/KIPWORK/DS-Project`) |
| Compile all `.java` in a folder | `javac *.java` |
| Run a class | `java ClassName` |
| New file via nano | `nano filename.java` → paste → `Ctrl+O`,`Enter` → `Ctrl+X` |
| Switch JDK version | `sudo update-alternatives --config java` (and `javac`) |
| 3-pane tmux session | `tmux new-session -d -s name "cmd1" \; split-window -h "cmd2" \; split-window -v "cmd3" \; attach` |
| Docker build+run | `docker compose build && docker compose up -d` |
