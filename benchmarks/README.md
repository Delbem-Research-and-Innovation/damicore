# Benchmarks

`benchmark_large_csv.py` covers the two measurements of specification section 24.4.

The large-input benchmark generates a 2 GiB, 64-column CSV and measures peak RSS during
preflight against the 1.5 GiB budget. `--skip-large` omits it when the working set does not
fit; the weekly dependency audit does exactly that.

The algorithm benchmark sweeps object counts 100, 250, 500, and 1,000, recording time, disk,
peak RSS, and pairs per second for each. Those counts are the default because the
specification requires them; `--objects` narrows the sweep and prints to stderr what was
dropped. Neighbor Joining is cubic, so the full sweep takes minutes rather than seconds.

Benchmarks are separate from the blocking test suite. Version 0.1 defines no portable time
threshold: a regression beyond 25% against the median of the last three runs on the same
runner is an alert, not an automatic block.
