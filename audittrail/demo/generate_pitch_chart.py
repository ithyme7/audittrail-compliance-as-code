import csv
import os

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Install matplotlib first: pip install matplotlib")
    raise SystemExit(1)


def create_pitch_chart(
    csv_file: str = "benchmark_results.csv", output_file: str = "pitch_ready_chart.png"
) -> None:
    if not os.path.exists(csv_file):
        print(f"File not found: {csv_file}. Run benchmark.py first.")
        return

    modes, throughputs = [], []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            modes.append(row["Mode"])
            throughputs.append(float(row["Throughput_events_per_sec"]))

    if len(modes) < 2 or "SYNC" not in modes or "ASYNC" not in modes:
        print("Not enough data to compare SYNC vs ASYNC.")
        return

    sync_tp = throughputs[modes.index("SYNC")]
    async_tp = throughputs[modes.index("ASYNC")]
    multiplier = async_tp / sync_tp if sync_tp > 0 else 0.0

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(9, 6))

    colors = ["#2C3E50", "#27AE60"]
    bars = ax.bar(modes, throughputs, color=colors, width=0.5, edgecolor="none", zorder=3)

    ax.set_title(
        "AuditTrail SDK: Log Verwerkingssnelheid",
        fontsize=18,
        fontweight="bold",
        color="#333333",
        pad=20,
        loc="left",
    )
    ax.set_ylabel("Events per seconde", fontsize=12, fontweight="bold", color="#555555")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#DDDDDD")
    ax.grid(axis="y", linestyle="--", alpha=0.7, zorder=0)

    for bar in bars:
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval + (max(throughputs) * 0.02),
            f"{int(yval):,}",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=12,
            color="#333333",
        )

    props = dict(boxstyle="round,pad=0.8", facecolor="#E8F8F5", edgecolor="#27AE60", alpha=0.9)
    ax.text(
        0.95,
        0.95,
        f"\N{FIRE} {multiplier:.1f}x Sneller\nmet Async Batching!",
        transform=ax.transAxes,
        fontsize=14,
        fontweight="bold",
        color="#196F3D",
        verticalalignment="top",
        horizontalalignment="right",
        bbox=props,
        zorder=5,
    )

    fig.text(
        0.02,
        0.02,
        "Bron: AuditTrail Compliance-as-Code SDK Benchmark",
        fontsize=9,
        color="#888888",
        style="italic",
    )

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1)
    plt.savefig(output_file, dpi=300, transparent=False, facecolor="white")
    print(f"Pitch-ready chart saved to {output_file}")


if __name__ == "__main__":
    create_pitch_chart()
