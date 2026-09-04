#!/usr/bin/env bash
# Runs PairDiffer over the pair files produced by tag_intervals.py or prepare_pairs.py.
#
#   ./run_diffs.sh --tags [prefix] [threads]   # tag-level study  (default prefix: tag)
#   ./run_diffs.sh [threads]                   # JAR study: both the JAR and the source pass
#
# Expects `mvn -DskipTests package` to have run here, and roseau-core 0.7.0-SNAPSHOT (the git-walk
# build the longitudinal study used) to be installed in the local Maven repository.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DATA="${RELEASE_DATA:-$REPO/results/releases/data}"

CP_FILE="$HERE/target/classpath.txt"
mvn -q -f "$HERE/pom.xml" dependency:build-classpath "-Dmdep.outputFile=$CP_FILE"
CP="$HERE/target/classes:$(cat "$CP_FILE")"

run() {
  local inputs="$1" prefix="$2" heap="$3" threads="$4"
  echo ">>> $prefix: $(($(wc -l < "$DATA/$inputs") - 1)) pairs"
  java "-Xmx$heap" -cp "$CP" com.github.alien.bench.releases.PairDiffer \
    "$REPO/benchmark/walk/walk.yaml" "$DATA/$inputs" "$DATA" "$prefix" "$threads"
}

if [[ "${1:-}" == "--tags" ]]; then
  prefix="${2:-tag}"
  run "$prefix-inputs.csv" "$prefix" 48g "${3:-10}"
else
  threads="${1:-10}"
  # Bytecode first: it is the cheap pass, and a failure there is worth seeing before the long one.
  run jar-inputs.csv jar 32g "$threads"
  run source-inputs.csv source 48g "$threads"
fi
