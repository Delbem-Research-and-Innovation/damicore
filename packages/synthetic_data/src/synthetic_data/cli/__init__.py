import typer

from synthetic_data.cli.generate import generate

app = typer.Typer()
# typer collapses a Typer() with exactly one command onto the app itself, so
# this is invoked as `synthetic-data --rows ... --seed ...` (no subcommand
# name) regardless of the name given here — matches damicore_tree_builder.
app.command()(generate)

__all__ = ["app"]
