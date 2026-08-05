# Benchmarks

`benchmark_large_csv.py` covers the two measurements of specification section 24.4.

The large-input benchmark generates a 2 GiB, 64-column CSV and measures peak RSS during
preflight against the 1.5 GiB budget. `--target-bytes` scales that working set down when the
available disk cannot hold it.

`--select` chooses which of the two measurements to run, because they cost very differently:
`large` needs multiple gigabytes of disk, `sweep` needs minutes of CPU, and `both` is the
default. The weekly workflow runs them as two steps so a failure names the one that regressed.

The algorithm benchmark sweeps object counts 100, 250, 500, and 1,000, recording time, disk,
peak RSS, and pairs per second for each. Those counts are the default because the
specification requires them; `--objects` narrows the sweep and prints to stderr what was
dropped. Neighbor Joining is cubic, so the full sweep takes minutes rather than seconds.

Benchmarks are separate from the blocking test suite. Version 0.1 defines no portable time
threshold: a regression beyond 25% against the median of the last three runs on the same
runner is an alert, not an automatic block.
