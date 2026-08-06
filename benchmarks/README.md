# Benchmarks

`benchmark_large_csv.py` covers the two measurements of specification section 24.4.

The large-input benchmark generates a 2 GiB, 64-column CSV, then measures preflight and
normalization separately. Only the normalization peak is held to the 1.5 GiB budget, because
that is the stage specification section 24.4 names: preflight scans the CSV without writing a
single object file, so it cannot stand in for the stage that does. Normalization writes the
objects, so the working set is roughly twice the CSV; `--target-bytes` scales it down when the
available disk cannot hold both.

Peak RSS comes from `ru_maxrss`, a high-water mark for the whole process. The normalization
figure therefore covers preflight too. That direction is deliberate for a budget: it can raise
a false alarm, never hide an overrun.

`--select` chooses which of the two measurements to run, because they cost very differently:
`large` needs multiple gigabytes of disk, `sweep` needs minutes of CPU, and `both` is the
default. `release.yml` runs `large` at the tag commit, where the RSS budget gates publication;
`benchmark.yml` is dispatchable for either.

The algorithm benchmark sweeps object counts 100, 250, 500, and 1,000, recording time, disk,
peak RSS, and pairs per second for each. Those counts are the default because the
specification requires them; `--objects` narrows the sweep and prints to stderr what was
dropped. Neighbor Joining is cubic, so the full sweep takes minutes rather than seconds.

Measurements always go to stdout; `--output` also writes them as JSON to a path. The workflow
uses it and uploads the file as a run artifact, because the regression rule below compares
against earlier runs and stdout of a finished job cannot be read back. A budget breach is
reported after the measurements are written, so the failing numbers survive too.

Benchmarks are separate from the blocking test suite. Version 0.1 defines no portable time
threshold: a regression beyond 25% against the median of the last three runs on the same
runner is an alert, not an automatic block.
