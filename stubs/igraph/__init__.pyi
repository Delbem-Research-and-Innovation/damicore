"""Minimal type surface for the igraph API this repository actually uses.

igraph ships no `py.typed`, so without this every call through it is `Unknown` and the
untypedness spreads into `damicore_clusterizer` and anything that reads its results. This
declares only the members `tree_graph` and `fastgreedy` call, which keeps the boundary
explicit and reviewable; a member used but not declared here is a type error rather than a
silent `Any`. Behaviour is still verified by the package's own tests against real igraph.
"""

from collections.abc import Sequence

class _AttributeSequence:
    def __getitem__(self, name: str) -> list[object]: ...
    def __setitem__(self, name: str, values: Sequence[object]) -> None: ...

class VertexClustering:
    @property
    def membership(self) -> list[int]: ...
    @property
    def modularity(self) -> float: ...
    def __len__(self) -> int: ...

class VertexDendrogram:
    def as_clustering(self, n: int | None = ...) -> VertexClustering: ...

class Graph:
    def __init__(
        self,
        n: int = ...,
        edges: Sequence[tuple[int, int]] | None = ...,
        directed: bool = ...,
    ) -> None: ...
    @property
    def vs(self) -> _AttributeSequence: ...
    @property
    def es(self) -> _AttributeSequence: ...
    def is_connected(self) -> bool: ...
    def community_fastgreedy(self, weights: str | None = ...) -> VertexDendrogram: ...
