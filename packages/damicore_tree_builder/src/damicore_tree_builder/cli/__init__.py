import typer

from damicore_tree_builder.cli import build

app = typer.Typer()
app.add_typer(build.app, name="build")

__all__ = ["app"]
