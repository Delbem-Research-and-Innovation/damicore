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

# Specification section 20 exposes four of the five resource limits as flags. Their values are
# read from the model rather than restated here: ResourceLimits owns them, so raising a limit
# there cannot leave the CLI clamped at the old one while `damicore.run()` honours the new one.
# The model is frozen, so one shared instance is safe to read from.
_DEFAULT_LIMITS = ResourceLimits()


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
        command.add_argument("--max-objects", type=int, default=_DEFAULT_LIMITS.max_objects)
        command.add_argument("--max-pairs", type=int, default=_DEFAULT_LIMITS.max_pairs)
        command.add_argument(
            "--max-matrix-bytes", type=int, default=_DEFAULT_LIMITS.max_matrix_bytes
        )
        command.add_argument(
            "--max-working-memory-bytes",
            type=int,
            default=_DEFAULT_LIMITS.max_working_memory_bytes,
        )
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


def _execution_from_arguments(arguments: argparse.Namespace) -> ExecutionConfig:
    requested: int | None = arguments.workers
    limits = ResourceLimits(
        max_objects=arguments.max_objects,
        max_pairs=arguments.max_pairs,
        max_matrix_bytes=arguments.max_matrix_bytes,
        max_working_memory_bytes=arguments.max_working_memory_bytes,
    )
    # "auto" is a literal in the config contract, so branch rather than widen to int | str.
    if requested is None:
        return ExecutionConfig(workers="auto", limits=limits)
    return ExecutionConfig(workers=requested, limits=limits)


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
    # argparse yields Any, and a dict of options splatted with ** erases every signature
    # check at the call. Bind the parsed values to typed locals once, so each argument below
    # is verified against the public API it is passed to.
    csv_path: str = arguments.csv
    split: str = arguments.split
    delimiter: str = arguments.delimiter
    encoding: str = arguments.encoding
    keep_normalized: bool = arguments.keep_normalized
    save_diagnostics: bool = arguments.save_diagnostics
    execution = _execution_from_arguments(arguments)
    try:
        if arguments.command == "estimate":
            preview = estimate(
                csv_path,
                split=split,
                delimiter=delimiter,
                encoding=encoding,
                keep_normalized=keep_normalized,
                save_diagnostics=save_diagnostics,
                execution=execution,
            )
            payload = preview.model_dump(mode="json")
            if arguments.json:
                print(json.dumps(payload, sort_keys=True))
            else:
                print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        else:
            compressor: str = arguments.compressor
            compression_level: int = arguments.compression_level
            num_clusters: int | None = arguments.clusters
            output_dir: str | None = arguments.output_dir
            result = run(
                csv_path,
                split=split,
                delimiter=delimiter,
                encoding=encoding,
                keep_normalized=keep_normalized,
                save_diagnostics=save_diagnostics,
                execution=execution,
                compressor=compressor,
                compression_level=compression_level,
                num_clusters=num_clusters,
                output_dir=output_dir,
                progress=not arguments.no_progress,
            )
            # Iterating the model rather than a hand-written list means an artifact added to
            # ArtifactPaths is printed without editing the CLI, and one that is absent for
            # this configuration stays absent instead of being printed as None.
            for name, path in result.artifacts:
                if path is not None:
                    print(f"{name}: {path}", file=sys.stderr)
            result.close()
        return 0
    except KeyboardInterrupt:
        return 130
    except DamicoreError as error:
        print(json.dumps({"code": error.code, "message": str(error)}), file=sys.stderr)
        return _exit_code(error)


if __name__ == "__main__":
    raise SystemExit(main())
