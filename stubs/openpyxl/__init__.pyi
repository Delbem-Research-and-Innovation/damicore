"""Minimal type surface for the openpyxl API this repository actually uses.

openpyxl ships no `py.typed`, so without this every workbook read is `Unknown` and the
untypedness spreads through `damicore_normalizer.spreadsheet_reader` into the object bytes
themselves. This declares only the members the reader and its fixtures call, which keeps the
boundary explicit and reviewable; a member used but not declared here is a type error rather
than a silent `Any`. Behaviour is still verified by the package's own tests against real
openpyxl.

`CellValue` is the closed set of Python types openpyxl yields from `values_only=True`. It is
the reason `cell_text_rule` can be total: the coercion has a finite domain to span, and a
type outside it is a type error here before it can become an unhandled value at runtime.
"""

import datetime as _datetime
from os import PathLike

from openpyxl.worksheet.worksheet import Worksheet

CellValue = (
    str
    | int
    | float
    | bool
    | _datetime.datetime
    | _datetime.date
    | _datetime.time
    | _datetime.timedelta
    | None
)

class Workbook:
    def __init__(self) -> None: ...
    @property
    def sheetnames(self) -> list[str]: ...
    @property
    def active(self) -> Worksheet | None: ...
    def __getitem__(self, key: str) -> Worksheet: ...
    def create_sheet(self, title: str | None = ...) -> Worksheet: ...
    def save(self, filename: str | PathLike[str]) -> None: ...
    def close(self) -> None: ...

def load_workbook(
    filename: str | PathLike[str],
    read_only: bool = ...,
    keep_vba: bool = ...,
    data_only: bool = ...,
    keep_links: bool = ...,
    rich_text: bool = ...,
) -> Workbook: ...
