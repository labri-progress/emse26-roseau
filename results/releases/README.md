# Commit-level vs. release-level breaking changes

How the commit-level breaking changes of the longitudinal study relate to those a release-level
analysis of the same libraries reports. Pipelines in [`benchmark/releases`](../../benchmark/releases/).

Environment is managed from the repo root (`uv sync` once). Then, from here:

```bash
uv run jupyter lab
```

## Tag-level study

A release-level walk of a default branch is the subsequence of its commits carrying a release tag,
diffed consecutively. Branch, source roots, exclusion rules, extractor and Roseau build are the
same as the commit-level walk, so granularity is the only variable: `C` is the commit-level walk's
breaking changes summed over an interval, `T` is one diff between the two tagged commits.

1,237 tag-to-tag intervals over 81,650 commits in 26 libraries:

| | pooled | median library | median interval |
|---|---|---|---|
| `T` attributable to a single walked commit (`C∩T / T`) | **98.2 %** | 99.2 % | 100 % |
| `C` still present at the next tag (`C∩T / C`) | 38.2 % | 33.9 % | 93.7 % |

The commit-level walk is a near-complete superset of the release-level one — 1.8 % of tag-level
breaking changes match no single commit, and those are composite effects concentrated in the
longest intervals. It additionally reports intermediate churn that projects undo before tagging, so
a commit-level count is not a count of released breaking changes.

That second figure is not a fixed factor; it tracks release cadence:

| commits between tags | 1–10 | 11–30 | 31–100 | 101–300 | >300 |
|---|---|---|---|---|---|
| intervals | 59 | 119 | 169 | 71 | 54 |
| `C` still present at the next tag | 98.9 % | 79.0 % | 76.7 % | 30.9 % | 23.9 % |

Deletions are the least durable kind: 27.6 % of `EXECUTABLE_REMOVED` survive to the next tag,
against 62.8 % of `TYPE_REMOVED` and 58.3 % of `FIELD_REMOVED`.

Restricting to the default branch excludes releases cut on release branches: 5 of 29 libraries
contribute two intervals or fewer, and `mockito-core` contributes 36 % of them, so aggregates are
also given per library. Stepping through pre-release tags as well (`tagall-*`) brings back two
libraries and moves the headline figures by under two points.

Notebook: `commit_vs_tag.ipynb`. Figure: `figures/survival-vs-cadence.pdf`.

## Released-JAR study

Anchors Maven Central releases onto the walked history and compares three views per interval: the
commit-level walk (`C`), one source diff between the two commits the releases were cut from (`S`),
and one diff between the two released JARs (`R`).

Over 1,233 intervals, `S` reproduces 76.7 % of `R` against 77.4 % for `C` — a 0.7 pp difference, so
Roseau's source and bytecode models agree on real artefacts. The remaining 22 % of `R` is
build-time construction of the artefact: shading, generated code, injected module descriptors, and
modules built from source roots the walk does not cover, concentrated in `mysql-connector-j`,
`lombok`, `assertj-core`, `protobuf-java` and `mockito-core`.

Notebook: `commit_vs_released_jar.ipynb`. Figures: `figures/commit-vs-release.pdf`,
`figures/bc-survival-by-library.pdf`.

## Data

Tag-level study (`tag-*`; `tagall-*` steps through pre-release tags too):

- `tag-coverage.csv` — per library: walked commits, tags in the repo, tags on the default branch,
  resulting intervals.
- `tag-intervals.csv` — one row per pair of consecutive tagged commits.
- `tag-pairs.csv`, `tag-bcs.csv` — per-interval statistics and one row per breaking change from the
  tag-to-tag diff.
- `tag-comparison.csv` — the comparison, one row per interval, with
  `tag-comparison-fate-by-kind.csv` and `tag-comparison-unattributed.csv`.

Released-JAR study:

- `releases-all.csv` — every version of every studied coordinate on Maven Central, with its
  publication date and whether it is a stable release.
- `releases-anchored.csv` — one row per stable release inside the walked window: the commit it is
  anchored to, how, and the lag between publication and that commit.
- `intervals.csv` — one row per interval on a library's mainline release chain.
- `jar-pairs.csv`, `jar-bcs.csv`, `source-pairs.csv`, `source-bcs.csv` — per-interval statistics and
  one row per breaking change, for `R` and for `S`.
- `comparison-tagged.csv` — the comparison; `comparison-all.csv` and `comparison-tagged-erased.csv`
  are the sensitivity variants. Each has `*-fate-by-kind.csv` and `*-residual.csv`.
