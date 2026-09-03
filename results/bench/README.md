# RQ2 performance analysis

`perf_results.ipynb` analyses `jmh-result.json` (produced by `java -jar target/benchmarks.jar -rf json` in [../../benchmark](../../benchmark/)).

Environment is managed from the repo root (`uv sync` once). Then, from here:

```bash
uv run jupyter lab
```
