from __future__ import annotations

import csv
import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from damicore_normalizer.config import NormalizationConfig
from damicore_normalizer.errors import NormalizerError
from damicore_normalizer.manifest import ObjectDescriptor
from damicore_normalizer.serializer import serialize_cell, serialize_row


@dataclass(frozen=True)
class ScanResult:
    objects: tuple[ObjectDescriptor, ...]
    total_bytes: int
    max_serialized_chunk_bytes: int
    row_count: int


class _FilePool:
    def __init__(self, root: Path, limit: int) -> None:
        self._root = root
        self._limit = limit
        self._streams: OrderedDict[str, BinaryIO] = OrderedDict()

    def write(self, name: str, payload: bytes) -> None:
        stream = self._streams.pop(name, None)
        if stream is None:
            if len(self._streams) >= self._limit:
                _, oldest = self._streams.popitem(last=False)
                oldest.close()
            stream = (self._root / name).open("ab")
        self._streams[name] = stream
        stream.write(payload)

    def close(self) -> None:
        for stream in self._streams.values():
            stream.close()
        self._streams.clear()


def _read_header(path: Path, config: NormalizationConfig) -> list[str]:
    try:
        with path.open("r", encoding=config.encoding, errors="strict", newline="") as stream:
            header = next(csv.reader(stream, delimiter=config.delimiter))
    except (OSError, UnicodeError, csv.Error, StopIteration) as exc:
        raise NormalizerError("Could not read a valid CSV header", code="csv_format_error") from exc
    if not header or any(name == "" for name in header):
        raise NormalizerError("CSV header names must be non-empty", code="csv_format_error")
    if len(set(header)) != len(header):
        raise NormalizerError("CSV header names must be unique", code="csv_format_error")
    return header


def scan_csv(
    csv_path: str | Path,
    config: NormalizationConfig,
    *,
    objects_dir: Path | None = None,
) -> ScanResult:
    """Scan canonical object bytes; optionally persist them through the same path."""
    path = Path(csv_path).resolve()
    if not path.is_file():
        raise NormalizerError(
            f"CSV path is not a regular file: {path}",
            code="input_validation_error",
        )
    header = _read_header(path, config)
    if config.split == "columns" and len(header) < 2:
        raise NormalizerError(
            "columns split requires at least two columns",
            code="csv_format_error",
        )

    if objects_dir is not None:
        objects_dir.mkdir(parents=True, exist_ok=False)

    column_hashes = [hashlib.sha256() for _ in header]
    column_sizes = [0 for _ in header]
    row_objects: list[ObjectDescriptor] = []
    max_chunk_bytes = 0
    row_count = 0
    pool = _FilePool(objects_dir, config.max_open_files) if objects_dir is not None else None

    try:
        chunks = pd.read_csv(
            path,
            sep=config.delimiter,
            encoding=config.encoding,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            skip_blank_lines=False,
            chunksize=config.chunk_rows,
            on_bad_lines="error",
            quotechar='"',
            doublequote=True,
            comment=None,
        )
        for chunk in chunks:
            if list(chunk.columns) != header:
                raise NormalizerError("CSV header changed while parsing", code="csv_format_error")
            chunk_bytes = 0
            for values in chunk.itertuples(index=False, name=None):
                text_values = tuple(str(value) for value in values)
                row_count += 1
                if config.split == "rows":
                    payload = serialize_row(text_values)
                    object_id = f"row_{row_count:06d}"
                    relative_path = f"objects/{object_id}.jsonl"
                    digest = hashlib.sha256(payload).hexdigest()
                    row_objects.append(
                        ObjectDescriptor(
                            object_id=object_id,
                            label=object_id,
                            relative_path=relative_path,
                            size_bytes=len(payload),
                            sha256=digest,
                        )
                    )
                    if objects_dir is not None:
                        (objects_dir / f"{object_id}.jsonl").write_bytes(payload)
                    chunk_bytes += len(payload)
                else:
                    for index, value in enumerate(text_values):
                        payload = serialize_cell(value)
                        column_hashes[index].update(payload)
                        column_sizes[index] += len(payload)
                        chunk_bytes += len(payload)
                        if pool is not None:
                            pool.write(f"column_{index + 1:06d}.jsonl", payload)
            max_chunk_bytes = max(max_chunk_bytes, chunk_bytes)
    except NormalizerError:
        raise
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as exc:
        raise NormalizerError("CSV parsing failed", code="csv_format_error") from exc
    finally:
        if pool is not None:
            pool.close()

    if row_count == 0 or (config.split == "rows" and row_count < 2):
        raise NormalizerError("CSV does not contain enough data rows", code="csv_format_error")

    if config.split == "columns":
        objects = tuple(
            ObjectDescriptor(
                object_id=f"column_{index + 1:06d}",
                label=label,
                relative_path=f"objects/column_{index + 1:06d}.jsonl",
                size_bytes=column_sizes[index],
                sha256=column_hashes[index].hexdigest(),
            )
            for index, label in enumerate(header)
        )
    else:
        objects = tuple(row_objects)
    return ScanResult(
        objects=objects,
        total_bytes=sum(item.size_bytes for item in objects),
        max_serialized_chunk_bytes=max_chunk_bytes,
        row_count=row_count,
    )
