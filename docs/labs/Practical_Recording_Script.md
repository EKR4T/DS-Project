# Practical Recording Script

Distributed Systems (ICS 4104) — Group 14, Emmanuel Keter (134976)
Use this as a read-along/action script while screen-recording the two practicals in WSL.
`[SAY]` = speak this to camera/mic. `[DO]` = type/run this or perform this action.
Keep terminal font large (Ctrl + / Ctrl -) and windows tiled before you hit record.

---

## 0. Opening Slate (both labs — ~20 sec)

`[SAY]`
> "Hello, my name is Emmanuel Keter, admission number 134976, Group 14, Distributed Systems ICS 4104.
> In this recording I'll demonstrate two practicals: first, Mutual Exclusion using the Token Ring
> Algorithm, and second, creation and consumption of a SOAP Web Service using Java JAX-WS. Both are
> implemented in a WSL Ubuntu environment."

---

## PART 1 — Mutual Exclusion (Token Ring Algorithm)

### 1.1 Theory (~30 sec)

`[SAY]`
> "In a distributed system, several processes may need to access a shared resource at the same time.
> Mutual exclusion guarantees only one process is in the critical section at once. The Token Ring
> algorithm arranges processes in a logical ring and circulates a single token — only the process
> holding the token may enter the critical section and send data to the server. Here I have one
> server, TokenServer1, and two clients, TokenClient1 and TokenClient2, communicating over UDP
> sockets on localhost."

### 1.2 Environment setup (~40 sec)

`[SAY]` "Let's set up the working directory and confirm the JDK."

`[DO]`
```bash
mkdir mutual-exclusion
cd mutual-exclusion
sudo apt install -y openjdk-17-jdk
sudo update-alternatives --config java
```
`[SAY]` "I'll select option 1 to use JDK 17."
`[DO]` type `1`, press Enter, then repeat for javac:
```bash
sudo update-alternatives --config javac
```
`[SAY]` "Same here — JDK 17 for the compiler."
`[DO]` type `1`, press Enter.

### 1.3 Code walkthrough (~90 sec)

`[SAY]` "Now let's look at the three source files I've already written."

`[DO]`
```bash
nano TokenServer1.java
```
`[SAY]` while scrolling through it:
> "TokenServer1 runs an infinite loop. Each iteration it creates a Server object, binds a
> DatagramSocket to port 8000 with `recPort`, and blocks on `recData()` until a UDP packet arrives.
> When a client sends data, the server reads the bytes into a String and prints `The message is`
> followed by the payload — that's the shared critical-section resource in this demo."
`[DO]` Ctrl+X to exit (no changes).

`[DO]`
```bash
nano TokenClient1.java
```
`[SAY]`
> "TokenClient1 holds the token first. It prompts 'Do you want to enter the Data -> YES/NO'. If I
> answer YES, it reads a line of input, forwards that data to TokenServer1 on port 8000 over a
> DatagramSocket, prints 'sending' then 'now sending', and afterwards passes the token on to
> TokenClient2. If I answer NO, it just goes to the else branch and passes the token along without
> entering the critical section."
`[DO]` Ctrl+X.

`[DO]`
```bash
nano TokenClient2.java
```
`[SAY]`
> "TokenClient2 is symmetric — it starts in receiving mode, waits for the token to arrive from
> Client1, then gets the same YES/NO prompt. Only whichever client currently holds the token can
> talk to the server; this is what enforces mutual exclusion here."
`[DO]` Ctrl+X.

### 1.4 Compilation (~15 sec)

`[SAY]` "Let's compile all three files together."

`[DO]`
```bash
javac *.java
tree
```
`[SAY]` "You can see the three .class files generated alongside the source, plus the token-passing
helper classes."

### 1.5 Execution (~90 sec)

`[SAY]` "I'll open three terminal tabs — one for the server, one for each client — and run them in
order."

`[DO]` Terminal tab 1:
```bash
java TokenServer1
```
`[SAY]` "The server is now listening on port 8000."

`[DO]` Terminal tab 2:
```bash
java TokenClient1
```
`[SAY]` "Client1 asks whether I want to enter the data. I'll say YES and type a message."
`[DO]` type `YES`, Enter, then type `Hello from Group 14`, Enter.
`[SAY]` "Notice it prints 'ready to send', then 'sending', then 'now sending' — and afterwards it
prompts again. This time I'll say NO to pass the token along without re-entering the critical
section."
`[DO]` type `NO`, Enter.

`[DO]` Terminal tab 3:
```bash
java TokenClient2
```
`[SAY]` "Client2 enters receiving mode, detects the incoming token, and now shows the same YES/NO
prompt. I'll answer YES and send a second message."
`[DO]` type `YES`, Enter, then type `Hello from Keter`, Enter.

`[SAY]` "Switching back to the server terminal — you can see it printed both messages: 'The message
is ClientOne....Hello from Group' and 'The message is ClientTwo....Hello from Ket', confirming each
client could only send while holding the token."

### 1.6 Conclusion (~20 sec)

`[SAY]`
> "This demonstrates the Token Ring Mutual Exclusion algorithm: the token circulated between the two
> clients, only the token holder could send to the shared server, and the message log confirms no
> two clients accessed the critical section simultaneously — so mutual exclusion was achieved and
> race conditions were prevented."

---

## PART 2 — Web Services (SOAP with JAX-WS)

### 2.1 Theory (~30 sec)

`[SAY]`
> "A web service lets applications communicate over a network using standard protocols like HTTP,
> XML, SOAP and WSDL. SOAP is an XML-based messaging protocol, and a SOAP service publishes its
> operations through a WSDL document that clients use to generate stubs automatically. Here I'll
> build a Calculator web service in Java JAX-WS that exposes an `add` operation, publish it with
> `Endpoint.publish()`, and consume it from a separate client generated via `wsimport`."

### 2.2 Environment setup (~40 sec)

`[SAY]` "First, set up the working directory and switch to JDK 8, which this JAX-WS setup needs."

`[DO]`
```bash
cd ~/distributed-systems/web-services
sudo update-alternatives --config java
sudo update-alternatives --config javac
java -version
javac -version
```
`[SAY]` "Confirmed — OpenJDK 1.8.0_492 for both runtime and compiler."

`[DO]`
```bash
mkdir -p com/learn/ws
tree
```

### 2.3 Code walkthrough (~90 sec)

`[DO]`
```bash
nano com/learn/ws/Calculator.java
```
`[SAY]`
> "This is the service class. It's annotated `@WebService(serviceName = "Calculator")`, and the
> `add` method is annotated `@WebMethod(operationName = "add")` with two `@WebParam`-annotated
> integers, `a` and `b`. It simply returns `a + b` — these annotations are what let JAX-WS expose it
> as a SOAP operation."
`[DO]` Ctrl+X.

`[DO]`
```bash
nano com/learn/ws/CalculatorPublisher.java
```
`[SAY]`
> "The publisher's main method calls `Endpoint.publish()`, binding the Calculator instance to
> `http://localhost:9999/ws/calculator`, and prints the WSDL URL. This replaces deploying to a
> GlassFish server — the JDK's built-in lightweight HTTP server hosts the endpoint directly."
`[DO]` Ctrl+X.

### 2.4 Compilation (~10 sec)

`[DO]`
```bash
javac com/learn/ws/*.java
tree
```
`[SAY]` "Calculator.class and CalculatorPublisher.class are generated."

### 2.5 Publish the service and generate client stubs (~60 sec)

`[DO]` Terminal tab 1:
```bash
java com.learn.ws.CalculatorPublisher
```
`[SAY]` "The service is now running and printing the WSDL URL at
`http://localhost:9999/ws/calculator?wsdl`."

`[DO]` Terminal tab 2:
```bash
mkdir -p client
wsimport \
  -keep \
  -p com.learn.ws.client \
  -d client \
  http://localhost:9999/ws/calculator?wsdl
```
`[SAY]` "wsimport parses the WSDL and generates the client-side stub classes — Calculator,
Calculator_Service, Add, AddResponse, and ObjectFactory — under `client/com/learn/ws/client`."

`[DO]`
```bash
curl -s http://localhost:9999/ws/calculator?wsdl | head -20
```
`[SAY]` "And here's a look at the raw WSDL XML itself — the port type, operation, and SOAP binding
that describe the `add` operation."

`[DO]`
```bash
tree
```

### 2.6 Client code walkthrough (~30 sec)

`[DO]`
```bash
nano CalculatorClient.java
```
`[SAY]`
> "The client imports the generated `Calculator` and `Calculator_Service` stub classes, gets a proxy
> via `new Calculator_Service().getCalculatorPort()`, and calls `calc.add(5, 7)` — that call is
> transparently marshalled into a SOAP request and sent to the running service."
`[DO]` Ctrl+X.

### 2.7 Compile and run the client (~20 sec)

`[DO]`
```bash
javac -cp client CalculatorClient.java
java -cp .:client CalculatorClient
```
`[SAY]` "And the output confirms it: '5 + 7 = 12' — computed remotely by the SOAP service and
returned to the client."

### 2.8 Conclusion (~20 sec)

`[SAY]`
> "This demonstrates creating and consuming a SOAP web service with Java JAX-WS: the Calculator
> service was published with `Endpoint.publish()`, its WSDL described the `add` operation, `wsimport`
> generated working client stubs from that WSDL, and the client successfully invoked the remote
> operation and received the correct result — showing communication between distributed
> components."

---

## Closing (~10 sec)

`[SAY]`
> "That concludes both practicals — Mutual Exclusion via Token Ring, and SOAP Web Services via
> JAX-WS. Thank you."

---

### Recording checklist
- [ ] Terminal font large enough to read on playback
- [ ] Each `nano` file scrolled slowly enough to read on camera before narrating
- [ ] Screen recorder capturing audio + all terminal windows (or switch full-screen per window)
- [ ] Server window kept visible/switched to after each client send, to show the log update live
- [ ] Trim dead air (package installs, `apt update`) in post-editing if the raw take runs long
