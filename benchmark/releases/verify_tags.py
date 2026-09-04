"""Self-checks for the tag-level study. Exits non-zero if any check fails.

    uv run python verify_tags.py [--prefix tag]
"""
import argparse
import collections
import csv
import os
import subprocess
import sys

import yaml

from prepare_pairs import DATA, WALK_DATA, WALK_YAML, relocate
from tag_intervals import tag_version

csv.field_size_limit(10 ** 8)

failures = []


def check(name, ok, detail=''):
    print(f'{"PASS" if ok else "FAIL"}  {name}{"  " + detail if detail else ""}')
    if not ok:
        failures.append(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='tag')
    args = ap.parse_args()
    p = args.prefix

    intervals = list(csv.DictReader(open(os.path.join(DATA, f'{p}-intervals.csv'))))
    comparison = {(r['library'], r['pair_id']): r
                  for r in csv.DictReader(open(os.path.join(DATA, f'{p}-comparison.csv')))}
    pairs = list(csv.DictReader(open(os.path.join(DATA, f'{p}-pairs.csv'))))
    repos = {r['libraryId']: r for r in yaml.safe_load(open(WALK_YAML))['repositories']}

    # Every field the two walks should agree on. Exclusion is annotation-driven and therefore
    # version-dependent, so it is only comparable between runs that look at the same commit.
    FIELDS = ('kind', 'nature', 'compatibility', 'impacted_package_fqn', 'impacted_type_fqn',
              'impacted_symbol_fqn', 'symbol_visibility', 'is_excluded_symbol',
              'is_deprecated_removal', 'is_internal_removal', 'matched_exclusion_rule')
    tag_bcs = collections.defaultdict(collections.Counter)
    for r in csv.DictReader(open(os.path.join(DATA, f'{p}-bcs.csv'))):
        tag_bcs[(r['library'], r['pair_id'])][tuple(r[f] for f in FIELDS)] += 1

    # 1. Structural integrity of the interval list.
    check('every interval moves forward along the walk',
          all(int(r['v2_index']) > int(r['v1_index']) for r in intervals))
    keys = [(r['library'], r['pair_id']) for r in intervals]
    check('interval keys are unique', len(keys) == len(set(keys)))
    # An interval is only diffable when a configured source root exists at both of its commits;
    # where it does not, the commit-level walk recorded no API either.
    diffed = {(r['library'], r['pair_id']) for r in pairs}
    rootless = set()
    for lib in {r['library'] for r in intervals}:
        walk = list(csv.DictReader(open(os.path.join(WALK_DATA, f'{lib}-commits.csv'))))
        for r in intervals:
            if r['library'] == lib and not (walk[int(r['v1_index'])]['source_root']
                                            and walk[int(r['v2_index'])]['source_root']):
                rootless.add((lib, r['pair_id']))
    undiffed = {(r['library'], r['pair_id']) for r in intervals} - diffed
    check('every interval with a source root has a diff', undiffed == rootless,
          f'{len(undiffed)} without a diff, {len(rootless)} without a source root')
    check('no diff failed', all(not r['error'] for r in pairs),
          f'{sum(1 for r in pairs if r["error"])} errors')
    check('intervals chain end-to-end within a library', all(
        a['v2_index'] == b['v1_index']
        for lib in {r['library'] for r in intervals}
        for a, b in zip([r for r in intervals if r['library'] == lib],
                        [r for r in intervals if r['library'] == lib][1:])))

    per_lib = collections.defaultdict(list)
    for r in intervals:
        per_lib[r['library']].append(r)

    root_mismatches = tag_mismatches = 0
    exact = exact_equal = 0
    events_mismatch = 0

    for lib, rows in sorted(per_lib.items()):
        walk = list(csv.DictReader(open(os.path.join(WALK_DATA, f'{lib}-commits.csv'))))
        by_index = collections.defaultdict(collections.Counter)
        with open(os.path.join(WALK_DATA, f'{lib}-bcs.csv')) as f:
            index = {c['commit_sha']: i for i, c in enumerate(walk)}
            for r in csv.DictReader(f):
                i = index.get(r['commit'])
                if i is not None:
                    by_index[i][tuple(r[f] for f in FIELDS)] += 1

        # 2. The tags really are the commits the walk visited, at the recorded index.
        gitdir = relocate(repos[lib]['gitDir'])
        roots = [os.path.relpath(relocate(x), os.path.dirname(gitdir))
                 for x in repos[lib]['sourceRoots']]
        for r in rows:
            for side in ('v1', 'v2'):
                i = int(r[f'{side}_index'])
                if walk[i]['commit_sha'] != r[f'{side}_sha']:
                    tag_mismatches += 1
                    continue
                for name in r[f'{side}_tags'].split(';'):
                    peeled = subprocess.run(
                        ['git', '--git-dir', gitdir, 'rev-list', '-n', '1', name],
                        capture_output=True, text=True).stdout.strip()
                    if peeled != r[f'{side}_sha'] or tag_version(name) is None:
                        tag_mismatches += 1
                # 3. The exported tree uses the source root the walk used at that commit.
                walked_root = walk[i]['source_root']
                expected = next((x for x in roots if subprocess.run(
                    ['git', '--git-dir', gitdir, 'ls-tree', '-d', '--name-only',
                     r[f'{side}_sha'], '--', x], capture_output=True, text=True).stdout.strip()),
                    None)
                if walked_root and expected != walked_root:
                    root_mismatches += 1

            # 4. commit_events recomputed here must match the walk's own per-commit counter.
            i, j = int(r['v1_index']), int(r['v2_index'])
            from_counter = sum(int(walk[k]['api_breaking_changes_count']) for k in range(i + 1, j + 1))
            if from_counter != int(comparison[(lib, r['pair_id'])]['commit_events']):
                events_mismatch += 1
            # 5. When two tags sit on consecutive commits, the tag-level walk is diffing exactly
            # the commit pair the commit-level walk diffed: every reported field must match,
            # exclusion decisions included.
            if j == i + 1:
                exact += 1
                if by_index[j] == tag_bcs[(lib, r['pair_id'])]:
                    exact_equal += 1

    check('tags resolve to the recorded walked commit', tag_mismatches == 0,
          f'{tag_mismatches} mismatches')
    check('exported source root matches the walk\'s', root_mismatches == 0,
          f'{root_mismatches} mismatches')
    check('commit_events matches the walk\'s api_breaking_changes_count', events_mismatch == 0,
          f'{events_mismatch} mismatches')
    check('single-commit intervals reproduce every field of the walk', exact_equal == exact,
          f'{exact_equal}/{exact} agree')

    print()
    if failures:
        print(f'{len(failures)} check(s) failed: {", ".join(failures)}')
        sys.exit(1)
    print('all checks passed')


if __name__ == '__main__':
    main()
