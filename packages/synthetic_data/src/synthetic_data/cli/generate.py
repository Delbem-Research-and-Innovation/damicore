import json
from pathlib import Path
from typing import Annotated

import typer

from synthetic_data.engine import write_csv
from synthetic_data.schemas.mixed_16col import build_schema

DEFAULT_OUTPUT = ".temp/synthetic_data/mixed_16col.csv"


def generate(
    rows: Annotated[int, typer.Option("--rows", help="Number of rows to generate.")] = 30_000,
    seed: Annotated[int, typer.Option("--seed", help="Seed for reproducible generation.")] = 0,
    output: Annotated[
        str, typer.Option("--output", help="Path for the output CSV file.")
    ] = DEFAULT_OUTPUT,
) -> None:
    """Generate the mixed_16col synthetic dataset as a CSV file."""
    output_path = Path(output)
    schema = build_schema()
    write_csv(schema, rows, seed, output_path)
    typer.echo(
        json.dumps(
            {
                "status": "success",
                "output": str(output_path),
                "rows": rows,
                "columns": len(schema),
            },
            indent=2,
        )
    )
