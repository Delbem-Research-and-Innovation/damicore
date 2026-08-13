# ADR 0007: A run directory is self-contained

Adopted files are copied into the run directory rather than referenced where
they live. The property being protected is not disk usage: `load_result`,
`DamicoreResult.save`, checkpoint resume, and every hash re-verification assume
that each object is a regular file contained in the artifact root.

Referencing a corpus in place would create two classes of run -- one whose
artifacts are complete and one whose artifacts point outward -- for a saving the
delimited path never took either, since normalized objects are already written
and are already roughly input-sized. With the default `keep_normalized=False`
the copy is deleted once verification succeeds.

Symlinks stay rejected. Hardlinks were measured to satisfy containment with no
extra blocks, and are still refused: they are same-filesystem only, so the
fallback would be silent, and they leave the run's object and the user's file
sharing one inode, where a later edit mutates a completed artifact.
