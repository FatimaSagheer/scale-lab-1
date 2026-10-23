 const express = require('express');
const path = require('path');
const app = express();

const cfg = {
  pool: Number(process.env.DB_POOL_SIZE || 10),
  queryMs: Number(process.env.DB_QUERY_MS || 50),
  timeoutMs: Number(process.env.POOL_WAIT_TIMEOUT_MS || 500),
  rate: 0,
};

let busy = 0;
const waiters = [];
const slots = Array(100).fill(null);   // slots[k] = start time of the request held by slot k, or null if free
const stats = { served: 0, failed: 0, lat: [], done: [] };

function acquire() {
  return new Promise((resolve) => {
    if (busy < cfg.pool) { busy++; return resolve(true); }
    const w = { resolve };
    w.timer = setTimeout(() => {
      const i = waiters.indexOf(w);
      if (i >= 0) waiters.splice(i, 1);
      resolve(false);
    }, cfg.timeoutMs);
    waiters.push(w);
  });
}
function release() {
  busy--;
  while (waiters.length && busy < cfg.pool) {
    const w = waiters.shift(); clearTimeout(w.timer); busy++; w.resolve(true);
  }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

app.get('/work', async (req, res) => {
  const t0 = Date.now();
  if (!(await acquire())) { stats.failed++; return res.status(503).json({ error: 'db pool exhausted' }); }
  const slot = slots.findIndex((s) => s === null);
  if (slot >= 0) slots[slot] = Date.now();
  try {
    await sleep(cfg.queryMs);
    res.json({ ok: true });
    const now = Date.now();
    stats.served++; stats.lat.push(now - t0); stats.done.push(now);
    if (stats.lat.length > 200) stats.lat.shift();
  } finally { if (slot >= 0) slots[slot] = null; release(); }
});

app.get('/stats', (req, res) => {
  const now = Date.now();
  while (stats.done.length && stats.done[0] < now - 1000) stats.done.shift();
  const avg = stats.lat.length ? stats.lat.reduce((a, b) => a + b, 0) / stats.lat.length : 0;
  const last = slots.findLastIndex((s) => s !== null);
  const slotAges = slots.slice(0, Math.max(cfg.pool, last + 1)).map((t) => (t === null ? -1 : now - t));
  res.json({ ...cfg, busy, slots: slotAges, queue: waiters.length, served: stats.served, failed: stats.failed,
             throughput: stats.done.length, avgLatencyMs: Math.round(avg), loadRunning: !!loader });
});

app.get('/config', (req, res) => {
  const { pool, timeout, rate } = req.query;
  if (pool) cfg.pool = Math.max(1, Math.min(100, Number(pool)));
  if (timeout) cfg.timeoutMs = Math.max(50, Number(timeout));
  if (rate) cfg.rate = Math.max(0, Math.min(2000, Number(rate)));
  while (waiters.length && busy < cfg.pool) { const w = waiters.shift(); clearTimeout(w.timer); busy++; w.resolve(true); }
  res.json(cfg);
});

app.get('/reset', (req, res) => {
  stats.served = 0; stats.failed = 0; stats.lat = []; stats.done = [];
  res.json({ ok: true });
});

// Built-in load generator: sends REAL HTTP requests to /work at cfg.rate per second
let loader = null;
function startLoad() {
  if (loader) return;
  let carry = 0;
  loader = setInterval(() => {
    carry += cfg.rate * 0.05;
    const n = Math.floor(carry); carry -= n;
    for (let i = 0; i < n; i++) fetch('http://localhost:8000/work').then((r) => r.arrayBuffer()).catch(() => {});
  }, 50);
}
function stopLoad() { clearInterval(loader); loader = null; }
app.get('/load/start', (req, res) => { startLoad(); res.json({ running: true }); });
app.get('/load/stop', (req, res) => { stopLoad(); res.json({ running: false }); });

app.use(express.static(path.join(__dirname, '..', 'public')));
app.listen(8000, () => console.log('Open http://localhost:8000  |  pool=' + cfg.pool));