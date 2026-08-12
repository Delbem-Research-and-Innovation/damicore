# Benchmarks

`benchmark_large_csv.py` covers the project's two resource measurements.

The large-input benchmark generates a 2 GiB, 64-column CSV, then measures preflight and
normalization separately. Only the normalization peak is held to the 1.5 GiB budget, because
that is the stage the budget covers: preflight scans the CSV without writing a
single object file, so it cannot stand in for the stage that does. Normalization writes the
objects, so the working set is roughly twice the CSV; `--target-bytes` scales it down when the
available disk cannot hold both.

Peak RSS comes from `ru_maxrss`, a high-water mark for the whole process. The normalization
figure therefore covers preflight too. That direction is deliberate for a budget: it can raise
a false alarm, never hide an overrun.

`--select` is required and takes exactly one measurement, never both. They cost very
differently — `large` needs multiple gigabytes of disk, `sweep` needs minutes of CPU — but the
reason one process runs one of them is the RSS reading: `ru_maxrss` is a whole-process
high-water mark, so a second measurement would report the first one's peak as its own.
`release.yml` runs `large` at the tag commit, where the RSS budget gates publication;
`benchmark.yml` dispatches either one.

The algorithm benchmark sweeps object counts 100, 250, 500, and 1,000, recording time, disk,
peak RSS, and pairs per second for each. `--objects` narrows the sweep and prints to stderr
what was dropped. Neighbor Joining is cubic in the object count, so each step of the sweep
costs several times the one before it and the full sweep takes minutes rather than seconds.

Measurements always go to stdout; `--output` also writes them as JSON to a path. The workflow
uses it and uploads the file as a run artifact, because the regression rule below compares
against earlier runs and stdout of a finished job cannot be read back. A budget breach is
reported after the measurements are written, so the failing numbers survive too.

Benchmarks are separate from the blocking test suite. Version 0.1 defines no portable time
threshold: a regression beyond 25% against the median of the last three runs on the same
runner is an alert, not an automatic block.
