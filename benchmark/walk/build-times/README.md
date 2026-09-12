# Preliminary study (RQ3, Section 5.3.3): per-commit JAR build times

`measure_build_times.py` checks out the 50 latest commits of each library in the longitudinal
corpus and times a full compile-and-package run (Maven, Gradle, or ant), without running any tests.

The corpus is read from [`../walk.yaml`](../walk.yaml). Builds run sequentially, since the
measurement is wall-clock time. Expect the full corpus to take on the order of a day.

## Running

```bash
uv run python measure_build_times.py --work-dir tmp-build
```

| Flag | Purpose |
| --- | --- |
| `--repos google__guava ...` | restrict to a subset (`owner__repo`) |
| `--commits N` | commits per repository (default 50) |
| `--dry-run` | print the plan without building |
| `--resume` | append to an existing CSV, skipping already-measured commits |
| `--summary-only` | print per-repository medians from an existing CSV |
| `--skip-difficult` | skip the three repositories listed under *Coverage* |
| `--timeout` | per-build timeout in seconds (default 1800) |

Requires `git`, a JDK, `mvn`, and `ant` on `PATH`; Gradle projects use their bundled wrapper.
Clones are reused between runs, and Maven builds share a local repository cache under `--work-dir`.

## Output

A CSV at `results/longitudinal/walk/notebooks/library-build-times.csv` (override with `--output`),
one row per build attempt:

`timestamp_utc, repo_name, repo_path, default_ref, commit_index, commit, commit_subject,
build_tool, build_command, elapsed_seconds, exit_code, outcome, message`

`outcome` is `success` or `build_failed`; timeouts and missing build tools are recorded as
`build_failed` with an explanatory `message`.

[`build_times.ipynb`](../../../results/longitudinal/walk/notebooks/build_times.ipynb) reads this
file, computes each repository's median build time, and multiplies it by the library's commit count
from `notebooks/data/*-commits.csv` to produce the whole-history estimates.

## Build commands

The command is detected per commit — `gradlew` → `mvnw` → `pom.xml` → `build.xml`. Four
repositories need an override, recorded in `BUILD_OVERRIDES`:

| Repository | Command | Why |
| --- | --- | --- |
| `google__guava` | `mvnw clean install` | `guava-parent` must be installed before the `guava` module resolves |
| `square__retrofit` | `gradlew :retrofit:jar` | `assemble` also builds every sample and adapter |
| `testng-team__testng` | `gradlew assemble -PjdkBuildVersion=21` | build requires an explicit JDK version |
| `projectlombok__lombok` | `ant dist` | ant-only build |

`REF_OVERRIDES` pins the four repositories measured on a branch other than `origin/HEAD`:
`jackson-core` and `jackson-databind` on `3.x`, `logging-log4j2` on `2.x`, `retrofit` on `trunk`.

## Coverage

The corpus holds 29 libraries across 28 repositories; `log4j-core` and `log4j-api` share
`apache/logging-log4j2`. Three repositories — `protocolbuffers/protobuf`, `mysql/mysql-connector-j`,
and `assertj/assertj` — need toolchains beyond git, a JDK, Maven, Gradle, and ant. Their build
failures are recorded like any other; pass `--skip-difficult` to leave them out.
