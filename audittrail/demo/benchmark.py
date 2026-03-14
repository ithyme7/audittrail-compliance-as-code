import os
import time

import audittrail
from audittrail import RiskLevel, trace_inference


def run_benchmark(mode: str, n_events: int = 10000) -> None:
    os.environ["AUDITTRAIL_MODE"] = mode
    audittrail._CONFIG["initialized"] = False
    audittrail.init(project=f"bench-{mode}", risk_level=RiskLevel.HIGH, output_dir="./demo_output")

    @trace_inference(require_human_review_threshold=0.85)
    def dummy_inference(x):
        return [0.9, 0.1]

    print(f"Start benchmark ({mode}) with {n_events} events...")
    start_time = time.time()
    for _ in range(n_events):
        dummy_inference([1.0, 2.0])
    audittrail.flush()
    duration = time.time() - start_time
    throughput = n_events / duration
    print(f"Done. Time: {duration:.2f}s | Throughput: {throughput:.0f} events/sec\n")


if __name__ == "__main__":
    run_benchmark("sync")
    run_benchmark("async")
