# import os
# import time
# import csv
# import statistics
# from encryption_schemes import (
#     aesgcm_encrypt, aesgcm_decrypt,
#     chacha_encrypt, chacha_decrypt,
# )

# import platform
# import os

# print("Platform:", platform.platform())
# print("Processor:", platform.processor())
# print("Python version:", platform.python_version())

# def run_once(name, enc, dec, key, payload: bytes, n_ops: int) -> dict:
#     t0 = time.perf_counter()
#     for _ in range(n_ops):
#         nonce, ct = enc(key, payload)
#         _ = dec(key, nonce, ct)
#     t1 = time.perf_counter()

#     wall = t1 - t0
#     return {
#         "scheme": name,
#         "payload_bytes": len(payload),
#         "n_ops": n_ops,
#         "wall_s": wall,
#         "avg_ms_per_op": (wall / n_ops) * 1000.0,
#         "ops_per_s": n_ops / wall,
#     }

# def benchmark(payload_sizes, n_ops=3000, repeats=5):
#     aes_key = os.urandom(32)
#     chacha_key = os.urandom(32)

#     rows = []
#     for size in payload_sizes:
#         payload = b"a" * size
#         for _ in range(repeats):
#             rows.append(run_once("AES-GCM", aesgcm_encrypt, aesgcm_decrypt, aes_key, payload, n_ops))
#             rows.append(run_once("ChaCha20-Poly1305", chacha_encrypt, chacha_decrypt, chacha_key, payload, n_ops))
#     return rows

# def summarize(rows):
#     summary = []
#     schemes = sorted(set(r["scheme"] for r in rows))
#     sizes = sorted(set(r["payload_bytes"] for r in rows))

#     for s in schemes:
#         for size in sizes:
#             subset = [r for r in rows if r["scheme"] == s and r["payload_bytes"] == size]
#             avg_ms = statistics.mean(r["avg_ms_per_op"] for r in subset)
#             std_ms = statistics.pstdev(r["avg_ms_per_op"] for r in subset)
#             avg_ops = statistics.mean(r["ops_per_s"] for r in subset)
#             std_ops = statistics.pstdev(r["ops_per_s"] for r in subset)
#             summary.append({
#                 "scheme": s,
#                 "payload_bytes": size,
#                 "avg_ms_per_op_mean": avg_ms,
#                 "avg_ms_per_op_std": std_ms,
#                 "ops_per_s_mean": avg_ops,
#                 "ops_per_s_std": std_ops,
#                 "repeats": len(subset),
#             })
#     return summary

# def write_csv(path, rows):
#     with open(path, "w", newline="", encoding="utf-8") as f:
#         w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
#         w.writeheader()
#         w.writerows(rows)

# if __name__ == "__main__":
#     payload_sizes = [64, 256, 1024, 4096, 16384]
#     rows = benchmark(payload_sizes, n_ops=3000, repeats=5)
#     summary = summarize(rows)

#     write_csv("benchmark_raw.csv", rows)
#     write_csv("benchmark_summary.csv", summary)

#     print("Wrote benchmark_raw.csv and benchmark_summary.csv")
#     for r in summary:
#         print(r)

import os, time, platform, csv
from datetime import datetime
from encryption_schemes import aesgcm_encrypt, aesgcm_decrypt, chacha_encrypt, chacha_decrypt

PAYLOAD_SIZES = [64, 256, 1024, 4096, 16384]
N_OPS = int(os.getenv("N_OPS", "10000"))

ENV_LABEL = os.getenv("BENCH_ENV", "local")  # set to "render" in Render worker
OUT_CSV = os.getenv("BENCH_OUT", f"bench_{ENV_LABEL}.csv")

def run_scheme(name, enc_fn, dec_fn, key, payload_size, n_ops):
    plaintext = os.urandom(payload_size)
    t0 = time.perf_counter()
    for _ in range(n_ops):
        nonce, ct = enc_fn(key, plaintext)
        _ = dec_fn(key, nonce, ct)
    t1 = time.perf_counter()
    total = t1 - t0
    avg_ms = (total / n_ops) * 1000.0
    ops_s = n_ops / total
    bytes_s = payload_size * ops_s
    return total, avg_ms, ops_s, bytes_s

def main():
    import os as _os
    aes_key = _os.urandom(32)
    chacha_key = _os.urandom(32)

    meta = {
        "timestamp": datetime.utcnow().isoformat(),
        "env": ENV_LABEL,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
    }

    rows = []
    for size in PAYLOAD_SIZES:
        total, avg_ms, ops_s, bytes_s = run_scheme("AES-GCM", aesgcm_encrypt, aesgcm_decrypt, aes_key, size, N_OPS)
        rows.append({**meta, "scheme":"AES-GCM", "payload_bytes":size, "n_ops":N_OPS,
                     "total_s":total, "avg_ms":avg_ms, "ops_per_s":ops_s, "bytes_per_s":bytes_s})
        total, avg_ms, ops_s, bytes_s = run_scheme("ChaCha20-Poly1305", chacha_encrypt, chacha_decrypt, chacha_key, size, N_OPS)
        rows.append({**meta, "scheme":"ChaCha20-Poly1305", "payload_bytes":size, "n_ops":N_OPS,
                     "total_s":total, "avg_ms":avg_ms, "ops_per_s":ops_s, "bytes_per_s":bytes_s})

    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print("Wrote:", OUT_CSV)
    print("Env:", ENV_LABEL)
    print("Platform:", meta["platform"])
    # Print final summary for easy copy from logs
    for r in rows:
        print(r["env"], r["scheme"], r["payload_bytes"], f'avg_ms={r["avg_ms"]:.6f}', f'ops/s={r["ops_per_s"]:.1f}', f'bytes/s={r["bytes_per_s"]:.1f}')

if __name__ == "__main__":
    main()