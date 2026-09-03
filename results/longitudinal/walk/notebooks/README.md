# Longitudinal analysis notebooks (RQ3)

Analyses of the commit-level walk of 29 Java libraries (186,946 commits).

Environment is managed from the repo root (`uv sync` once). Then, from here:

```bash
uv run jupyter lab
```

## Data

- `data/<lib>-commits.csv`: one row per analysed commit: churn, API size, exported/internal
  symbol counts, BC counts, and the wall-clock cost of each pipeline phase.
- `data/<lib>-bcs.csv`: one row per detected breaking change: kind, compatibility, impacted
  symbol, and whether it falls outside the public API (`is_excluded_symbol`,
  `is_internal_removal`).
- `libraries.csv`: Java LoC per library (`cloc`).
- `library-build-times.csv`: `mvn/gradle/ant package` timings for the last 50 commits of
  each library, used to estimate what a JAR-based tool would cost. Regenerate it with
  [`benchmark/walk/build-times`](../../../../benchmark/walk/build-times/).

## Notebooks

- `build_times.ipynb`: the preliminary study (paper Section 5.3.3) — per-library build success
  rates and median build times, extrapolated to whole-history JAR construction cost.
- `longitudinal.ipynb`: API evolution and breaking changes over each history.
- `performance.ipynb`: Roseau's per-phase runtime across the corpus.
