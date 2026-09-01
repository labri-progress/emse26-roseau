# Longitudinal analysis notebooks (RQ3)

Analyses of the commit-level walk of 29 Java libraries (184,246 commits).

```bash
uv sync && uv run jupyter lab
```

## Data

- `data/<lib>-commits.csv`: one row per analysed commit: churn, API size, exported/internal
  symbol counts, BC counts, and the wall-clock cost of each pipeline phase.
- `data/<lib>-bcs.csv`: one row per detected breaking change: kind, compatibility, impacted
  symbol, and whether it falls outside the public API (`is_excluded_symbol`,
  `is_internal_removal`).
- `libraries.csv`: Java LoC per library (`cloc`).
- `library-build-times.csv`: `mvn/gradle/ant package` timings for the last 50 commits of
  each library, used to estimate what a JAR-based tool would cost.
