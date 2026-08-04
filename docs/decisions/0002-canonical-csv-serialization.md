# ADR 0002: Canonical CSV serialization

CSV values remain text. Columns use one compact JSON string per line and rows
use one compact JSON array per line. UTF-8 and LF make bytes independent of
chunking and platform, which makes NCD inputs reproducible and hashable.
