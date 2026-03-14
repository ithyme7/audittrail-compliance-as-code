import csv
import os
import time

import audittrail
from audittrail import RiskLevel, trace_inference


def run_benchmark(mode: str, n_events: int = 10000):
    os.environ["AUDITTRAIL_MODE"] = mode
    audittrail._CONFIG["initialized"] = False
    audittrail.init(project=f"bench-{mode}", risk_level=RiskLevel.HIGH, output_dir="./demo_output")

    @trace_inference(require_human_review_threshold=0.85)
    def dummy_inference(x):
        return [0.9, 0.1]

    print(f"Start benchmark ({mode.upper()}) with {n_events} events...")
    start_time = time.time()
    for _ in range(n_events):
        dummy_inference([1.0, 2.0])
    audittrail.flush()
    duration = time.time() - start_time
    throughput = n_events / duration
    print(f"Done. Time: {duration:.2f}s | Throughput: {throughput:.0f} events/sec\n")
    return duration, throughput


def generate_plot(results):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Tip: install matplotlib (pip install matplotlib) to generate a PNG plot.")
        return

    modes = [r[0] for r in results]
    throughputs = [r[2] for r in results]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(modes, throughputs, color=["#e74c3c", "#2ecc71"])
    plt.title("AuditTrail SDK: Sync vs Async Performance", fontsize=14, fontweight="bold")
    plt.ylabel("Throughput (Events / Second)", fontsize=12)
    plt.xlabel("Log Mode", fontsize=12)
    plt.ylim(0, max(throughputs) * 1.2)

    for bar in bars:
        yval = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            yval + (max(throughputs) * 0.02),
            f"{int(yval)} ev/s",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=11,
        )

    plt.tight_layout()
    plt.savefig("benchmark_plot.png", dpi=300)
    print("Plot saved to benchmark_plot.png")


if __name__ == "__main__":
    n_events = 10000
    results = []
    for mode in ["sync", "async"]:
        dur, tp = run_benchmark(mode, n_events)
        results.append((mode.upper(), dur, tp))

    csv_path = "benchmark_results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Mode", "Duration_sec", "Throughput_events_per_sec"])
        for r in results:
            writer.writerow(r)
    print(f"Data saved to {csv_path}")

    generate_plot(results)
