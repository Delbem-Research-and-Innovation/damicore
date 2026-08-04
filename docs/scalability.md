# Scalability and resource gates

For `n` objects, DAMICORE computes `n(n-1)/2` NCD pairs, stores an `n × n`
float64 matrix, uses another same-sized on-disk Neighbor Joining workspace, and
runs Neighbor Joining in cubic time. Memory maps avoid loading those matrices
as ordinary arrays; they do not change algorithmic complexity.

Preflight scans the full CSV without creating object files and calculates exact
normalized bytes plus conservative memory and disk bounds. Default limits cap
objects at 1,000, pairs at 500,000, and each matrix at 512 MiB. `estimate`
always returns its ordered violations. `run` turns any violation into
`ResourceLimitError`; free disk can never be bypassed.

The supported large-input shape is many CSV bytes but a moderate object count,
typically columns. Splitting a large file into rows can create millions of
objects and is deliberately rejected.
