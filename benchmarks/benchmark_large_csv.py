from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

from damicore import ExecutionConfig, ResourceLimits, estimate, run
from synthetic_data import generate_csv


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1_000)
    parser.add_argument("--target-bytes", type=int, default=2_147_483_648)
    parser.add_argument("--skip-large", action="store_true")
    arguments = parser.parse_args()
    arguments.directory.mkdir(parents=True, exist_ok=True)
    measurements: dict[str, object] = {}
    if not arguments.skip_large:
        large_rows = math.ceil(arguments.target_bytes / (64 * 16))
        large_path = generate_csv(
            arguments.directory / "large-64-columns.csv",
            rows=large_rows,
            columns=64,
            clusters=4,
            seed=42,
        )
        large_preview = estimate(large_path, split="columns")
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        if large_path.stat().st_size < arguments.target_bytes * 0.9:
            raise RuntimeError("large benchmark CSV did not reach 90% of target size")
        if peak_rss > 1_610_612_736:
            raise RuntimeError("large preflight exceeded the 1.5 GiB RSS budget")
        measurements["large_preflight"] = {
            "input_bytes": large_preview.input_size_bytes,
            "peak_rss_bytes": peak_rss,
        }
    for columns in (16, 32, 64, 128):
        csv_path = generate_csv(
            arguments.directory / f"benchmark-{columns}.csv",
            rows=arguments.rows,
            columns=columns,
            clusters=4,
            seed=42,
        )
        execution = ExecutionConfig(
            workers=1,
            limits=ResourceLimits(max_objects=1_000),
        )
        started = time.monotonic()
        preview = estimate(csv_path, execution=execution)
        result = run(
            csv_path,
            output_dir=arguments.directory / f"run-{columns}",
            progress=False,
            execution=execution,
        )
        result.close()
        measurements[f"algorithm_{columns}"] = {
            "seconds": time.monotonic() - started,
            "input_bytes": preview.input_size_bytes,
            "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
    print(json.dumps(measurements, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
