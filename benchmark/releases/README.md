# Commit-level vs. release-level breaking changes

The longitudinal study walks the first-parent history of each library's default branch, reporting
breaking changes between consecutive commits. This directory measures how those relate to the
breaking changes a **release-level** analysis of the same libraries reports.

Two studies. Data and analysis land in [`results/releases`](../../results/releases/).

## Tag-level study

A release-level walk of a history is the subsequence of its commits that carry a release tag,
diffed consecutively:

| | | step |
|---|---|---|
| **C** | the commit-level walk's breaking changes, summed over the commits between two tags | commit |
| **T** | one Roseau diff between the two tagged commits | tag |

Branch, source roots, exclusion rules, extractor and Roseau build are identical on both sides, so
granularity is the only variable. Nothing is downloaded and no artefact is built.

```bash
uv sync                                     # once, from the repo root
cd benchmark/releases
mvn -DskipTests package                     # the diff runner

uv run python tag_intervals.py              # tags on the default branch -> intervals + sources
./run_diffs.sh --tags                       # one Roseau diff per tag-to-tag interval
uv run python analyze_tags.py               # compare C and T
uv run python verify_tags.py                # self-checks

uv run python tag_intervals.py --include-prereleases --prefix tagall   # sensitivity
./run_diffs.sh --tags tagall
uv run python analyze_tags.py --prefix tagall
```

`tag_intervals.py` → `tag-coverage.csv`, `tag-intervals.csv`, `tag-inputs.csv`. A tag names a
version when, after stripping a non-digit prefix (`v`, `r`, `rel/commons-io-`), what remains starts
with a digit; pre-release qualifiers are excluded unless `--include-prereleases`. Only tags whose
peeled commit lies on the walked chain are kept, so releases cut on a release branch are out of
scope. Consecutive tagged commits form the intervals; several tags on one commit collapse to one
step. Source trees are exported with `git archive`, taking the first `sourceRoot` present at that
commit, as `GitWalker` does.

`PairDiffer` → `tag-pairs.csv`, `tag-bcs.csv`. One `Roseau.diff` per interval: JDT extractor, empty
classpath, per-library exclusions read from `walk.yaml`.

`analyze_tags.py` → `tag-comparison.csv`, `tag-comparison-fate-by-kind.csv`,
`tag-comparison-unattributed.csv`. Identifies a breaking change by `(kind, impacted_symbol_fqn)`
and intersects `C` and `T` per interval. Aggregates are reported pooled, per library and per
interval, because one library contributes a third of the intervals. `--erased` matches on
generics-erased signatures, `--all-symbols` keeps breaking changes on excluded symbols.

`verify_tags.py` asserts that the two walks measure the same thing: tags resolve to the recorded
walked commit, the exported source root is the one the walk used, `commit_events` agrees with the
walk's own per-commit counter, and — the end-to-end check — every interval spanning a single commit
reproduces that commit's breaking-change rows field for field, exclusion decisions included.

## Released-JAR study

Anchors Maven Central releases onto the walked history and produces three views per interval:

| | | modality | granularity |
|---|---|---|---|
| **C** | the walk's per-commit breaking changes, summed over the interval | source | incremental |
| **S** | one Roseau diff between the two commits the releases were cut from | source | cumulative |
| **R** | one Roseau diff between the two released JARs | bytecode | cumulative |

`S` vs `R` isolates modality: whether Roseau's source and bytecode models agree on real artefacts.
`C` vs `R` additionally mixes in releases cut off the default branch, artefacts built from source
roots outside `walk.yaml`, and build-time transformation of the JAR — use the tag-level study to
measure granularity alone.

```bash
cd benchmark/releases
uv run python fetch_releases.py                    # release inventory from Maven Central
uv run python anchor_releases.py                   # anchor releases onto the walked history
uv run python prepare_pairs.py                     # download JARs, export source trees
mvn -DskipTests package && ./run_diffs.sh          # the JAR pass, then the source pass
uv run python analyze.py --tagged-only             # compare C, S and R
uv run python analyze.py                           # sensitivity: every mainline interval
uv run python analyze.py --tagged-only --erased    # sensitivity: generics-erased matching
```

`fetch_releases.py` reads the Maven Central directory listing for every `group:artifact` a
library's source root publishes under (`coords.py`; several libraries change coordinates
mid-history, e.g. `commons-lang` → `commons-lang3`). The listing gives the version list and each
version's publication date in one request.

`anchor_releases.py` locates the commit each release was cut from and projects it onto the walked
history: `tag_exact` (the tag is a walked commit), `tag_ancestor` (the tag is off the walked line,
so the anchor is the newest walked commit that is an ancestor of it — binary search, valid because
ancestry is monotone along the chain), `timestamp` (no tag matches; the anchor is the last walked
commit predating publication), or `out_of_range`. It then keeps each library's mainline release
chain: releases in publication order whose anchor *and* version both move forward. `tag_anchored`
marks intervals with both endpoints tag-located — the `--tagged-only` set.

`prepare_pairs.py` downloads both JARs and exports both anchor commits. `PairDiffer` diffs each
pair; the extractor follows the location, ASM for a JAR and JDT for a source tree. `analyze.py`
intersects the three sets and emits `comparison-*.csv` with `*-fate-by-kind.csv` and
`*-residual.csv`.

## Requirements

- The longitudinal walk output in `results/longitudinal/walk/notebooks/data/` (shipped here).
- The 29 clones the walk visited, under `/data/<owner>__<repo>/` (override with `CLONES=...`);
  `walk.yaml` records the paths as they were on the run machine and the scripts relocate them.
- `roseau-core` built from the same `git-walk` commit as the walk (`0.7.0-SNAPSHOT`) and installed
  locally: `cd roseau && ./mvnw -DskipTests install`. A different Roseau build would confound tool
  version with the effect being measured.
- Scratch space for the exported source trees (`WORK=`, default `/data/release-study`): ~5 GB, ~6 GB
  with the JAR downloads. Only the released-JAR study touches the network.

Runtimes on 10 threads: the tag-level diff pass ~2 min, the JAR study's JAR pass ~8 min and its
source pass ~2 min.

## Limitations

- A library that cuts releases on release branches contributes few or no tag-level intervals: five
  do (`commons-beanutils`, `commons-collections`, `httpclient`, `protobuf-java`, `spring-context`).
  `mockito-core` contributes 36 % of the intervals, hence the per-library medians.
- Anchoring a release by timestamp is unreliable for artefacts backfilled into Maven Central years
  after release (the early Apache Commons versions, gson 1.x); `analyze.py --tagged-only` excludes
  them.
- `jackson-core` 3.x ships a multi-release JAR carrying the same shaded class in the base directory
  and under `META-INF/versions/{17,21}`; Roseau 0.7.0-SNAPSHOT's ASM extractor rejects it as a
  duplicated type, so three JAR-study intervals have no JAR diff.
- Roseau is not bit-for-bit deterministic across runs. Re-running the tag-level pass reproduces
  45,781 of 45,781 breaking-change rows, but one moves between two supertypes: joda-time
  `0.9.5 → 0.9.8` attributes a `getChronology()` removal to `DateTimePrinter` in one run and to
  `DateTimeParser` in the next, because `DateTimeFormatterBuilder` implements both and the symbol
  matcher breaks the tie on iteration order.
