"""Measure the cost of building a JAR at every commit, for the RQ3 corpus.

The preliminary study of Section 5.3.3: for each library of the longitudinal
corpus, check out its N latest commits and time a full compile-and-package run
(Maven, Gradle, or ant as appropriate), without running any tests. The median
per-commit build time is used by
`results/longitudinal/walk/notebooks/build_times.ipynb` to extrapolate what a
JAR-based tool such as japicmp or Revapi costs over a whole history.

The corpus is read from `benchmark/walk/walk.yaml`.

Output is a CSV with one row per build attempt, written by default to the path
the notebook reads:

    results/longitudinal/walk/notebooks/library-build-times.csv

Builds run strictly sequentially: the measurement is wall-clock time, so
overlapping builds would distort it.

Usage:
    uv run python measure_build_times.py --work-dir /data/tmp-build
    uv run python measure_build_times.py --repos google__guava --commits 10
    uv run python measure_build_times.py --summary-only
"""

from __future__ import annotations

import argparse
import csv
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WALK_CONFIG = REPO_ROOT / "benchmark" / "walk" / "walk.yaml"
DEFAULT_OUTPUT = (
    REPO_ROOT / "results" / "longitudinal" / "walk" / "notebooks" / "library-build-times.csv"
)

# Column order consumed by build_times.ipynb; do not reorder.
FIELDNAMES = [
    "timestamp_utc",
    "repo_name",
    "repo_path",
    "default_ref",
    "commit_index",
    "commit",
    "commit_subject",
    "build_tool",
    "build_command",
    "elapsed_seconds",
    "exit_code",
    "outcome",
    "message",
]

# The only two outcomes the notebook accepts; timeouts and crashes are reported
# as `build_failed` with an explanatory message.
OUTCOME_SUCCESS = "success"
OUTCOME_FAILED = "build_failed"

# Repositories measured on a branch other than the one `origin/HEAD` points at.
REF_OVERRIDES = {
    "FasterXML__jackson-core": "3.x",
    "FasterXML__jackson-databind": "3.x",
    "apache__logging-log4j2": "2.x",
    "square__retrofit": "trunk",
}

# Repositories where the auto-detected command does not produce a JAR.
BUILD_OVERRIDES = {
    # guava-parent must be installed before the guava module resolves.
    "google__guava": ("maven", ["sh", "./mvnw", "-B", "clean", "install", "-DskipTests"]),
    # `assemble` builds every sample and adapter; only the library matters.
    "square__retrofit": ("gradle", ["sh", "./gradlew", "--no-daemon", "clean", ":retrofit:jar", "-x", "test"]),
    "testng-team__testng": (
        "gradle",
        ["sh", "./gradlew", "--no-daemon", "clean", "assemble", "-x", "test", "-PjdkBuildVersion=21"],
    ),
    "projectlombok__lombok": ("ant", ["ant", "-noinput", "dist"]),
}

# Repositories needing toolchains beyond git, a JDK, Maven, Gradle, and ant.
# They are attempted like any other unless --skip-difficult is passed.
KNOWN_DIFFICULT = {
    "protocolbuffers__protobuf",
    "mysql__mysql-connector-j",
    "assertj__assertj",
}


@dataclass(frozen=True)
class Repository:
    name: str  # owner__repo
    url: str
    libraries: tuple[str, ...]


@dataclass(frozen=True)
class BuildSpec:
    tool: str
    command: list[str]


def log(message: str) -> None:
    print(message, flush=True)


def run_git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {repo}: {result.stderr.strip()}")
    return result.stdout.strip()


def load_corpus(config: Path) -> list[Repository]:
    """Read the RQ3 corpus from walk.yaml, collapsing libraries that share a repo."""
    data = yaml.safe_load(config.read_text())
    by_name: dict[str, tuple[str, list[str]]] = {}
    for entry in data.get("repositories", []):
        url = entry["url"].rstrip("/")
        name = url.removeprefix("https://github.com/").replace("/", "__")
        url_, libs = by_name.setdefault(name, (url, []))
        libs.append(entry["libraryId"])
    return [Repository(name, url, tuple(libs)) for name, (url, libs) in sorted(by_name.items())]


def ensure_clone(repo: Repository, work_dir: Path, depth: int | None) -> Path:
    path = work_dir / repo.name
    if (path / ".git").is_dir():
        log(f"  reusing clone at {path}")
        return path

    log(f"  cloning {repo.url} -> {path}")
    cmd = ["git", "clone", "--quiet"]
    if depth:
        cmd += ["--depth", str(depth)]
    cmd += [repo.url, str(path)]
    subprocess.run(cmd, check=True)
    return path


def resolve_ref(repo: Repository, path: Path) -> str:
    """Return the full remote-tracking ref this repository is measured on."""
    if override := REF_OVERRIDES.get(repo.name):
        return f"refs/remotes/origin/{override}"

    head = run_git(path, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
    if head:
        return head
    for candidate in ("main", "master"):
        if run_git(path, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{candidate}", check=False):
            return f"refs/remotes/origin/{candidate}"
    raise RuntimeError(f"cannot determine default ref for {repo.name}")


def detect_build(repo: Repository, path: Path, m2_cache: Path) -> BuildSpec:
    """Pick the build command, honouring per-repository overrides."""
    if override := BUILD_OVERRIDES.get(repo.name):
        tool, command = override
        if tool == "maven":
            command = [*command, f"-Dmaven.repo.local={m2_cache}"]
        return BuildSpec(tool, command)

    if (path / "gradlew").is_file():
        return BuildSpec("gradle", ["sh", "./gradlew", "--no-daemon", "clean", "assemble", "-x", "test"])
    maven_args = ["-B", "clean", "package", "-DskipTests", f"-Dmaven.repo.local={m2_cache}"]
    if (path / "mvnw").is_file():
        return BuildSpec("maven", ["sh", "./mvnw", *maven_args])
    if (path / "pom.xml").is_file():
        return BuildSpec("maven", ["mvn", *maven_args])
    if (path / "build.xml").is_file():
        return BuildSpec("ant", ["ant", "-noinput", "dist"])
    raise RuntimeError(f"no recognised build file in {path}")


def latest_commits(path: Path, ref: str, count: int) -> list[tuple[str, str]]:
    """Return the `count` newest commits of `ref`, newest first, as (sha, subject)."""
    raw = run_git(path, "log", ref, f"--max-count={count}", "--format=%H%x1f%s")
    commits = []
    for line in raw.splitlines():
        sha, _, subject = line.partition("\x1f")
        commits.append((sha, subject))
    return commits


def load_done(output: Path) -> set[tuple[str, str]]:
    """(repo_name, commit) pairs already measured, so --resume never duplicates rows."""
    if not output.is_file():
        return set()
    with output.open(newline="") as handle:
        return {(row["repo_name"], row["commit"]) for row in csv.DictReader(handle)}


def build_once(path: Path, spec: BuildSpec, timeout: int) -> tuple[float, int, str, str]:
    """Run one build, returning (elapsed_seconds, exit_code, outcome, message)."""
    started = time.perf_counter()
    try:
        result = subprocess.run(
            spec.command,
            cwd=path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return time.perf_counter() - started, 124, OUTCOME_FAILED, f"timed out after {timeout}s"
    except OSError as error:  # build tool not installed
        return time.perf_counter() - started, 127, OUTCOME_FAILED, str(error)

    elapsed = time.perf_counter() - started
    if result.returncode == 0:
        return elapsed, 0, OUTCOME_SUCCESS, ""
    tail = (result.stderr or result.stdout or "").strip().splitlines()
    return elapsed, result.returncode, OUTCOME_FAILED, " ".join(tail[-5:])[:500]


def measure_repository(
    repo: Repository,
    path: Path,
    args: argparse.Namespace,
    m2_cache: Path,
    done: set[tuple[str, str]],
    writer: csv.DictWriter,
    handle,
) -> None:
    ref = resolve_ref(repo, path)
    commits = latest_commits(path, ref, args.commits)
    log(f"  ref={ref}  commits={len(commits)}")

    for index, (sha, subject) in enumerate(commits, start=1):
        if (repo.name, sha) in done:
            log(f"  [{index:>3}/{len(commits)}] {sha[:10]} skipped (already measured)")
            continue

        try:
            run_git(path, "checkout", "--quiet", "--detach", sha)
            if args.clean_worktree:
                run_git(path, "clean", "-xdfq")
            # Detected per commit: build files come and go over a history.
            spec = detect_build(repo, path, m2_cache)
        except RuntimeError as error:
            log(f"  [{index:>3}/{len(commits)}] {sha[:10]} unbuildable: {error}")
            spec = BuildSpec("unknown", [])
            elapsed, code, outcome, row_message = 0.0, 128, OUTCOME_FAILED, str(error)[:500]
        else:
            elapsed, code, outcome, row_message = build_once(path, spec, args.timeout)
            log(f"  [{index:>3}/{len(commits)}] {sha[:10]} {outcome:<12} {elapsed:7.2f}s")

        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "repo_name": repo.name,
                "repo_path": repo.name,
                "default_ref": ref,
                "commit_index": index,
                "commit": sha,
                "commit_subject": subject,
                "build_tool": spec.tool,
                "build_command": " ".join(spec.command),
                "elapsed_seconds": f"{elapsed:.6f}",
                "exit_code": code,
                "outcome": outcome,
                "message": row_message,
            }
        )
        handle.flush()


def print_summary(output: Path) -> None:
    """Compile the per-library medians the notebook extrapolates from."""
    if not output.is_file():
        log(f"No results at {output}")
        return

    with output.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        log("No rows recorded.")
        return

    by_repo: dict[str, list[dict]] = {}
    for row in rows:
        by_repo.setdefault(row["repo_name"], []).append(row)

    log(f"\n{'repository':40s} {'n':>4} {'ok':>4} {'median(s)':>10} {'mean(s)':>9}  tool")
    log("-" * 82)
    for name, group in sorted(by_repo.items()):
        times = [float(r["elapsed_seconds"]) for r in group]
        successes = sum(r["outcome"] == OUTCOME_SUCCESS for r in group)
        tool = group[0]["build_tool"]
        log(
            f"{name:40s} {len(group):>4} {successes:>4} "
            f"{statistics.median(times):>10.2f} {statistics.mean(times):>9.2f}  {tool}"
        )
    log("-" * 82)
    log(f"{len(rows)} build attempts across {len(by_repo)} repositories")
    log(
        "\nWhole-history extrapolation (Table 'tab:preliminary') is computed by "
        "results/longitudinal/walk/notebooks/build_times.ipynb,\nwhich multiplies these medians "
        "by each library's commit count from notebooks/data/*-commits.csv."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure per-commit JAR build times for the RQ3 longitudinal corpus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--work-dir", type=Path, default=Path("build-times-workdir"),
                        help="Directory holding the clones and the shared Maven cache.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="CSV consumed by build_times.ipynb.")
    parser.add_argument("--commits", type=int, default=50,
                        help="Number of latest commits to build per repository.")
    parser.add_argument("--repos", nargs="*", default=None,
                        help="Restrict to these repositories (owner__repo). Default: whole corpus.")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="Per-build timeout in seconds.")
    parser.add_argument("--depth", type=int, default=None,
                        help="Shallow-clone depth. Omit for full clones (safer: some builds "
                             "call git describe).")
    parser.add_argument("--clean-worktree", action="store_true",
                        help="Run 'git clean -xdf' between commits, on top of each build tool's "
                             "own clean task. Slower.")
    parser.add_argument("--skip-difficult", action="store_true",
                        help=f"Skip {', '.join(sorted(KNOWN_DIFFICULT))}, which need toolchains "
                             "beyond git, a JDK, Maven, Gradle, and ant.")
    parser.add_argument("--resume", action="store_true",
                        help="Append to an existing CSV, skipping (repo, commit) pairs already in it.")
    parser.add_argument("--summary-only", action="store_true",
                        help="Print the per-repository summary of an existing CSV and exit.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the plan (repositories, refs, commands) without building.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.summary_only:
        print_summary(args.output)
        return 0

    corpus = load_corpus(WALK_CONFIG)
    if args.repos:
        wanted = set(args.repos)
        unknown = wanted - {repo.name for repo in corpus}
        if unknown:
            log(f"Unknown repositories: {', '.join(sorted(unknown))}")
            return 2
        corpus = [repo for repo in corpus if repo.name in wanted]
    if args.skip_difficult:
        corpus = [repo for repo in corpus if repo.name not in KNOWN_DIFFICULT]

    for tool in ("git", "mvn", "ant"):
        if shutil.which(tool) is None:
            log(f"warning: '{tool}' not found on PATH; repositories needing it will fail")

    work_dir = args.work_dir.expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    m2_cache = work_dir / "cache" / "m2"
    m2_cache.mkdir(parents=True, exist_ok=True)

    log(f"Corpus:   {len(corpus)} repositories from {WALK_CONFIG.relative_to(REPO_ROOT)}")
    log(f"Commits:  {args.commits} latest per repository")
    log(f"Work dir: {work_dir}")
    log(f"Output:   {args.output}")

    if args.dry_run:
        for repo in corpus:
            libs = ", ".join(repo.libraries)
            override = " (build override)" if repo.name in BUILD_OVERRIDES else ""
            log(f"  {repo.name:40s} {libs}{override}")
        return 0

    done = load_done(args.output) if args.resume else set()
    if done:
        log(f"Resuming: {len(done)} build attempts already recorded")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_header = not (args.resume and args.output.is_file())
    mode = "a" if args.resume and args.output.is_file() else "w"

    with args.output.open(mode, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        if write_header:
            writer.writeheader()

        for position, repo in enumerate(corpus, start=1):
            log(f"\n[{position}/{len(corpus)}] {repo.name}  ({', '.join(repo.libraries)})")
            try:
                path = ensure_clone(repo, work_dir, args.depth)
                measure_repository(repo, path, args, m2_cache, done, writer, handle)
            except (RuntimeError, subprocess.CalledProcessError) as error:
                log(f"  skipping {repo.name}: {error}")

    print_summary(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
