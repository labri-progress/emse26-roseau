# Exclusion-convention inventory

This directory contains the reproducible inventory used to check the common
annotation and package-name exclusions in `benchmark/walk/walk.yaml`.

Regenerate the CSV data from the local corpus clones with:

```bash
uv run python results/exclusions/scan_conventions.py \
  --clones-dir clones/roseau-0.7.0
```

The scanner reads each library's configured source roots at `endSha`, without
changing the clone's worktree. If a source root was removed before `endSha`, it
uses the latest source snapshot still present within the configured commit
range. Comments and string literals are removed before annotations and package
declarations are counted.

Open `exclusions.ipynb` for the tables, plots, and conclusions.
