"""Pipeline orchestrator that sequences the damicore_* packages.

Each stage is called through the public, versioned data contract of its
package (the ``__all__`` surface of ``damicore_normalizer``,
``damicore_distance`` and ``damicore_tree_builder``). This module owns no
domain logic of its own — it only wires the output of one stage into the
input of the next.

The clusterizer stage is intentionally not wired in yet: ``damicore_clusterizer``
does not have a public API to call.
"""

from __future__ import annotations

from typing import Any, TypedDict

from damicore_distance import DistanceMatrixInput, DistanceMatrixOutput, compute_distance_matrix
from damicore_distance.core import MetricStrategy
from damicore_normalizer import NormalizerInput, NormalizerOutput, normalize_dataset
from damicore_tree_builder import run as build_tree


class PipelineInput(TypedDict):
    """End-to-end contract for running normalizer -> distance -> tree_builder."""

    normalizer: NormalizerInput
    distance_metric_strategy: MetricStrategy
    distance_output_path: str
    tree_output_path: str


class PipelineOutput(TypedDict):
    """Aggregated report from every stage of the pipeline."""

    normalizer: NormalizerOutput
    distance: DistanceMatrixOutput
    tree_builder: dict[str, Any]


def run_pipeline(contract: PipelineInput) -> PipelineOutput:
    """Run the normalizer, distance and tree_builder stages in sequence.

    Parameters
    ----------
    contract : PipelineInput
        Input for the normalizer stage plus the parameters required by the
        distance and tree_builder stages. The ``input_directory`` for the
        distance stage and the ``input_path`` for the tree_builder stage are
        derived automatically from the previous stage's output.

    Returns
    -------
    PipelineOutput
        The output of each stage, keyed by stage name.
    """
    normalizer_output = normalize_dataset(contract["normalizer"])

    distance_output = compute_distance_matrix(
        DistanceMatrixInput(
            input_directory=normalizer_output["output_directory_path"],
            metric_strategy=contract["distance_metric_strategy"],
            output_destination=contract["distance_output_path"],
        )
    )

    tree_builder_output = build_tree(
        input_path=distance_output.output_file_path,
        output_path=contract["tree_output_path"],
    )

    return {
        "normalizer": normalizer_output,
        "distance": distance_output,
        "tree_builder": tree_builder_output,
    }
