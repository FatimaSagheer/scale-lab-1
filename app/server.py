import os, time, threading
from flask import Flask, jsonify

app = Flask(__name__)

DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_QUERY_MS = int(os.getenv("DB_QUERY_MS", "50"))
POOL_WAIT_TIMEOUT = float(os.getenv("POOL_WAIT_TIMEOUT", "0.5"))

pool = threading.BoundedSemaphore(DB_POOL_SIZE)

@app.get("/work")
def work():
    if not pool.acquire(timeout=POOL_WAIT_TIMEOUT):
        return jsonify(error="db pool exhausted"), 503
    try:
        time.sleep(DB_QUERY_MS / 1000)
        return jsonify(ok=True)
    finally:
        pool.release()

@app.get("/health")
def health():
    return "ok"
