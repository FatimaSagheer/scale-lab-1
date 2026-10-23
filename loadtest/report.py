import json, glob, os
runs = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob("results/*.json"))}
colors = ["#378ADD", "#D85A30", "#1D9E75", "#BA7517"]

def bars(metric, label):
    mx = max((r[metric] or 0) for rs in runs.values() for r in rs) or 1
    out = f"<h3>{label}</h3>"
    for i, (name, rs) in enumerate(runs.items()):
        for r in rs:
            w = 100 * (r[metric] or 0) / mx
            out += (f"<div class='row'><span class='l'>{name} · {r['requests']:,} req</span>"
                    f"<div class='b' style='width:{w:.1f}%;background:{colors[i % 4]}'></div>"
                    f"<span class='v'>{r[metric]}</span></div>")
    return out

tables = ""
for name, rs in runs.items():
    tables += f"<h3>{name}</h3><table><tr><th>Requests<th>Avg ms<th>p95 ms<th>p99 ms<th>Failed<th>Fail %<th>Req/s"
    for r in rs:
        tables += f"<tr><td>{r['requests']:,}<td>{r['avg_ms']}<td>{r['p95_ms']}<td>{r['p99_ms']}<td>{r['failed']}<td>{r['fail_pct']}<td>{r['throughput_rps']}"
    tables += "</table>"

html = f"""<!doctype html><meta charset=utf-8><title>Load test report</title>
<style>body{{font-family:system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;margin-bottom:1rem}}td,th{{border:1px solid #ccc;padding:4px 10px;text-align:right}}
.row{{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:13px}}.l{{width:190px}}
.b{{height:14px;border-radius:3px}}.v{{font-variant-numeric:tabular-nums}}</style>
<h1>Load test report</h1>{tables}
{bars('avg_ms','Average response time (ms), lower is better')}
{bars('throughput_rps','Throughput (requests/sec), flat = capacity limit')}
{bars('failed','Failed requests')}"""
open("results/report.html", "w").write(html)
print("Wrote results/report.html")
