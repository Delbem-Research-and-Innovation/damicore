import json

from damicore.cli import main


def _csv(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("a,b\naa,ab\naa,ac\n", encoding="utf-8")
    return path


def test_cli_estimate_json_has_clean_stdout(tmp_path, capsys):
    code = main(["estimate", str(_csv(tmp_path)), "--workers", "1", "--json"])
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["object_count"] == 2


def test_cli_run_and_typed_error_codes(tmp_path, capsys):
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


def test_cli_interrupt_exit_code(monkeypatch, tmp_path):
    def interrupted(**_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("damicore.cli.run", interrupted)
    assert main(["run", str(_csv(tmp_path)), "--no-progress"]) == 130
