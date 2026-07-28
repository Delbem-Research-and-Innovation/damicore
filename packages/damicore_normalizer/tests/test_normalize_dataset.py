from pathlib import Path

import pytest

from damicore_normalizer import NormalizerInput, NormalizerOutput, normalize_dataset


@pytest.mark.unit
def test_filename_format(normalize_result: NormalizerOutput) -> None:
    output_dir = Path(normalize_result["output_directory_path"])
    assert (output_dir / "sexo.txt").exists()
    assert (output_dir / "populacao.txt").exists()


@pytest.mark.unit
def test_total_files_generated(normalize_result: NormalizerOutput) -> None:
    assert normalize_result["total_files_generated"] == 2


@pytest.mark.unit
def test_file_has_one_column_per_line(normalize_result: NormalizerOutput) -> None:
    output_dir = Path(normalize_result["output_directory_path"])
    sample_file = output_dir / "populacao.txt"
    lines = sample_file.read_text(encoding="latin-1").strip().split("\n")
    for line in lines:
        parts = line.split(";")
        assert len(parts) == 1


@pytest.mark.unit
def test_output_file_has_no_header(normalize_result: NormalizerOutput) -> None:
    output_dir = Path(normalize_result["output_directory_path"])
    sexo_file = output_dir / "sexo.txt"
    populacao_file = output_dir / "populacao.txt"

    assert "sexo" not in sexo_file.read_text(encoding="latin-1")
    assert "populacao" not in populacao_file.read_text(encoding="latin-1")


@pytest.mark.unit
def test_invalid_split_strategy_type_raises(contract: NormalizerInput) -> None:
    contract["split_strategy"]["type"] = "sliding_window"
    with pytest.raises(ValueError, match="composite_keys"):
        normalize_dataset(contract)
