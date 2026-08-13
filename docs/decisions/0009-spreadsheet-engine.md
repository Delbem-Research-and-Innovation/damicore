# ADR 0009: openpyxl reads spreadsheets, through its own API

`.xlsx` and `.xlsm` are read with `openpyxl` in `read_only` mode, iterating rows
directly. `pandas.read_excel` is not used: it has no `chunksize`, so the whole
sheet materializes and the bounded-memory invariant is lost.

`python-calamine` was measured and rejected. It collapses formula, blank, and
empty-string cells to `''`, and types the same integer as `int` from a `.xls`
and as `float` from an `.xlsx`; that information is gone before this package
sees it, so no rule here can recover it. It is also a compiled extension, which
ties availability to wheels published for each interpreter in the supported
range.

openpyxl is pure Python, streams rows, and keeps the distinctions that matter:
an integer stays an integer, formula text survives, and a blank cell is
distinguishable from an empty string. Its one measured defect is dimension
inflation -- a single formatting-only cell at H40 reported a 2x3 sheet as 40x8 --
which ADR 0010 repairs by trimming to the used range.

Legacy `.xls` is out of scope and raises a typed error naming the conversion.
Supporting it would add a second engine, a second coercion rule, and a second
fixture generator for a format last current in 2003. If it returns, `xlrd`
is the engine to use: it keeps the pure-Python property and leaves this path
untouched, and it needs its own boolean rule because it reports `True` as `1`.
