# ADR 0006: The object source is an axis owned by the normalizer

DAMICORE measures bytes. Objects reach the distance stage either by splitting a
tabular dataset or by already being files, and both are the same concern:
produce verified object bytes plus the manifest that names them.

`damicore_normalizer` owns that axis. Five of the six steps it already performs
-- validate the source, refuse a non-empty output directory, detect input drift,
re-verify each written object against its size and SHA-256, write the manifest
atomically -- are independent of where the bytes came from. Only object
production varies, and it now varies across three cases: delimited text,
spreadsheet, and adopted files.

The orchestrator does not build manifests. One producer of the inter-stage
contract is worth more than a package name that reads as tabular-only, so the
distribution keeps its name; `materialize_objects` is the entry point and
`normalize_csv` remains a documented wrapper for delimited datasets.
