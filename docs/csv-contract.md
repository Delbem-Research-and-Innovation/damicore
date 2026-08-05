# CSV contract

DAMICORE accepts an existing regular local file. It parses with pandas in
chunks, strict decoding, string values, blank-line preservation, standard CSV
double-quote rules, and no NA or type inference. The delimiter is one Unicode
character. Header names must be present and unique.

Every record must carry exactly as many fields as the header declares. A record with more or
fewer fields is rejected as a CSV format error, naming the line and the two counts, because
accepting one would drop a cell value or invent one that the file never contained. A blank
line is not a width mismatch: blank lines are preserved as a row of empty cells.

`split="columns"` requires at least two columns and one data row. Each cell is
encoded as one compact UTF-8 JSON string followed by LF. `split="rows"`
requires at least two data rows; each becomes one compact JSON array followed
by LF. Values are not stripped, Unicode-normalized, or otherwise changed.

Object IDs are positional (`column_000001` or `row_000001`) and labels are
presentation only. Different CSV chunk sizes produce identical object bytes.
