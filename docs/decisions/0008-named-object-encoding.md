# ADR 0008: The object encoding is named and versioned

An NCD value is only meaningful relative to the bytes it measured, so the
encoding that produced those bytes is part of the result. The manifest records
it as `object_encoding`: `json-lines/1` for a split dataset, `raw-bytes/1` for
adopted files, whose objects are the user's bytes unchanged.

The bytes themselves do not change. ADR 0002 stays in force. Switching to an
escaped tab-separated encoding was measured on a 60x20 fixture with four planted
clusters: objects shrank 3.77%, NCD moved by at most 0.040023 and 0.009071 on
average, and the recovered partition was identical. A change that invalidates
every published distance without changing an answer is not worth taking.

Raw tab-separated text is separately excluded because it is not injective.
`['a\tb', 'c']` and `['a', 'b\tc']` serialize to the same bytes, as do one cell
containing a newline and two cells that do not, so two different objects would
measure as distance 0 while every matrix validator still passed.

Naming the encoding is what makes a future one additive rather than a rewrite.
A tab-separated rendering for human inspection belongs under `diagnostics/`,
never as the NCD input.
