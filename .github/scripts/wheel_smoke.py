"""Smoke an environment built only from wheels.

Runs under the target interpreter of a clean virtual environment, so it may import nothing
beyond the standard library and the installed ``damicore`` distributions. It never imports
from the checkout: the only thing this file contributes is the check itself.

``--package`` asserts a distribution installs alone, that its declared public surface
resolves, and that any behaviour a name lookup cannot see still holds under the dependencies
that distribution actually declares. The exact symbol list is not asserted here; that
contract belongs to ``tests/architecture``, and duplicating it would mean two owners for one
rule.

``--pipeline`` asserts the aggregate distribution runs the required pipeline end to end
from a CSV path and reloads the persisted run.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import pathlib
import sysconfig
import tempfile
from typing import cast

CSV = "a,b,c,d\n1,4,7,9\n2,5,8,1\n3,6,2,4\n1,4,7,8\n"

# Where an installed distribution must live. Resolving anywhere else means the smoke is
# reading the checkout, which would let it pass while the wheel is broken.
INSTALL_ROOTS = tuple(
    pathlib.Path(path).resolve()
    for path in (sysconfig.get_paths()["purelib"], sysconfig.get_paths()["platlib"])
)


def check_public_surface(name: str) -> None:
    """Import a package and assert it came from the installation and fully resolves."""
    module = importlib.import_module(name)
    origin = pathlib.Path(getattr(module, "__file__", "") or "").resolve()
    if not any(origin.is_relative_to(root) for root in INSTALL_ROOTS):
        raise AssertionError(
            f"{name} resolved to {origin}, outside the installation roots "
            f"{[str(root) for root in INSTALL_ROOTS]}"
        )

    # A module attribute carries no static type, so validate the shape rather than trust it:
    # __all__ must be a non-empty list of names, which is also what the contract claims.
    declared: object = getattr(module, "__all__", None)
    if not isinstance(declared, list):
        raise TypeError(f"{name}.__all__ must be a list, got {declared!r}")
    # isinstance narrows only to list[Unknown]; this cast carries no unchecked premise, because
    # the list check above established it and every entry is validated individually below.
    exported: list[str] = []
    for entry in cast(list[object], declared):
        if not isinstance(entry, str):
            raise TypeError(f"{name}.__all__ must hold only names, got {entry!r}")
        exported.append(entry)
    if not exported:
        raise AssertionError(f"{name}.__all__ must not be empty")
    missing = [symbol for symbol in exported if not hasattr(module, symbol)]
    if missing:
        raise AssertionError(f"{name}.__all__ exports unresolvable names: {missing}")
    print(f"wheel-smoke: {name} exports {len(exported)} resolvable names")
    check = _BEHAVIOUR_CHECKS.get(name)
    if check is not None:
        check()
        print(f"wheel-smoke: {name} public behaviour holds under its declared dependencies")


def _distance_view_without_the_pandas_extra() -> None:
    """A name resolving proves only that an attribute exists, never that calling it works.

    `head` and `to_pandas` are the whole reason damicore-distance declares a pandas extra.
    Installed without it, they must fail with the package's own error naming the extra, and
    the NumPy surface beside them must keep working. Resolving `__all__` sees none of this: a
    method whose first line raises ModuleNotFoundError passes that check untouched.
    """
    import numpy as np
    from damicore_distance import DistanceError, DistanceMatrixView

    directory = pathlib.Path(tempfile.mkdtemp())
    path = directory / "distance.npy"
    np.save(  # pyright: ignore[reportUnknownMemberType] - numpy ships save() untyped
        path, np.zeros((3, 3), dtype=np.float64), allow_pickle=False
    )
    view = DistanceMatrixView(path, ["a", "b", "c"])
    try:
        assert view.shape == (3, 3), view.shape
        assert view.dtype == np.float64, view.dtype
        has_pandas = importlib.util.find_spec("pandas") is not None
        for method in (view.head, view.to_pandas):
            try:
                method()
            except DistanceError as error:
                if has_pandas:
                    raise AssertionError(
                        f"{method.__name__} refused pandas work although pandas is installed"
                    ) from error
                if "damicore-distance[pandas]" not in str(error):
                    raise AssertionError(
                        f"{method.__name__} must name the extra to install, said: {error}"
                    ) from error
            else:
                if not has_pandas:
                    raise AssertionError(
                        f"{method.__name__} materialised a frame without pandas installed"
                    )
    finally:
        view.close()


# Keyed by import name: a distribution appears here when its public surface has behaviour a
# name lookup cannot see, which so far means an optional dependency.
_BEHAVIOUR_CHECKS = {"damicore_distance": _distance_view_without_the_pandas_extra}


def check_pipeline() -> None:
    """Run the required pipeline from a CSV path and reload the persisted run."""
    from damicore import ExecutionConfig, load_result, run

    directory = pathlib.Path(tempfile.mkdtemp())
    source = directory / "dataset.csv"
    source.write_text(CSV, encoding="utf-8")
    output = directory / "run"

    result = run(
        str(source),
        output_dir=str(output),
        progress=False,
        execution=ExecutionConfig(workers=1),
    )
    try:
        assert result.report.status == "completed", result.report.status
        assert list(result.membership.columns) == ["object_id", "label", "cluster"]
    finally:
        result.close()

    reloaded = load_result(str(output))
    try:
        assert reloaded.report.status == "completed", reloaded.report.status
        assert reloaded.membership.equals(result.membership)
    finally:
        reloaded.close()
    print("wheel-smoke: pipeline completed and reloaded")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        metavar="IMPORT_NAME",
        help="package whose import and public surface must resolve; repeatable",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="run the aggregate pipeline end to end and reload its output",
    )
    arguments = parser.parse_args()
    if not arguments.package and not arguments.pipeline:
        parser.error("pass at least one --package or --pipeline")

    for name in arguments.package:
        check_public_surface(name)
    if arguments.pipeline:
        check_pipeline()


if __name__ == "__main__":
    main()
