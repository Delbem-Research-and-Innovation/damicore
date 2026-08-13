from collections.abc import Iterator, Sequence

from openpyxl import CellValue
from openpyxl.cell.cell import Cell

class Worksheet:
    title: str
    def iter_rows(
        self,
        min_row: int | None = ...,
        max_row: int | None = ...,
        min_col: int | None = ...,
        max_col: int | None = ...,
        values_only: bool = ...,
    ) -> Iterator[tuple[CellValue, ...]]: ...
    def append(self, iterable: Sequence[CellValue]) -> None: ...
    def merge_cells(self, range_string: str) -> None: ...
    def __getitem__(self, key: str) -> Cell: ...
