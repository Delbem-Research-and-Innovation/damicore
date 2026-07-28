import json
from typing import Annotated

import typer

from damicore_tree_builder.functional import run


def build(
    input_path: Annotated[
        str, typer.Option("--input", help="Path to input distance matrix CSV file.")
    ],
    output_path: Annotated[str, typer.Option("--output", help="Path for output Newick file.")],
) -> None:
    """Build a Neighbor-Joining phylogenetic tree from a distance matrix CSV."""
    try:
        report = run(input_path, output_path)
    except (FileNotFoundError, ValueError) as error:
        typer.echo(json.dumps({"status": "error", "message": str(error)}, indent=2))
        raise typer.Exit(code=1)
    typer.echo(json.dumps(report, indent=2))
