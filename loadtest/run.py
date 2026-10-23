import asyncio, aiohttp, time, json, statistics, sys, csv, os

URL = os.getenv("TARGET", "http://localhost:8000/work")
STAGES = [100, 1000, 5000, 10000]
CONCURRENCY = int(os.getenv("CONCURRENCY", "200"))
CLIENT_TIMEOUT = 5

def pct(data, p):
    data = sorted(data)
    return data[min(len(data) - 1, int(len(data) * p / 100))] if data else 0

async def one(session, sem, lat, errs):
    async with sem:
        t0 = time.perf_counter()
        try:
            async with session.get(URL) as r:
                await r.read()
                if r.status != 200:
                    errs.append(r.status); return
        except Exception as e:
            errs.append(type(e).__name__); return
        lat.append((time.perf_counter() - t0) * 1000)

async def stage(total):
    lat, errs = [], []
    sem = asyncio.Semaphore(min(total, CONCURRENCY))
    conn = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=CLIENT_TIMEOUT)) as s:
        t0 = time.perf_counter()
        await asyncio.gather(*[one(s, sem, lat, errs) for _ in range(total)])
        wall = time.perf_counter() - t0
    return {
        "requests": total,
        "avg_ms": round(statistics.mean(lat), 1) if lat else None,
        "p50_ms": round(pct(lat, 50), 1), "p95_ms": round(pct(lat, 95), 1), "p99_ms": round(pct(lat, 99), 1),
        "failed": len(errs),
        "fail_pct": round(100 * len(errs) / total, 2),
        "throughput_rps": round(len(lat) / wall, 1),
        "duration_s": round(wall, 2),
    }

async def main():
    results = []
    print(f"Target: {URL} | concurrency: {CONCURRENCY}\n")
    hdr = f"{'Requests':>9} {'Avg ms':>8} {'p95 ms':>8} {'p99 ms':>8} {'Failed':>7} {'Fail %':>7} {'Req/s':>8}"
    print(hdr); print("-" * len(hdr))
    for n in STAGES:
        r = await stage(n); results.append(r)
        print(f"{r['requests']:>9} {r['avg_ms']:>8} {r['p95_ms']:>8} {r['p99_ms']:>8} {r['failed']:>7} {r['fail_pct']:>7} {r['throughput_rps']:>8}")
        await asyncio.sleep(2)
    os.makedirs("results", exist_ok=True)
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    json.dump(results, open(f"results/{tag}.json", "w"), indent=2)
    with open(f"results/{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    print(f"\nSaved results/{tag}.json and results/{tag}.csv")

asyncio.run(main())
