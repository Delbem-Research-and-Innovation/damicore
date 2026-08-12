from __future__ import annotations

import argparse
import json
import math
import resource
import sys
import time
from pathlib import Path

from damicore import ExecutionConfig, ResourceLimits, estimate, run
from damicore_normalizer import NormalizationConfig, normalize_csv
from synthetic_data import generate_csv

# Roughly geometric, because Neighbor Joining is cubic in the object count: each step costs
# several times the one before, so a linear sweep would spend all its time at the top end.
OBJECT_COUNTS = (100, 250, 500, 1_000)

# The budget: 1.5 GiB of peak RSS while normalizing the large input.
NORMALIZATION_RSS_BUDGET_BYTES = 1_610_612_736


def _directory_bytes(directory: Path) -> int:
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def _peak_rss_bytes() -> int:
    # ru_maxrss is KiB on Linux; every measurement below reports bytes so the two benchmarks
    # in this file stay comparable. It is a high-water mark for the whole process, so a value
    # read after several stages covers all of them. That direction is safe for a budget: it
    # can raise a false alarm, never hide an overrun.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _rows_for_target(directory: Path, target_bytes: int, columns: int) -> int:
    # Measured from a probe rather than assumed, because the generator owns its cell width and
    # a hardcoded constant silently overshot the target more than threefold. Preflight alone
    # survived that; normalization writes the objects too, so the working set is roughly twice
    # the CSV and an overshoot is the difference between fitting on a runner and filling it.
    probe_rows = 1_000
    probe = generate_csv(
        directory / "width-probe.csv",
        rows=probe_rows,
        columns=columns,
        clusters=4,
        seed=42,
    )
    bytes_per_row = probe.stat().st_size / probe_rows
    probe.unlink()
    # The probe's header inflates bytes_per_row by well under a tenth of a percent, so this
    # lands just below the target rather than above it. The 90% floor asserted later absorbs
    # that, and undershooting is the safe direction for a disk-bound measurement.
    return max(1, math.ceil(target_bytes / bytes_per_row))


def _emit(measurements: dict[str, object], output: Path | None) -> None:
    payload = json.dumps(measurements, indent=2, sort_keys=True) + "\n"
    sys.stdout.write(payload)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--rows", type=int, default=1_000)
    parser.add_argument("--target-bytes", type=int, default=2_147_483_648)
    # The two benchmarks have very different costs: the large
    # normalization measurement needs a multi-gigabyte working set, while the object sweep is
    # minutes of CPU. Exactly one per process, and required, so that neither "neither" nor
    # "both" can be requested: ru_maxrss is a whole-process high-water mark, so a second
    # measurement in the same process would report the first one's peak as its own.
    parser.add_argument(
        "--select",
        choices=("large", "sweep"),
        required=True,
        help="which of the two specified benchmarks to run",
    )
    parser.add_argument(
        "--objects",
        type=int,
        nargs="+",
        default=OBJECT_COUNTS,
        help=(
            "object counts to sweep; defaults to %(default)s. A caller that "
            "narrows this is trading coverage for wall time."
        ),
    )
    # A run is compared against the median of the last three on the
    # same runner, which is impossible while the numbers only reach stdout of a finished job.
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="also write the measurements as JSON to this path, for run-over-run comparison",
    )
    arguments = parser.parse_args()
    run_large: bool = arguments.select == "large"
    run_sweep: bool = arguments.select == "sweep"
    if run_sweep and sorted(arguments.objects) != sorted(OBJECT_COUNTS):
        print(
            f"note: sweeping {sorted(arguments.objects)} instead of the "
            f"specified {list(OBJECT_COUNTS)}",
            file=sys.stderr,
        )
    arguments.directory.mkdir(parents=True, exist_ok=True)
    measurements: dict[str, object] = {}
    # Collected rather than raised, so the measurements are written before the process exits.
    # A run that broke the budget is the one whose numbers are worth keeping.
    budget_failures: list[str] = []
    if run_large:
        large_rows = _rows_for_target(
            arguments.directory, arguments.target_bytes, columns=64
        )
        large_path = generate_csv(
            arguments.directory / "large-64-columns.csv",
            rows=large_rows,
            columns=64,
            clusters=4,
            seed=42,
        )
        large_preview = estimate(large_path, split="columns")
        preflight_peak_rss = _peak_rss_bytes()
        measurements["large_preflight"] = {
            "input_bytes": large_preview.input_size_bytes,
            "peak_rss_bytes": preflight_peak_rss,
        }
        # The budgeted stage. Preflight scans the CSV without writing a single object file, so
        # measuring it alone leaves the budgeted stage unmeasured. The measurement stops
        # here: normalization is the last stage the 1.5 GiB budget covers, and going further
        # would only add the cubic cost this measurement does not need.
        started = time.monotonic()
        normalization = normalize_csv(
            large_path,
            arguments.directory / "large-normalization",
            config=NormalizationConfig(split="columns"),
        )
        normalization_seconds = time.monotonic() - started
        normalization_peak_rss = _peak_rss_bytes()
        measurements["large_normalization"] = {
            "input_bytes": large_preview.input_size_bytes,
            "object_count": normalization.object_count,
            "normalized_bytes": normalization.total_bytes,
            "seconds": normalization_seconds,
            "peak_rss_bytes": normalization_peak_rss,
        }
        if large_preview.input_size_bytes < arguments.target_bytes * 0.9:
            budget_failures.append(
                "large benchmark CSV did not reach 90% of target size"
            )
        if normalization_peak_rss > NORMALIZATION_RSS_BUDGET_BYTES:
            budget_failures.append(
                f"large normalization peaked at {normalization_peak_rss} bytes of RSS, "
                f"above the {NORMALIZATION_RSS_BUDGET_BYTES} byte budget"
            )
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
        measurements[f"algorithm_{objects}"] = {
            "object_count": preview.object_count,
            "pair_count": preview.pair_count,
            "seconds": seconds,
            "pairs_per_second": preview.pair_count / seconds if seconds > 0 else 0.0,
            "input_bytes": preview.input_size_bytes,
            "run_disk_bytes": _directory_bytes(run_dir),
            "peak_rss_bytes": _peak_rss_bytes(),
        }
    _emit(measurements, arguments.output)
    if budget_failures:
        for failure in budget_failures:
            print(f"error: {failure}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
