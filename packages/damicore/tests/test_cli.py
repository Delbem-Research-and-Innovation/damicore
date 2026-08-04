import json
from pathlib import Path

import pytest

from damicore import DamicoreResult
from damicore.cli import main

pytestmark = pytest.mark.unit


def _csv(tmp_path: Path) -> Path:
    path = tmp_path / "input.csv"
    path.write_text("a,b\naa,ab\naa,ac\n", encoding="utf-8")
    return path


def test_cli_estimate_json_has_clean_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["estimate", str(_csv(tmp_path)), "--workers", "1", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["object_count"] == 2


def test_cli_run_and_typed_error_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = _csv(tmp_path)
    output = tmp_path / "run"
    assert (
        main(
            [
                "run",
                str(source),
                "--workers",
                "1",
                "--output-dir",
                str(output),
                "--no-progress",
            ]
        )
        == 0
    )
    assert str(output) in capsys.readouterr().err
    assert main(["estimate", str(source), "--max-objects", "1", "--json"]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "run",
                str(source),
                "--max-objects",
                "1",
                "--output-dir",
                str(tmp_path / "limited"),
                "--no-progress",
            ]
        )
        == 3
    )
    assert json.loads(capsys.readouterr().err)["code"] == "resource_limit_error"


def test_cli_envelope_reports_the_public_code_of_a_translated_stage_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Specification sections 19 and 20: the envelope carries the public code, not the
    stage's internal one, and the exit status follows the translated class."""
    source = tmp_path / "duplicate.csv"
    source.write_text("a,a\n1,2\n", encoding="utf-8")
    assert main(["run", str(source), "--no-progress", "--output-dir", str(tmp_path / "out")]) == 2
    assert json.loads(capsys.readouterr().err)["code"] == "csv_format_error"


def test_cli_interrupt_exit_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Accepts any call shape: whether the CLI passes the CSV positionally or by keyword is
    # not part of what this test asserts.
    def interrupted(*_args: object, **_kwargs: object) -> DamicoreResult:
        raise KeyboardInterrupt

    monkeypatch.setattr("damicore.cli.run", interrupted)
    assert main(["run", str(_csv(tmp_path)), "--no-progress"]) == 130
