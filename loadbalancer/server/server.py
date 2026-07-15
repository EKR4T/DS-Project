"""
Backend web server (Assignment 1, Task 1).

Each replica is just this Flask app running in its own container; the
SERVER_ID environment variable (set per-container by the load balancer when
it spawns the replica) is what makes /home distinguish one replica from
another.
"""
import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/home", methods=["GET"])
def home():
    server_id = os.environ.get("SERVER_ID", "unknown")
    return jsonify(message=f"Hello from Server: {server_id}", status="successful"), 200


@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    return "", 200


if __name__ == "__main__":
    # threaded=True: Flask's dev server is single-threaded by default, which
    # would serialize every request through this replica - defeating the
    # concurrent/async request handling the assignment requires.
    app.run(host="0.0.0.0", port=5000, threaded=True)
