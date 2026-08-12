# ADR 0005: Process pool for distance workers

Distance shards run on `ProcessPoolExecutor` with the `spawn` context. Threads
were measured as the alternative, because zlib releases the GIL and they would
remove the `if __name__ == "__main__":` guard that spawning imposes on callers.

They were rejected on the measurement. NCD needs one fresh `compressobj` per
pair, and at level 6 each allocates roughly 256 KiB of deflate state, so worker
threads contend on the shared heap instead of scaling. On a 400-object CSV of
1.5 KiB objects the distance stage took 15.5 s serial, 5.0 s on four processes,
and 26.9 s on four threads: threads are slower than running serially. Threads
only match processes once objects are large enough for compression to dominate
allocation, around 200 KiB.

`forkserver` was tested and re-imports the caller's `__main__` exactly as `spawn`
does, so no process context removes the guard. The guard requirement is
documented instead, and a dead pool is reported as a `DistanceError` naming both
of its real causes rather than as `BrokenProcessPool`.

Revisit if the compressor changes to one that reuses its state across pairs, or
if per-object sizes in practice move above the crossover.
