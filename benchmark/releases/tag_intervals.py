"""Stage 1 of the tag-level study: the release tags that lie on the walked default branch.

The commit-level walk visits the first-parent history of each library's default branch, ending at
its HEAD. A *tag-level walk of the same branch* is therefore just the subsequence of those commits
that carry a release tag, diffed consecutively. Holding the branch, the source roots, the exclusion
rules and the extractor fixed leaves exactly one variable between the two walks: granularity.

Writes tag-intervals.csv (one row per pair of consecutive tagged commits) and tag-inputs.csv (the
PairDiffer input), and exports the tagged commits' source trees.
"""
import argparse
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import yaml

from prepare_pairs import DATA, SRC, WALK_DATA, WALK_YAML, export_sources, relocate

# A tag names a version once a non-digit prefix ("v", "rel/commons-io-", "r") is stripped: what is
# left has to start with a digit and look like a dotted number.
VERSION = re.compile(r'^\d[\d._-]*')
LEADING = re.compile(r'^\D*')
PRERELEASE = re.compile(
    r'(?i)(^|[-._])(alpha|beta|rc|cr|m\d|milestone|snapshot|preview|ea|dev|pre|b\d+|incubat\w*|'
    r'candidate|nightly)([-._0-9]|$)')


def tag_version(name):
    """The version a tag names, or None if the tag does not name one."""
    version = LEADING.sub('', name.rsplit('/', 1)[-1])
    return version if VERSION.match(version) else None


def is_stable(version):
    return PRERELEASE.search(version) is None


def tagged_commits(gitdir, walk_shas, include_prereleases):
    """Walked commit index -> the version tags on it, oldest walked commit first."""
    position = {sha: i for i, sha in enumerate(walk_shas)}
    out = subprocess.run(
        ['git', '--git-dir', gitdir, 'for-each-ref',
         '--format=%(refname:short)\t%(objectname)\t%(*objectname)', 'refs/tags'],
        capture_output=True, text=True, check=True).stdout

    by_index = {}
    for line in out.splitlines():
        name, obj, peeled = line.split('\t')
        index = position.get(peeled or obj)
        if index is None:
            continue
        version = tag_version(name)
        if version is None or (not include_prereleases and not is_stable(version)):
            continue
        by_index.setdefault(index, []).append((name, version))
    return dict(sorted(by_index.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--include-prereleases', action='store_true',
                    help='also step through alpha/beta/RC/milestone tags')
    ap.add_argument('--prefix', default='tag',
                    help='basename of the generated files (default: tag)')
    args = ap.parse_args()

    repos = {r['libraryId']: r for r in yaml.safe_load(open(WALK_YAML))['repositories']}
    rows, jobs, coverage = [], set(), []

    for lib in sorted(repos):
        repo = repos[lib]
        gitdir = relocate(repo['gitDir'])
        roots = tuple(os.path.relpath(relocate(p), os.path.dirname(gitdir))
                      for p in repo['sourceRoots'])

        with open(os.path.join(WALK_DATA, f'{lib}-commits.csv')) as f:
            walk = [(r['commit_sha'], r['date_utc']) for r in csv.DictReader(f)]
        shas = [s for s, _ in walk]

        tagged = tagged_commits(gitdir, shas, args.include_prereleases)
        steps = list(tagged.items())
        for (i, v1_tags), (j, v2_tags) in zip(steps, steps[1:]):
            rows.append({
                'library': lib,
                # Several tags can sit on one commit (an RC re-tagged as the release); the first
                # one names the step, the rest are kept for traceability.
                'pair_id': f'{v1_tags[0][1]}__{v2_tags[0][1]}',
                'v1_version': v1_tags[0][1], 'v2_version': v2_tags[0][1],
                'v1_tags': ';'.join(n for n, _ in v1_tags),
                'v2_tags': ';'.join(n for n, _ in v2_tags),
                'v1_sha': shas[i], 'v2_sha': shas[j],
                'v1_index': i, 'v2_index': j,
                'v1_date_utc': walk[i][1], 'v2_date_utc': walk[j][1],
                'commits_in_interval': j - i,
            })
            jobs.add((lib, gitdir, roots, shas[i]))
            jobs.add((lib, gitdir, roots, shas[j]))

        all_tags = subprocess.run(
            ['git', '--git-dir', gitdir, 'for-each-ref', '--format=%(refname:short)', 'refs/tags'],
            capture_output=True, text=True, check=True).stdout.split()
        coverage.append({
            'library': lib, 'walked_commits': len(shas), 'tags_in_repo': len(all_tags),
            'version_tags_in_repo': sum(1 for t in all_tags if tag_version(t)),
            'tagged_walked_commits': len(tagged), 'intervals': max(0, len(steps) - 1),
        })
        print(f'{lib:22}{len(tagged):>5} tagged commits{len(steps) - 1 if steps else 0:>6} intervals',
              file=sys.stderr)

    os.makedirs(DATA, exist_ok=True)
    intervals_csv = os.path.join(DATA, f'{args.prefix}-intervals.csv')
    with open(intervals_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} intervals -> {intervals_csv}', file=sys.stderr)

    coverage_csv = os.path.join(DATA, f'{args.prefix}-coverage.csv')
    with open(coverage_csv, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(coverage[0].keys()))
        w.writeheader()
        w.writerows(coverage)

    print(f'exporting {len(jobs)} tagged commits', file=sys.stderr)
    exported = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for lib, sha, path in pool.map(export_sources, sorted(jobs)):
            exported[(lib, sha)] = path

    inputs_csv = os.path.join(DATA, f'{args.prefix}-inputs.csv')
    with open(inputs_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['library', 'pair_id', 'v1_label', 'v1_location', 'v2_label', 'v2_location'])
        kept = 0
        for r in rows:
            v1 = exported.get((r['library'], r['v1_sha']), '')
            v2 = exported.get((r['library'], r['v2_sha']), '')
            if v1 and v2:
                w.writerow([r['library'], r['pair_id'], r['v1_version'], v1,
                            r['v2_version'], v2])
                kept += 1
    print(f'{kept} rows -> {inputs_csv}', file=sys.stderr)


if __name__ == '__main__':
    main()
