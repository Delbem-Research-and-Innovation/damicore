import typer

from damicore_tree_builder.cli.build import build

app = typer.Typer()
# typer collapses a Typer() with exactly one command onto the app itself, so
# this is invoked as `damicore-tree-builder --input ... --output ...` (no
# subcommand name) regardless of the name given here.
app.command()(build)

__all__ = ["app"]
