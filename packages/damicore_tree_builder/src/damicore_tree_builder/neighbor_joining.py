from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

from damicore_tree_builder.errors import TreeBuilderError
from damicore_tree_builder.models import Tree, TreeEdge, TreeNode


def validate_matrix(
    matrix: np.ndarray[Any, Any],
    labels: Sequence[str],
    block_size: int = 512,
) -> None:
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or matrix.shape[0] != len(labels):
        raise TreeBuilderError(
            "Distance matrix shape does not match labels", code="distance_matrix_validation_error"
        )
    if len(labels) < 2 or len(set(labels)) != len(labels):
        raise TreeBuilderError(
            "At least two unique labels are required", code="distance_matrix_validation_error"
        )
    if matrix.dtype != np.float64:
        raise TreeBuilderError(
            "Distance matrix must be float64",
            code="distance_matrix_validation_error",
        )
    size = len(labels)
    for row_start in range(0, size, block_size):
        row_stop = min(row_start + block_size, size)
        if not np.isfinite(matrix[row_start:row_stop]).all():
            raise TreeBuilderError(
                "Distance matrix must be finite",
                code="distance_matrix_validation_error",
            )
        for row in range(row_start, row_stop):
            if float(matrix[row, row]) != 0.0:
                raise TreeBuilderError(
                    "Distance matrix diagonal must be exactly zero",
                    code="distance_matrix_validation_error",
                )
            # pyright: ignore is on np.array_equal, whose numpy stub is partially
            # unknown under strict mode; the arrays themselves are fully typed.
            symmetric = np.array_equal(  # pyright: ignore[reportUnknownMemberType]
                matrix[row, :], matrix[:, row]
            )
            if not bool(symmetric):
                raise TreeBuilderError(
                    "Distance matrix must be bitwise symmetric",
                    code="distance_matrix_validation_error",
                )


def neighbor_joining(matrix: npt.NDArray[np.floating[Any]], labels: Sequence[str]) -> Tree:
    """Build a deterministic Neighbor Joining tree, copying the input matrix."""
    copied = np.array(matrix, dtype=np.float64, copy=True, order="C")
    validate_matrix(copied, labels)
    return build_neighbor_joining(copied, list(labels), q_block_size=512)


def build_neighbor_joining(
    work: np.ndarray[Any, Any],
    labels: list[str],
    display_labels: list[str] | None = None,
    *,
    q_block_size: int,
) -> Tree:
    active = list(labels)
    slots = {label: index for index, label in enumerate(labels)}
    rendered_labels = display_labels or labels
    nodes = [
        TreeNode(id=identifier, kind="leaf", label=rendered_labels[index])
        for index, identifier in enumerate(labels)
    ]
    edges: list[TreeEdge] = []
    internal_index = 1
    row_sums = {
        node: float(sum(work[slots[node], slots[other]] for other in active if other != node))
        for node in active
    }

    while len(active) > 2:
        active.sort()
        count = len(active)
        best: tuple[float, str, str] | None = None
        for block_start in range(0, count, q_block_size):
            block_stop = min(block_start + q_block_size, count)
            for left_index in range(block_start, block_stop):
                left = active[left_index]
                for right in active[left_index + 1 :]:
                    score = (
                        (count - 2) * float(work[slots[left], slots[right]])
                        - row_sums[left]
                        - row_sums[right]
                    )
                    candidate = (score, left, right)
                    if best is None or candidate < best:
                        best = candidate
        # `active` holds at least three labels here, so the pair loop above always ran and
        # `best` is always set; asserting it is how the type narrows without a dead branch.
        assert best is not None
        _, left, right = best
        left_slot, right_slot = slots[left], slots[right]
        distance = float(work[left_slot, right_slot])
        delta = (row_sums[left] - row_sums[right]) / (count - 2)
        left_length = 0.5 * (distance + delta)
        right_length = distance - left_length
        internal = f"nj_{internal_index:06d}"
        internal_index += 1
        nodes.append(TreeNode(id=internal, kind="internal"))
        edges.extend(
            [
                TreeEdge(source=internal, target=left, length=left_length),
                TreeEdge(source=internal, target=right, length=right_length),
            ]
        )
        remaining = [node for node in active if node not in (left, right)]
        internal_sum = 0.0
        for other in remaining:
            other_slot = slots[other]
            left_distance = float(work[left_slot, other_slot])
            right_distance = float(work[right_slot, other_slot])
            updated = 0.5 * (left_distance + right_distance - distance)
            work[left_slot, other_slot] = updated
            work[other_slot, left_slot] = updated
            row_sums[other] = row_sums[other] - left_distance - right_distance + updated
            internal_sum += updated
        work[left_slot, left_slot] = 0.0
        slots.pop(left)
        slots.pop(right)
        row_sums.pop(left)
        row_sums.pop(right)
        slots[internal] = left_slot
        row_sums[internal] = internal_sum
        active = [*remaining, internal]

    active.sort()
    left, right = active
    final_length = float(work[slots[left], slots[right]]) / 2.0
    root = "nj_root"
    nodes.append(TreeNode(id=root, kind="internal"))
    edges.extend(
        [
            TreeEdge(source=root, target=left, length=final_length),
            TreeEdge(source=root, target=right, length=final_length),
        ]
    )
    ordered_edges = tuple(sorted(edges, key=lambda edge: (edge.source, edge.target)))
    return Tree(root_id=root, nodes=tuple(nodes), edges=ordered_edges)
