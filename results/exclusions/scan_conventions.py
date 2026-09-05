#!/usr/bin/env python3
"""Inventory Java annotations and package components in the walk corpus.

The scanner reads ``walk.yaml`` and inspects every library at its configured
``endSha`` (or its latest in-range source snapshot if the roots were removed).
Files are streamed from the local Git clones, so their worktrees are never
checked out or modified.

Example:
    uv run python results/exclusions/scan_conventions.py \
        --clones-dir clones/roseau-0.7.0
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import tarfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "benchmark" / "walk" / "walk.yaml"
DEFAULT_CLONES = REPO_ROOT / "clones" / "roseau-0.7.0"
DEFAULT_OUTPUT = Path(__file__).with_name("data")

ANNOTATION_RE = re.compile(
    r"@\s*([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)"
)
PACKAGE_RE = re.compile(
    r"(?m)^\s*package\s+([A-Za-z_$][\w$]*(?:\s*\.\s*[A-Za-z_$][\w$]*)*)\s*;"
)


@dataclass(frozen=True)
class Library:
    library_id: str
    repository: str
    clone: Path
    start_revision: str
    revision: str
    source_roots: tuple[str, ...]


def normalize_java_name(name: str) -> str:
    return re.sub(r"\s*\.\s*", ".", name)


def strip_comments_and_literals(source: str) -> str:
    """Replace comments and character/string contents while preserving lines."""
    result = list(source)
    i = 0
    state = "code"
    while i < len(source):
        if state == "code":
            if source.startswith("//", i):
                result[i : i + 2] = "  "
                i += 2
                state = "line-comment"
            elif source.startswith("/*", i):
                result[i : i + 2] = "  "
                i += 2
                state = "block-comment"
            elif source.startswith('"""', i):
                result[i : i + 3] = "   "
                i += 3
                state = "text-block"
            elif source[i] == '"':
                result[i] = " "
                i += 1
                state = "string"
            elif source[i] == "'":
                result[i] = " "
                i += 1
                state = "character"
            else:
                i += 1
        elif state == "line-comment":
            if source[i] == "\n":
                state = "code"
            else:
                result[i] = " "
            i += 1
        elif state == "block-comment":
            if source.startswith("*/", i):
                result[i : i + 2] = "  "
                i += 2
                state = "code"
            else:
                if source[i] != "\n":
                    result[i] = " "
                i += 1
        elif state == "text-block":
            if source.startswith('"""', i):
                result[i : i + 3] = "   "
                i += 3
                state = "code"
            else:
                if source[i] != "\n":
                    result[i] = " "
                i += 1
        else:  # string or character
            delimiter = '"' if state == "string" else "'"
            if source[i] == "\\" and i + 1 < len(source):
                if source[i] != "\n":
                    result[i] = " "
                if source[i + 1] != "\n":
                    result[i + 1] = " "
                i += 2
            elif source[i] == delimiter:
                result[i] = " "
                i += 1
                state = "code"
            else:
                if source[i] != "\n":
                    result[i] = " "
                i += 1
    return "".join(result)


def repository_name(url: str) -> str:
    return url.rstrip("/").removeprefix("https://github.com/").replace("/", "__")


def minimize_roots(roots: Iterable[str]) -> tuple[str, ...]:
    """Drop duplicate roots and children already covered by a parent root."""
    kept: list[PurePosixPath] = []
    for root in sorted({PurePosixPath(r) for r in roots}, key=lambda p: (len(p.parts), str(p))):
        if not any(root == parent or parent in root.parents for parent in kept):
            kept.append(root)
    return tuple(str(root) for root in kept)


def load_libraries(config: Path, clones_dir: Path) -> list[Library]:
    data = yaml.safe_load(config.read_text())
    libraries = []
    for entry in data["repositories"]:
        recorded_root = Path(entry["gitDir"]).parent
        relative_roots = []
        for source_root in entry["sourceRoots"]:
            try:
                relative_roots.append(str(Path(source_root).relative_to(recorded_root)))
            except ValueError as error:
                raise ValueError(
                    f"{entry['libraryId']}: source root {source_root} is outside {recorded_root}"
                ) from error
        repo = repository_name(entry["url"])
        libraries.append(
            Library(
                entry["libraryId"],
                repo,
                clones_dir / repo,
                entry["startSha"],
                entry["endSha"],
                minimize_roots(relative_roots),
            )
        )
    return libraries


def git_path_exists(clone: Path, revision: str, path: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}:{path}"],
        cwd=clone,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def source_snapshot(library: Library) -> tuple[str, list[str]]:
    """Use endSha, or the latest in-range snapshot before source-root removal."""
    roots = [
        root
        for root in library.source_roots
        if git_path_exists(library.clone, library.revision, root)
    ]
    if roots:
        return library.revision, roots

    candidates: list[tuple[int, str, list[str]]] = []
    for root in library.source_roots:
        changed = subprocess.run(
            ["git", "rev-list", "-n", "1", library.revision, "--", root],
            cwd=library.clone,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        for candidate in (changed, f"{changed}^") if changed else ():
            resolved = subprocess.run(
                ["git", "rev-parse", "--verify", candidate],
                cwd=library.clone,
                capture_output=True,
                text=True,
                check=False,
            )
            if resolved.returncode != 0:
                continue
            revision = resolved.stdout.strip()
            in_range = subprocess.run(
                ["git", "merge-base", "--is-ancestor", library.start_revision, revision],
                cwd=library.clone,
                check=False,
            ).returncode == 0
            existing = [
                root
                for root in library.source_roots
                if git_path_exists(library.clone, revision, root)
            ]
            if in_range and existing:
                timestamp = int(
                    subprocess.run(
                        ["git", "show", "-s", "--format=%ct", revision],
                        cwd=library.clone,
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout
                )
                candidates.append((timestamp, revision, existing))
    if not candidates:
        return library.revision, []
    _, revision, roots = max(candidates)
    return revision, roots


def java_files(library: Library) -> Iterable[tuple[str, str, str]]:
    if not (library.clone / ".git").is_dir():
        raise FileNotFoundError(
            f"missing clone for {library.library_id}: {library.clone}"
        )
    revision, roots = source_snapshot(library)
    if not roots:
        print(
            f"warning: {library.library_id}: no configured source root exists at "
            f"{library.revision}",
            file=sys.stderr,
        )
        return
    if revision != library.revision:
        print(
            f"warning: {library.library_id}: source roots are absent at endSha; "
            f"using latest in-range snapshot {revision}",
            file=sys.stderr,
        )

    process = subprocess.Popen(
        ["git", "archive", "--format=tar", revision, "--", *roots],
        cwd=library.clone,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    seen: set[str] = set()
    with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
        for member in archive:
            if (
                not member.isfile()
                or not member.name.endswith(".java")
                or member.name in seen
            ):
                continue
            seen.add(member.name)
            extracted = archive.extractfile(member)
            if extracted is not None:
                yield revision, member.name, extracted.read().decode("utf-8", errors="replace")
    stderr = process.stderr.read().decode(errors="replace") if process.stderr else ""
    if process.wait() != 0:
        raise RuntimeError(f"git archive failed for {library.library_id}: {stderr.strip()}")


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--clones-dir", type=Path, default=DEFAULT_CLONES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    libraries = load_libraries(args.config.resolve(), args.clones_dir.resolve())
    annotation_occurrences: Counter[tuple[str, str]] = Counter()
    annotation_files: dict[tuple[str, str], set[str]] = defaultdict(set)
    annotation_spellings: dict[tuple[str, str], set[str]] = defaultdict(set)
    package_files: dict[tuple[str, str], set[str]] = defaultdict(set)
    scanned_files: Counter[str] = Counter()

    for library in libraries:
        print(f"Scanning {library.library_id} at {library.revision[:12]}...", flush=True)
        for revision, path, source in java_files(library):
            scanned_files[library.library_id] += 1
            code = strip_comments_and_literals(source)
            file_id = f"{library.repository}@{revision}:{path}"
            for match in ANNOTATION_RE.finditer(code):
                spelling = normalize_java_name(match.group(1))
                if spelling == "interface":
                    continue
                simple_name = spelling.rsplit(".", 1)[-1]
                key = (library.library_id, simple_name)
                annotation_occurrences[key] += 1
                annotation_files[key].add(file_id)
                annotation_spellings[key].add(spelling)
            package_match = PACKAGE_RE.search(code)
            if package_match:
                package = normalize_java_name(package_match.group(1))
                package_files[(library.library_id, package)].add(file_id)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    annotation_rows = []
    for (library_id, annotation), occurrences in annotation_occurrences.items():
        annotation_rows.append(
            {
                "library_id": library_id,
                "annotation": annotation,
                "occurrences": occurrences,
                "files": len(annotation_files[(library_id, annotation)]),
                "source_spellings": ";".join(
                    sorted(annotation_spellings[(library_id, annotation)])
                ),
            }
        )
    annotation_rows.sort(
        key=lambda row: (
            -int(row["occurrences"]),
            str(row["annotation"]),
            str(row["library_id"]),
        )
    )
    write_csv(
        args.output_dir / "annotations-by-library.csv",
        ["library_id", "annotation", "occurrences", "files", "source_spellings"],
        annotation_rows,
    )

    annotation_names = sorted({name for _, name in annotation_occurrences})
    aggregate_annotations = []
    for name in annotation_names:
        keys = [key for key in annotation_occurrences if key[1] == name]
        aggregate_annotations.append(
            {
                "annotation": name,
                "occurrences": sum(annotation_occurrences[key] for key in keys),
                "files": len(set().union(*(annotation_files[key] for key in keys))),
                "libraries": len({key[0] for key in keys}),
                "library_ids": ";".join(sorted({key[0] for key in keys})),
                "source_spellings": ";".join(
                    sorted(set().union(*(annotation_spellings[key] for key in keys)))
                ),
            }
        )
    aggregate_annotations.sort(
        key=lambda row: (
            -int(row["libraries"]),
            -int(row["occurrences"]),
            str(row["annotation"]),
        )
    )
    write_csv(
        args.output_dir / "annotations.csv",
        [
            "annotation",
            "occurrences",
            "files",
            "libraries",
            "library_ids",
            "source_spellings",
        ],
        aggregate_annotations,
    )

    aggregate_packages: dict[str, set[str]] = defaultdict(set)
    package_libraries: dict[str, set[str]] = defaultdict(set)
    for (library_id, package), files in package_files.items():
        aggregate_packages[package].update(files)
        package_libraries[package].add(library_id)
    package_rows = [
        {
            "package": package,
            "files": len(files),
            "libraries": len(package_libraries[package]),
            "library_ids": ";".join(sorted(package_libraries[package])),
        }
        for package, files in aggregate_packages.items()
    ]
    package_rows.sort(
        key=lambda row: (
            -int(row["libraries"]),
            -int(row["files"]),
            str(row["package"]),
        )
    )
    write_csv(
        args.output_dir / "packages.csv",
        ["package", "files", "libraries", "library_ids"],
        package_rows,
    )

    component_packages: dict[str, set[str]] = defaultdict(set)
    component_files: dict[str, set[str]] = defaultdict(set)
    component_libraries: dict[str, set[str]] = defaultdict(set)
    for (library_id, package), files in package_files.items():
        for component in package.split("."):
            component_packages[component].add(package)
            component_files[component].update(files)
            component_libraries[component].add(library_id)
    component_rows = [
        {
            "component": component,
            "packages": len(component_packages[component]),
            "files": len(component_files[component]),
            "libraries": len(component_libraries[component]),
            "library_ids": ";".join(sorted(component_libraries[component])),
            "example_packages": ";".join(sorted(component_packages[component])[:5]),
        }
        for component in component_packages
    ]
    component_rows.sort(
        key=lambda row: (
            -int(row["libraries"]),
            -int(row["files"]),
            str(row["component"]),
        )
    )
    write_csv(
        args.output_dir / "package-components.csv",
        [
            "component",
            "packages",
            "files",
            "libraries",
            "library_ids",
            "example_packages",
        ],
        component_rows,
    )

    scanned_libraries = sum(files > 0 for files in scanned_files.values())
    write_csv(
        args.output_dir / "summary.csv",
        [
            "configured_libraries",
            "scanned_libraries",
            "repositories",
            "java_files",
            "annotation_names",
            "packages",
            "package_components",
        ],
        [
            {
                "configured_libraries": len(libraries),
                "scanned_libraries": scanned_libraries,
                "repositories": len({library.repository for library in libraries}),
                "java_files": sum(scanned_files.values()),
                "annotation_names": len(annotation_names),
                "packages": len(aggregate_packages),
                "package_components": len(component_packages),
            }
        ],
    )
    print(
        f"Scanned {sum(scanned_files.values()):,} Java files for {scanned_libraries}/"
        f"{len(libraries)} libraries in "
        f"{len({library.repository for library in libraries})} repositories."
    )
    print(
        f"Found {len(annotation_names):,} annotation simple names, "
        f"{len(aggregate_packages):,} packages, and {len(component_packages):,} package components."
    )
    print(f"Wrote results to {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
