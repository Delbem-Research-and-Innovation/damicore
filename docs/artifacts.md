# Artifact contract

A completed run contains `manifest.json`, `report.json`, `distance.npy`,
`labels.json`, `tree.json`, `tree.nwk`, `membership.csv`, `clusters.json`, and
checkpoints. Diagnostics and normalized objects are optional according to the
run configuration.

JSON is schema version 1, UTF-8, two-space indented, sorted, finite-only, and LF
terminated. Internal artifact paths are relative and contained in the run
directory. Manifests and small results use same-directory temporary files,
`fsync`, and atomic replacement. `load_result` verifies every declared size and
SHA-256 before returning a read-only matrix view.

Only `completed` is a successful terminal state. `failed` and `interrupted`
reports remain diagnostic and may be resumed when their input, configuration,
schema, runtime fingerprint, receipts, and checkpoints remain compatible.
