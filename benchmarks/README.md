# Benchmarks

`benchmark_large_csv.py` measures preflight RSS for a generated CSV and records
NCD/NJ wall time for object counts 16, 32, 64, and 128. Benchmarks are separate
from blocking daily tests; CI can retain their JSON output to compare releases.
