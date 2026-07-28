from pathlib import Path

import pytest
from damicore_distance.compressors import Compressor
from damicore_distance.core import AlgorithmType, MetricStrategy

from damicore.pipeline import PipelineInput, run_pipeline


@pytest.mark.unit
def test_run_pipeline_chains_normalizer_distance_and_tree_builder(tmp_path: Path) -> None:
    source_csv = tmp_path / "raw.csv"
    source_csv.write_text(
        "cod_distr;ano;Idade;sexo;populacao;regiao\n"
        "1;2020;0;M;100;norte\n"
        "1;2020;0;F;200;norte\n"
        "1;2020;1;M;150;sul\n"
        "1;2020;1;F;180;sul\n"
        "2;2020;0;M;90;leste\n"
        "2;2020;0;F;95;leste\n",
        encoding="latin-1",
    )

    contract: PipelineInput = {
        "normalizer": {
            "source_file_path": str(source_csv),
            "split_strategy": {
                "type": "composite_keys",
                "key_columns": ["cod_distr", "ano", "Idade"],
                "content_columns": ["sexo", "populacao", "regiao"],
            },
            "output_folder_name": "normalized",
        },
        "distance_metric_strategy": MetricStrategy(
            algorithm=AlgorithmType.NCD,
            compressor=Compressor.GZIP,
            compression_level=9,
        ),
        "distance_output_path": str(tmp_path / "distance_matrix.csv"),
        "tree_output_path": str(tmp_path / "tree.nwk"),
    }

    result = run_pipeline(contract)

    assert result["normalizer"]["status"] == "success"
    assert result["distance"].status == "success"
    assert result["tree_builder"]["status"] == "success"
    assert Path(contract["distance_output_path"]).exists()
    assert Path(contract["tree_output_path"]).exists()
