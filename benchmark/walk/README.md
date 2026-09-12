# Longitudinal walk (RQ3)

[`walk.yaml`](walk.yaml) fixes the 29 libraries, commit ranges, source roots,
and public-API exclusions used in the paper. Paths are relative to the
replication-package root. Place repository clones at
`clones/<GitHub owner>__<repository>`; the repository URLs are recorded in the
configuration.

The walk requires Roseau `0.7.0-SNAPSHOT` with `BatchGitWalker`. With its checkout at `roseau/`, run from the
replication-package root:

```bash
./roseau/mvnw -f roseau/pom.xml -pl git -am install -DskipTests
./roseau/mvnw -f roseau/pom.xml -pl git exec:java \
  -Dexec.mainClass=io.github.alien.roseau.git.BatchGitWalker \
  -Dexec.args="$PWD/benchmark/walk/walk.yaml $PWD/results/longitudinal/walk/notebooks/data"
```

The walker writes `<library>-commits.csv` and `<library>-bcs.csv` files read by
the notebooks in
[`results/longitudinal/walk/notebooks`](../../results/longitudinal/walk/notebooks/).
The configuration audit and sampled JAR-build study have their own commands in
[`audit_source_roots.py`](audit_source_roots.py) and
[`build-times`](build-times/).
