from __future__ import annotations

import argparse
import json
import sys

from damicore import ExecutionConfig, ResourceLimits, estimate, run
from damicore.errors import (
    ArtifactValidationError,
    CheckpointMismatchError,
    ConfigurationError,
    DamicoreError,
    InputValidationError,
    OutputDirectoryConflictError,
    ResourceLimitError,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="damicore")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("estimate", "run"):
        command = commands.add_parser(name)
        command.add_argument("csv")
        command.add_argument("--split", choices=("columns", "rows"), default="columns")
        command.add_argument("--delimiter", default=",")
        command.add_argument("--encoding", default="utf-8")
        command.add_argument("--workers", type=int)
        command.add_argument("--max-objects", type=int, default=1_000)
        command.add_argument("--max-pairs", type=int, default=500_000)
        command.add_argument("--max-matrix-bytes", type=int, default=536_870_912)
        command.add_argument("--max-working-memory-bytes", type=int, default=536_870_912)
        command.add_argument("--keep-normalized", action="store_true")
        command.add_argument("--save-diagnostics", action="store_true")
    estimate_parser = commands.choices["estimate"]
    estimate_parser.add_argument("--json", action="store_true")
    run_parser = commands.choices["run"]
    run_parser.add_argument("--compressor", choices=("zlib", "gzip"), default="zlib")
    run_parser.add_argument("--compression-level", type=int, default=6)
    run_parser.add_argument("--clusters", type=int)
    run_parser.add_argument("--output-dir")
    run_parser.add_argument("--no-progress", action="store_true")
    return parser


def _execution(arguments: argparse.Namespace) -> ExecutionConfig:
    workers: int | str = arguments.workers if arguments.workers is not None else "auto"
    return ExecutionConfig(
        workers=workers,
        limits=ResourceLimits(
            max_objects=arguments.max_objects,
            max_pairs=arguments.max_pairs,
            max_matrix_bytes=arguments.max_matrix_bytes,
            max_working_memory_bytes=arguments.max_working_memory_bytes,
        ),
    )


def _exit_code(error: DamicoreError) -> int:
    if isinstance(error, (ConfigurationError, InputValidationError)):
        return 2
    if isinstance(error, ResourceLimitError):
        return 3
    if isinstance(error, ArtifactValidationError):
        return 4
    if isinstance(error, (OutputDirectoryConflictError, CheckpointMismatchError)):
        return 5
    return 4


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    common = {
        "csv_path": arguments.csv,
        "split": arguments.split,
        "delimiter": arguments.delimiter,
        "encoding": arguments.encoding,
        "keep_normalized": arguments.keep_normalized,
        "save_diagnostics": arguments.save_diagnostics,
        "execution": _execution(arguments),
    }
    try:
        if arguments.command == "estimate":
            preview = estimate(**common)
            payload = preview.model_dump(mode="json")
            if arguments.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        else:
            result = run(
                **common,
                compressor=arguments.compressor,
                compression_level=arguments.compression_level,
                num_clusters=arguments.clusters,
                output_dir=arguments.output_dir,
                progress=not arguments.no_progress,
            )
            print(str(result.artifacts.run_dir), file=sys.stderr)
            result.close()
        return 0
    except KeyboardInterrupt:
        return 130
    except DamicoreError as error:
        print(json.dumps({"code": error.code, "message": str(error)}), file=sys.stderr)
        return _exit_code(error)


if __name__ == "__main__":
    raise SystemExit(main())
