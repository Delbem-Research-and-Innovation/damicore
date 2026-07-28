from pathlib import Path

import pytest

from damicore_normalizer import NormalizerInput, NormalizerOutput, normalize_dataset

SOURCE_CSV_NAME = "raw-dataset-seade-pop-age.csv"

_RAW_CSV_CONTENT = (
    "cod_distr;ano;Idade;sexo;populacao\n"
    "1;2020;0;M;100\n"
    "1;2020;0;F;200\n"
    "1;2020;1;M;150\n"
    "1;2020;1;F;180\n"
)


def _build_contract(csv_path: Path) -> NormalizerInput:
    return {
        "source_file_path": str(csv_path),
        "split_strategy": {
            "type": "composite_keys",
            "key_columns": ["cod_distr", "ano", "Idade"],
            "content_columns": ["sexo", "populacao"],
        },
        "output_folder_name": "output-normalizer-cod_distr-ano-idade",
    }


@pytest.fixture(scope="module")
def isolated_csv_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    csv_dir = tmp_path_factory.mktemp("normalizer_fixture")
    (csv_dir / SOURCE_CSV_NAME).write_text(_RAW_CSV_CONTENT, encoding="latin-1")
    return csv_dir


@pytest.fixture
def contract(isolated_csv_dir: Path) -> NormalizerInput:
    return _build_contract(isolated_csv_dir / SOURCE_CSV_NAME)


@pytest.fixture(scope="module")
def normalize_result(isolated_csv_dir: Path) -> NormalizerOutput:
    return normalize_dataset(_build_contract(isolated_csv_dir / SOURCE_CSV_NAME))
