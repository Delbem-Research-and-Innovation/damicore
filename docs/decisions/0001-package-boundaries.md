# ADR 0001: Package boundaries

The four stage distributions are independently installable and never import a
sibling. Only `damicore` depends on and sequences them. Paths and versioned
artifacts are the integration boundary; no shared core package is introduced.
