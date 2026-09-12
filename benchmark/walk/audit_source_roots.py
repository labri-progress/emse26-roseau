#!/usr/bin/env python3
"""Audit `walk.yaml` source roots across first-parent histories.

Modes: `gaps`, `segments`, `range`, and `impact`.

Usage:
    uv run benchmark/walk/audit_source_roots.py gaps [library ...]
    uv run benchmark/walk/audit_source_roots.py segments [library ...]
    uv run benchmark/walk/audit_source_roots.py range [library ...]
    uv run benchmark/walk/audit_source_roots.py impact <old-walk.yaml>
"""
import collections
import os
import re
import subprocess
import sys

import yaml

WALK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "walk.yaml")
PKG_RE = re.compile(rb"^\s*package\s+([\w.]+)\s*;", re.M)


def first_parent_chain(gitdir, start, end):
    """Return the oldest-first first-parent chain from start through end."""
    shas = subprocess.run(["git", "--git-dir", gitdir, "rev-list", "--first-parent", end],
                          capture_output=True, text=True, check=True).stdout.split()
    if start:
        if start not in shas:
            raise SystemExit(f"startSha {start} is not on the first-parent chain of {end}")
        shas = shas[:shas.index(start) + 1]
    shas.reverse()
    return shas


def stream_name_status(gitdir, end):
    """Yield oldest-first commits and first-parent file changes."""
    proc = subprocess.Popen(
        ["git", "--git-dir", gitdir, "-c", "core.quotePath=false", "log", "--first-parent",
         "--reverse", "--root", "--no-renames", "-z", "--name-status", "--format=%x01%H", end],
        stdout=subprocess.PIPE, text=True, bufsize=1 << 20)
    tokens = proc.stdout.read().split("\0")
    proc.wait()
    sha, entries, i = None, [], 0
    while i < len(tokens):
        token = tokens[i]
        if token.lstrip("\n").startswith("\x01"):
            if sha is not None:
                yield sha, entries
            sha, entries, i = token.lstrip("\n")[1:], [], i + 1
            continue
        if not token:
            i += 1
            continue
        entries.append((token.lstrip("\n")[0], tokens[i + 1] if i + 1 < len(tokens) else ""))
        i += 2
    if sha is not None:
        yield sha, entries


def ancestors(path):
    parts = path.split("/")
    for k in range(1, len(parts)):
        yield "/".join(parts[:k])


def replay(gitdir, end, chain, roots, on_commit):
    """Replay tracked files and invoke on_commit for commits in chain."""
    files, dcount, jcount = set(), collections.Counter(), collections.Counter()
    for sha, entries in stream_name_status(gitdir, end):
        java_changed = False
        for status, path in entries:
            is_java = path.endswith(".java")
            java_changed |= is_java
            if status == "D" and path in files:
                files.discard(path)
                for a in ancestors(path):
                    dcount[a] -= 1
                    if is_java:
                        jcount[a] -= 1
            elif status in ("A", "M", "T") and path not in files:
                files.add(path)
                for a in ancestors(path):
                    dcount[a] += 1
                    if is_java:
                        jcount[a] += 1
        if sha in chain:
            on_commit(sha, java_changed, files, dcount, jcount, resolve(roots, dcount))


def rel_roots(repo):
    """Return worktree-relative source-root groups."""
    worktree = os.path.dirname(repo["gitDir"])
    return [[os.path.relpath(p, worktree) for p in (entry if isinstance(entry, list) else [entry])]
            for entry in repo["sourceRoots"]]


def resolve(groups, dcount):
    """Return existing paths from the first configured group with any."""
    for group in groups:
        existing = [p for p in group if dcount[p] > 0]
        if existing:
            return existing
    return []


def infer_roots(gitdir, sha, java_files, limit=4000):
    """Infer source roots from Java package declarations."""
    selection = sorted(java_files)[:limit]
    if not selection:
        return collections.Counter()
    proc = subprocess.Popen(["git", "--git-dir", gitdir, "cat-file", "--batch"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1 << 20)
    blob, _ = proc.communicate("".join(f"{sha}:{f}\n" for f in selection).encode())
    roots, pos = collections.Counter(), 0
    for path in selection:
        nl = blob.find(b"\n", pos)
        if nl < 0:
            break
        header = blob[pos:nl].split()
        if len(header) < 3 or header[1] != b"blob":
            pos = nl + 1
            continue
        size = int(header[2])
        body, pos = blob[nl + 1:nl + 1 + size], nl + 1 + size + 1
        directory = os.path.dirname(path)
        match = PKG_RE.search(body[:8192])
        if not match:
            roots[directory] += 1  # default package
            continue
        pkgdir = match.group(1).decode().replace(".", "/")
        if directory == pkgdir or directory.endswith("/" + pkgdir):
            roots[directory[:len(directory) - len(pkgdir)].rstrip("/")] += 1
        else:
            roots[f"<package/path mismatch: {directory}>"] += 1
    return roots


def date(gitdir, sha):
    return subprocess.run(["git", "--git-dir", gitdir, "show", "-s", "--format=%cs", sha],
                          capture_output=True, text=True).stdout.strip()


def repositories(config, only):
    for repo in yaml.safe_load(open(config))["repositories"]:
        if not only or repo["libraryId"] in only:
            yield repo


def cmd_gaps(only):
    for repo in repositories(WALK, only):
        gitdir, roots = repo["gitDir"], rel_roots(repo)
        chain = first_parent_chain(gitdir, repo.get("startSha", ""), repo["endSha"])
        order = {sha: i for i, sha in enumerate(chain)}
        groups = {}

        def on_commit(sha, java_changed, files, dcount, jcount, present):
            if present:
                return
            java = {f for f in files if f.endswith(".java")}
            shape = frozenset("/".join(os.path.dirname(f).split("/")[:3]) for f in java)
            group = groups.setdefault(shape, {"shas": [], "sample": None})
            group["shas"].append(sha)
            if group["sample"] is None:
                group["sample"] = (sha, sorted(java))

        replay(gitdir, repo["endSha"], set(chain), roots, on_commit)
        if not groups:
            continue
        print(f"\n{'=' * 100}\n{repo['libraryId']}   configured: {roots}\n{'=' * 100}")
        for group in sorted(groups.values(), key=lambda g: order[g["shas"][0]]):
            shas = sorted(group["shas"], key=order.get)
            sample, java = group["sample"]
            print(f"  {len(shas):5d} commits  {date(gitdir, shas[0])} .. {date(gitdir, shas[-1])}"
                  f"   idx {order[shas[0]]}-{order[shas[-1]]}  sample {sample[:10]}")
            if not java:
                print("         (no .java files anywhere in the tree)")
            for root, n in infer_roots(gitdir, sample, java).most_common(12):
                print(f"         {n:6d}  {root or '<repo root>'}")


def cmd_segments(only):
    for repo in repositories(WALK, only):
        gitdir, roots = repo["gitDir"], rel_roots(repo)
        chain = first_parent_chain(gitdir, repo.get("startSha", ""), repo["endSha"])
        segments = []

        def on_commit(sha, java_changed, files, dcount, jcount, present):
            chosen = ";".join(present) if present else None
            n_java = sum(jcount[p] for p in present)
            if segments and segments[-1][0] == chosen:
                segments[-1][2], segments[-1][3], segments[-1][5] = sha, segments[-1][3] + 1, n_java
            else:
                segments.append([chosen, sha, sha, 1, n_java, n_java])

        replay(gitdir, repo["endSha"], set(chain), roots, on_commit)
        print(f"\n### {repo['libraryId']}  ({len(chain)} commits)  configured={roots}")
        for chosen, first, last, n, java_first, java_last in segments:
            warn = "  <-- ROOT CONTAINS NO JAVA" if chosen and not (java_first and java_last) else ""
            print(f"  {n:6d}  {date(gitdir, first)}..{date(gitdir, last)}  "
                  f"{str(chosen):45s} java {java_first}->{java_last}{warn}")


def cmd_range(only):
    """Report the range where a configured root resolves."""
    print(f"{'library':22s} {'commits':>8s} {'lead gap':>9s} {'trail gap':>10s}  suggested startSha / endSha")
    for repo in repositories(WALK, only):
        gitdir, roots = repo["gitDir"], rel_roots(repo)
        chain = first_parent_chain(gitdir, repo.get("startSha", ""), repo["endSha"])
        index = {sha: i for i, sha in enumerate(chain)}
        resolved = []
        replay(gitdir, repo["endSha"], set(chain), roots,
               lambda sha, jc, f, d, j, present: present and resolved.append(sha))
        if not resolved:
            print(f"{repo['libraryId']:22s} {len(chain):8d}   NO COMMIT RESOLVES A SOURCE ROOT")
            continue
        first, last = min(resolved, key=index.get), max(resolved, key=index.get)
        lead, trail = index[first], len(chain) - 1 - index[last]
        if lead or trail:
            print(f"{repo['libraryId']:22s} {len(chain):8d} {lead:9d} {trail:10d}  "
                  f"start={first} ({date(gitdir, first)})"
                  + (f"  end={last} ({date(gitdir, last)})" if trail else ""))


def cmd_impact(old_config):
    old = {r["libraryId"]: rel_roots(r) for r in repositories(old_config, None)}
    total_old = total_new = total_java = 0
    print(f"{'library':22s} {'gaps old':>9s} {'gaps new':>9s} {'fixed':>7s} {'fixed (java-changing)':>22s}")
    for repo in repositories(WALK, None):
        lib, gitdir = repo["libraryId"], repo["gitDir"]
        roots_new, roots_old = rel_roots(repo), old[lib]
        chain = first_parent_chain(gitdir, repo.get("startSha", ""), repo["endSha"])
        stats = collections.Counter()

        def on_commit(sha, java_changed, files, dcount, jcount, present):
            before = resolve(roots_old, dcount) or None
            after = resolve(roots_new, dcount) or None
            stats["old"] += before is None
            stats["new"] += after is None
            if before is None and after is not None:
                stats["fixed"] += 1
                stats["fixed_java"] += java_changed
            elif before is not None and after is not None and before != after:
                stats["switched"] += 1

        replay(gitdir, repo["endSha"], set(chain), roots_new + roots_old, on_commit)
        total_old, total_new, total_java = (total_old + stats["old"], total_new + stats["new"],
                                            total_java + stats["fixed_java"])
        if stats["old"] != stats["new"] or stats["switched"]:
            extra = f"   (+{stats['switched']} commits switched root)" if stats["switched"] else ""
            print(f"{lib:22s} {stats['old']:9d} {stats['new']:9d} {stats['fixed']:7d} "
                  f"{stats['fixed_java']:22d}{extra}")
    print(f"{'TOTAL':22s} {total_old:9d} {total_new:9d} {total_old - total_new:7d} {total_java:22d}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("gaps", "segments", "range", "impact"):
        raise SystemExit(__doc__)
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "gaps":
        cmd_gaps(set(args))
    elif mode == "segments":
        cmd_segments(set(args))
    elif mode == "range":
        cmd_range(set(args))
    else:
        cmd_impact(args[0])
