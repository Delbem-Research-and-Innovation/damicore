# ADR 0010: Spreadsheet cells become text by a rule this project owns

A spreadsheet cell is typed; a DAMICORE object is bytes. The rule that crosses
that gap decides what the data is, so it belongs here and not to whichever
library happens to parse the file. Two engines reading one workbook disagreed on
integers, formulas, blanks, and dates, which means an unstated rule would let a
dependency bump silently change published distances.

The rule is recorded in the manifest as `cell_text_rule: v1`:

- text is unchanged -- no stripping, no Unicode normalization, as for delimited
  input;
- a blank cell, `None`, and an empty string all become `""`, which is what a
  blank delimited field already produces;
- an integer, and a float whose value is integral, become decimal digits with no
  fractional part and no exponent, so the same table read from a spreadsheet and
  from delimited text produces the same object bytes;
- any other float becomes `repr`, the shortest representation that round-trips;
- a boolean becomes `TRUE` or `FALSE`, which is how a spreadsheet export writes
  it;
- a date or datetime becomes `YYYY-MM-DDTHH:MM:SS`, never a serial number;
- an error value becomes its own text, such as `#REF!`;
- a formula becomes the formula text and is never evaluated.

Dates are always rendered with a time component because openpyxl reports a date
cell as a midnight datetime, so the distinction is already gone. Recovering it
from the cell's number format would make object bytes depend on presentation,
and reformatting a cell without touching its value would change run identity.

Formulas are read with `data_only=False`. The cached alternative returns nothing
for a workbook the spreadsheet application never recalculated, which would turn
a formula into a blank without saying so.

Three structural rules complete the contract. The table is the smallest
rectangle containing every non-blank cell, so trailing blank rows and columns are
trimmed and formatting alone cannot invent objects. A workbook with one sheet
uses it; more than one requires an explicit choice, because picking the first
silently decides which data was analyzed. Merged cells are read as presented,
with the value in the leading cell and blanks beside it, since rejecting them is
hostile and filling them invents data.
