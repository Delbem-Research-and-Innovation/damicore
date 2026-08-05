from __future__ import annotations

import argparse
import json
import math
import resource
import sys
import time
from pathlib import Path

from damicore import ExecutionConfig, ResourceLimits, estimate, run
from synthetic_data import generate_csv

# Object counts required by specification section 24.4.
OBJECT_COUNTS = (100, 250, 500, 1_000)


def _directory_bytes(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def _peak_rss_bytes() -> int:
    # ru_maxrss is KiB on Linux; every measurement below reports bytes so the two benchmarks
    # in this file stay comparable.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1_000)
    parser.add_argument("--target-bytes", type=int, default=2_147_483_648)
    # Specification section 24.4 defines two benchmarks with different costs: the large
    # normalization measurement needs a multi-gigabyte working set, while the object sweep is
    # minutes of CPU. One axis rather than two skip flags, so "neither" cannot be requested.
    parser.add_argument(
        "--select",
        choices=("large", "sweep", "both"),
        default="both",
        help="which of the two specified benchmarks to run",
    )
    parser.add_argument(
        "--objects",
        type=int,
        nargs="+",
        default=OBJECT_COUNTS,
        help=(
            "object counts to sweep; defaults to the counts required by specification "
            "section 24.4. A caller that narrows this is trading coverage for wall time."
        ),
    )
    arguments = parser.parse_args()
    run_large: bool = arguments.select in ("large", "both")
    run_sweep: bool = arguments.select in ("sweep", "both")
    if run_sweep and sorted(arguments.objects) != sorted(OBJECT_COUNTS):
        print(
            f"note: sweeping {sorted(arguments.objects)} instead of the "
            f"specified {list(OBJECT_COUNTS)}",
            file=sys.stderr,
        )
    arguments.directory.mkdir(parents=True, exist_ok=True)
    measurements: dict[str, object] = {}
    if run_large:
        large_rows = math.ceil(arguments.target_bytes / (64 * 16))
        large_path = generate_csv(
            arguments.directory / "large-64-columns.csv",
            rows=large_rows,
            columns=64,
            clusters=4,
            seed=42,
        )
        large_preview = estimate(large_path, split="columns")
        peak_rss = _peak_rss_bytes()
        if large_path.stat().st_size < arguments.target_bytes * 0.9:
            raise RuntimeError("large benchmark CSV did not reach 90% of target size")
        if peak_rss > 1_610_612_736:
            raise RuntimeError("large preflight exceeded the 1.5 GiB RSS budget")
        measurements["large_preflight"] = {
            "input_bytes": large_preview.input_size_bytes,
            "peak_rss_bytes": peak_rss,
        }
    for objects in sorted(arguments.objects) if run_sweep else ():
        csv_path = generate_csv(
            arguments.directory / f"benchmark-{objects}.csv",
            rows=arguments.rows,
            columns=objects,
            clusters=4,
            seed=42,
        )
        execution = ExecutionConfig(
            workers=1,
            limits=ResourceLimits(max_objects=max(objects, 1_000)),
        )
        run_dir = arguments.directory / f"run-{objects}"
        started = time.monotonic()
        preview = estimate(csv_path, execution=execution)
        result = run(
            csv_path,
            output_dir=run_dir,
            progress=False,
            execution=execution,
        )
        result.close()
        seconds = time.monotonic() - started
        # Specification section 24.4 requires time, disk, RSS and pairs per second.
        measurements[f"algorithm_{objects}"] = {
            "object_count": preview.object_count,
            "pair_count": preview.pair_count,
            "seconds": seconds,
            "pairs_per_second": preview.pair_count / seconds if seconds > 0 else 0.0,
            "input_bytes": preview.input_size_bytes,
            "run_disk_bytes": _directory_bytes(run_dir),
            "peak_rss_bytes": _peak_rss_bytes(),
        }
    print(json.dumps(measurements, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
