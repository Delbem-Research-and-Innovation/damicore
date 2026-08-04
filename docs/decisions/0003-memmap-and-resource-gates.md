# ADR 0003: Memory maps and resource gates

The exact distance matrix and Neighbor Joining workspace are float64 `.npy`
memory maps. A mandatory preflight calculates hard bounds before object files
are created. This bounds memory without disguising quadratic storage or cubic
tree construction.
