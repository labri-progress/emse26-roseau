"""Stage 3: materialise the two sides of each release interval and emit PairDiffer inputs.

For every interval on a library's mainline release chain we need:
  * the two released JARs, downloaded from Maven Central  -> jar-pairs.csv
  * the two source trees at the anchor commits, exported from the clone -> source-pairs.csv

The source side is what isolates the effect of *granularity* (one cumulative diff over the
interval vs. the sum of the walk's per-commit diffs) from the effect of *modality* (Roseau on
bytecode vs. on sources) and of *what was actually shipped*.
"""
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml

def _repo_root():
    """The replication package root, two levels above benchmark/releases/."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


REPO = os.environ.get('REPO_ROOT', _repo_root())
WALK_DATA = os.path.join(REPO, 'results/longitudinal/walk/notebooks/data')
WALK_YAML = os.path.join(REPO, 'benchmark/walk/walk.yaml')
DATA = os.environ.get('RELEASE_DATA', os.path.join(REPO, 'results/releases/data'))
# Scratch space for the downloaded JARs and the exported source trees (a few GB).
WORK = os.environ.get('WORK', '/data/release-study')
# walk.yaml records the clone paths as they were on the run machine; CLONES relocates them.
CLONES = os.environ.get('CLONES', '/data')
JARS = os.path.join(WORK, 'jars')
SRC = os.path.join(WORK, 'src')
BASE = 'https://repo1.maven.org/maven2'
UA = 'roseau-release-study/1.0 (research)'


def relocate(path):
    """Rewrite a walk.yaml clone path onto this machine's clone directory."""
    return re.sub(r'^/data(/new)?/', CLONES.rstrip('/') + '/', path)


def jar_path(g, a, v):
    return os.path.join(JARS, g, a, f'{a}-{v}.jar')


def download(gav):
    g, a, v = gav
    dest = jar_path(g, a, v)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return gav, True, 'cached'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = f'{BASE}/{g.replace(".", "/")}/{a}/{v}/{a}-{v}.jar'
    p = subprocess.run(['curl', '-sSfL', '--max-time', '300', '-A', UA, '-o', dest, url],
                       capture_output=True, text=True)
    if p.returncode != 0 or os.path.getsize(dest) == 0:
        if os.path.exists(dest):
            os.remove(dest)
        return gav, False, p.stderr.strip()[:120] or 'empty'
    return gav, True, 'downloaded'


def git(gitdir, *args, check=True):
    p = subprocess.run(['git', '--git-dir', gitdir, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f'git {args}: {p.stderr.strip()}')
    return p


def export_sources(job):
    """Export the first source root that exists at this commit, like GitWalker picks it."""
    lib, gitdir, roots, sha = job
    dest = os.path.join(SRC, lib, sha)
    marker = os.path.join(dest, '.exported')
    if os.path.exists(marker):
        return lib, sha, open(marker).read().strip()
    for root in roots:
        if not git(gitdir, 'ls-tree', '-d', '--name-only', sha, '--', root,
                   check=False).stdout.strip():
            continue
        out = os.path.join(dest, root)
        os.makedirs(dest, exist_ok=True)
        tar = subprocess.Popen(['git', '--git-dir', gitdir, 'archive', sha, '--', root],
                               stdout=subprocess.PIPE)
        subprocess.run(['tar', '-x', '-C', dest], stdin=tar.stdout, check=True)
        tar.wait()
        with open(marker, 'w') as f:
            f.write(out)
        return lib, sha, out
    os.makedirs(dest, exist_ok=True)
    with open(marker, 'w') as f:
        f.write('')
    return lib, sha, ''


def main():
    cfg = yaml.safe_load(open(WALK_YAML))
    repos = {}
    for r in cfg['repositories']:
        gitdir = relocate(r['gitDir'])
        repo_root = os.path.dirname(gitdir)
        roots = [os.path.relpath(relocate(p), repo_root) for p in r['sourceRoots']]
        repos[r['libraryId']] = (gitdir, roots)

    intervals = list(csv.DictReader(open(os.path.join(DATA, 'intervals.csv'))))
    print(f'{len(intervals)} intervals', file=sys.stderr)

    # --- JARs -------------------------------------------------------------------------------
    gavs = set()
    for r in intervals:
        gavs.add((r['v1_group_id'], r['v1_artifact_id'], r['v1_version']))
        gavs.add((r['v2_group_id'], r['v2_artifact_id'], r['v2_version']))
    print(f'{len(gavs)} distinct artefacts to fetch', file=sys.stderr)

    available, failures = set(), []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, (gav, ok, note) in enumerate(pool.map(download, sorted(gavs)), 1):
            if ok:
                available.add(gav)
            else:
                failures.append((gav, note))
            if i % 200 == 0:
                print(f'  {i}/{len(gavs)} artefacts', file=sys.stderr)
    print(f'{len(available)} JARs available, {len(failures)} missing', file=sys.stderr)
    for gav, note in failures[:20]:
        print(f'  missing {":".join(gav)} ({note})', file=sys.stderr)

    # --- sources ----------------------------------------------------------------------------
    jobs = set()
    for r in intervals:
        gitdir, roots = repos[r['library']]
        jobs.add((r['library'], gitdir, tuple(roots), r['v1_anchor_sha']))
        jobs.add((r['library'], gitdir, tuple(roots), r['v2_anchor_sha']))
    print(f'{len(jobs)} distinct anchor commits to export', file=sys.stderr)

    exported = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for i, (lib, sha, path) in enumerate(pool.map(export_sources, sorted(jobs)), 1):
            exported[(lib, sha)] = path
            if i % 200 == 0:
                print(f'  {i}/{len(jobs)} commits', file=sys.stderr)
    missing_src = sum(1 for v in exported.values() if not v)
    print(f'{len(exported) - missing_src} source trees exported, {missing_src} empty',
          file=sys.stderr)

    # --- pair files -------------------------------------------------------------------------
    header = ['library', 'pair_id', 'v1_label', 'v1_location', 'v2_label', 'v2_location']
    jar_rows, src_rows = [], []
    for r in intervals:
        g1, a1, v1 = r['v1_group_id'], r['v1_artifact_id'], r['v1_version']
        g2, a2, v2 = r['v2_group_id'], r['v2_artifact_id'], r['v2_version']
        if (g1, a1, v1) in available and (g2, a2, v2) in available:
            jar_rows.append([r['library'], r['pair_id'], v1, jar_path(g1, a1, v1),
                             v2, jar_path(g2, a2, v2)])
        s1 = exported.get((r['library'], r['v1_anchor_sha']), '')
        s2 = exported.get((r['library'], r['v2_anchor_sha']), '')
        if s1 and s2:
            src_rows.append([r['library'], r['pair_id'], r['v1_anchor_sha'], s1,
                             r['v2_anchor_sha'], s2])

    for name, rows in (('jar-inputs.csv', jar_rows), ('source-inputs.csv', src_rows)):
        with open(os.path.join(DATA, name), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f'{len(rows)} rows -> {name}', file=sys.stderr)


if __name__ == '__main__':
    main()
