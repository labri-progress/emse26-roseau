"""Stage 5: compare what the walk sees commit by commit with what is observable between releases.

Three views of the same interval between two consecutive mainline releases:

  C  the walk's per-commit breaking changes, summed over the commits in the interval
     (source, incremental)
  S  one cumulative Roseau diff between the two anchor commits (source)
  R  one cumulative Roseau diff between the two released JARs (bytecode)

C vs S isolates the effect of *granularity*; S vs R isolates *modality plus what was shipped*.
Breaking changes are identified by (kind, impacted symbol); a generics-erased key is reported
alongside as a robustness check, since source and bytecode print type arguments differently.
"""
import argparse
import collections
import csv
import os
import statistics
import sys


def _repo_root():
    """The replication package root, two levels above benchmark/releases/."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


REPO = os.environ.get('REPO_ROOT', _repo_root())
WALK_DATA = os.path.join(REPO, 'results/longitudinal/walk/notebooks/data')
WALK_YAML = os.path.join(REPO, 'benchmark/walk/walk.yaml')
DATA = os.environ.get('RELEASE_DATA', os.path.join(REPO, 'results/releases/data'))

csv.field_size_limit(10 ** 8)


def strip_generics(s):
    """Drop type arguments so that a source-printed and a bytecode-printed signature agree."""
    out, depth = [], 0
    for ch in s:
        if ch == '<':
            depth += 1
        elif ch == '>':
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return ''.join(out)


def key(kind, fqn, erased):
    return kind, strip_generics(fqn) if erased else fqn


def load_walk_index(lib):
    index = {}
    with open(os.path.join(WALK_DATA, f'{lib}-commits.csv')) as f:
        for i, row in enumerate(csv.DictReader(f)):
            index[row['commit_sha']] = i
    return index


def load_walk_bcs(lib, index, public_only):
    """Commit index -> list of (kind, impacted_symbol_fqn)."""
    by_commit = collections.defaultdict(list)
    with open(os.path.join(WALK_DATA, f'{lib}-bcs.csv')) as f:
        for row in csv.DictReader(f):
            if public_only and row['is_excluded_symbol'] == 'true':
                continue
            i = index.get(row['commit'])
            if i is not None:
                by_commit[i].append((row['kind'], row['impacted_symbol_fqn']))
    return by_commit


def load_pair_bcs(path, public_only):
    """(library, pair_id) -> list of (kind, impacted_symbol_fqn)."""
    by_pair = collections.defaultdict(list)
    if not os.path.exists(path):
        return by_pair
    with open(path) as f:
        for row in csv.DictReader(f):
            if public_only and row['is_excluded_symbol'] == 'true':
                continue
            by_pair[(row['library'], row['pair_id'])].append(
                (row['kind'], row['impacted_symbol_fqn']))
    return by_pair


def load_packages(path, erased):
    """Breaking-change key -> the package it impacts, for the residual breakdown."""
    packages = {}
    if not os.path.exists(path):
        return packages
    with open(path) as f:
        for row in csv.DictReader(f):
            packages[key(row['kind'], row['impacted_symbol_fqn'], erased)] = \
                row['impacted_package_fqn']
    return packages


def load_pair_status(path):
    status = {}
    if not os.path.exists(path):
        return status
    with open(path) as f:
        for row in csv.DictReader(f):
            status[(row['library'], row['pair_id'])] = row['error']
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='comparison.csv')
    ap.add_argument('--erased', action='store_true',
                    help='match breaking changes on generics-erased signatures')
    ap.add_argument('--all-symbols', action='store_true',
                    help='include breaking changes on symbols excluded from the public API')
    ap.add_argument('--tagged-only', action='store_true',
                    help='keep only intervals whose two endpoints were located by a Git tag')
    args = ap.parse_args()
    public_only = not args.all_symbols

    intervals = list(csv.DictReader(open(os.path.join(DATA, 'intervals.csv'))))
    if args.tagged_only:
        intervals = [r for r in intervals if r['tag_anchored'] == 'True']
    jar_bcs = load_pair_bcs(os.path.join(DATA, 'jar-bcs.csv'), public_only)
    jar_packages = load_packages(os.path.join(DATA, 'jar-bcs.csv'), args.erased)
    src_bcs = load_pair_bcs(os.path.join(DATA, 'source-bcs.csv'), public_only)
    jar_ok = load_pair_status(os.path.join(DATA, 'jar-pairs.csv'))
    src_ok = load_pair_status(os.path.join(DATA, 'source-pairs.csv'))

    rows = []
    fate = collections.Counter()      # kind -> how each commit-level BC ends up
    kind_release = collections.Counter()
    residual = collections.Counter()  # (library, package) -> released BCs in neither C nor S
    for lib in sorted({r['library'] for r in intervals}):
        index = load_walk_index(lib)
        by_commit = load_walk_bcs(lib, index, public_only)
        for r in (x for x in intervals if x['library'] == lib):
            i, j = int(r['v1_anchor_index']), int(r['v2_anchor_index'])
            pair = (lib, r['pair_id'])

            commit_events = [bc for k in range(i + 1, j + 1) for bc in by_commit.get(k, [])]
            c_keys = {key(k, f, args.erased) for k, f in commit_events}
            s_keys = {key(k, f, args.erased) for k, f in src_bcs.get(pair, [])}
            r_keys = {key(k, f, args.erased) for k, f in jar_bcs.get(pair, [])}

            if (pair in jar_ok and not jar_ok[pair]) and (pair in src_ok and not src_ok[pair]):
                for k in c_keys:
                    if k in r_keys:
                        fate[(k[0], 'released')] += 1
                    elif k in s_keys:
                        fate[(k[0], 'in_source_not_in_jar')] += 1
                    else:
                        fate[(k[0], 'cancelled_before_release')] += 1
                for k in r_keys:
                    if k in c_keys:
                        kind_release[(k[0], 'seen_at_commit_level')] += 1
                    elif k in s_keys:
                        kind_release[(k[0], 'in_source_diff_only')] += 1
                    else:
                        kind_release[(k[0], 'unseen')] += 1
                        residual[(lib, jar_packages.get(k, ''))] += 1

            rows.append({
                'library': lib, 'pair_id': r['pair_id'],
                'v1_version': r['v1_version'], 'v2_version': r['v2_version'],
                'v1_anchor_method': r['v1_anchor_method'], 'v2_anchor_method': r['v2_anchor_method'],
                'tag_anchored': r['tag_anchored'],
                'commits_in_interval': j - i,
                'commits_with_bcs': sum(1 for k in range(i + 1, j + 1) if by_commit.get(k)),
                'has_jar_diff': pair in jar_ok and not jar_ok[pair],
                'has_source_diff': pair in src_ok and not src_ok[pair],
                'commit_events': len(commit_events),
                'commit_keys': len(c_keys),
                'source_keys': len(s_keys),
                'release_keys': len(r_keys),
                'commit_and_release': len(c_keys & r_keys),
                'commit_and_source': len(c_keys & s_keys),
                'source_and_release': len(s_keys & r_keys),
                'release_only': len(r_keys - c_keys),
                'commit_only': len(c_keys - r_keys),
            })

    with open(os.path.join(DATA, args.out), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} intervals -> {args.out}', file=sys.stderr)
    write_fate(fate, os.path.join(DATA, args.out.replace('.csv', '-fate-by-kind.csv')))
    write_residual(residual, os.path.join(DATA, args.out.replace('.csv', '-residual.csv')))
    report(rows)
    report_kinds(fate, kind_release)


def write_fate(fate, path):
    kinds = sorted({k for k, _ in fate})
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['kind', 'released', 'in_source_not_in_jar', 'cancelled_before_release'])
        for k in kinds:
            w.writerow([k, fate[(k, 'released')], fate[(k, 'in_source_not_in_jar')],
                        fate[(k, 'cancelled_before_release')]])
    print(f'{len(kinds)} kinds -> {path}', file=sys.stderr)


def write_residual(residual, path):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['library', 'impacted_package_fqn', 'released_bcs_in_neither'])
        for (lib, pkg), n in sorted(residual.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([lib, pkg, n])
    print(f'{len(residual)} (library, package) rows -> {path}', file=sys.stderr)


def report_kinds(fate, kind_release):
    print('\nFate of each distinct commit-level breaking change, by kind')
    hdr = f"{'kind':46}{'total':>8}{'released':>10}{'src only':>10}{'cancelled':>11}{'rel %':>8}"
    print(hdr)
    print('-' * len(hdr))
    kinds = sorted({k for k, _ in fate}, key=lambda k: -sum(fate[(k, s)] for s in
                   ('released', 'in_source_not_in_jar', 'cancelled_before_release')))
    for k in kinds[:20]:
        rel = fate[(k, 'released')]
        src = fate[(k, 'in_source_not_in_jar')]
        can = fate[(k, 'cancelled_before_release')]
        tot = rel + src + can
        print(f'{k:46}{tot:>8}{rel:>10}{src:>10}{can:>11}{pct(rel, tot):>8}')
    rel = sum(v for (_, s), v in fate.items() if s == 'released')
    src = sum(v for (_, s), v in fate.items() if s == 'in_source_not_in_jar')
    can = sum(v for (_, s), v in fate.items() if s == 'cancelled_before_release')
    print('-' * len(hdr))
    print(f'{"ALL":46}{rel + src + can:>8}{rel:>10}{src:>10}{can:>11}{pct(rel, rel + src + can):>8}')

    seen = sum(v for (_, s), v in kind_release.items() if s == 'seen_at_commit_level')
    srco = sum(v for (_, s), v in kind_release.items() if s == 'in_source_diff_only')
    unseen = sum(v for (_, s), v in kind_release.items() if s == 'unseen')
    total = seen + srco + unseen
    print(f'\nProvenance of released breaking changes: {total} total')
    print(f'  attributable to a single walked commit          {seen:>7} ({pct(seen, total)})')
    print(f'  only in the cumulative source diff              {srco:>7} ({pct(srco, total)})')
    print(f'  in neither (bytecode-only / off-mainline)       {unseen:>7} ({pct(unseen, total)})')


def ratio(a, b):
    return f'{a / b:.2f}' if b else '   -'


def pct(a, b):
    return f'{100 * a / b:5.1f}%' if b else '     -'


def report(rows):
    usable = [r for r in rows if r['has_jar_diff'] and r['has_source_diff']]
    print(f'\n{len(usable)}/{len(rows)} intervals have both a JAR diff and a source diff\n')

    hdr = (f"{'library':22}{'iv':>5}{'commits':>9}{'C evt':>8}{'C key':>8}{'S key':>8}"
           f"{'R key':>8}{'C/R':>7}{'C∩R/C':>8}{'C∩R/R':>8}{'S∩R/R':>8}")
    print(hdr)
    print('-' * len(hdr))

    def line(name, rs):
        c_evt = sum(r['commit_events'] for r in rs)
        c_key = sum(r['commit_keys'] for r in rs)
        s_key = sum(r['source_keys'] for r in rs)
        r_key = sum(r['release_keys'] for r in rs)
        cr = sum(r['commit_and_release'] for r in rs)
        sr = sum(r['source_and_release'] for r in rs)
        print(f'{name:22}{len(rs):>5}{sum(r["commits_in_interval"] for r in rs):>9}'
              f'{c_evt:>8}{c_key:>8}{s_key:>8}{r_key:>8}'
              f'{ratio(c_evt, r_key):>7}{pct(cr, c_key):>8}{pct(cr, r_key):>8}{pct(sr, r_key):>8}')

    for lib in sorted({r['library'] for r in usable}):
        line(lib, [r for r in usable if r['library'] == lib])
    print('-' * len(hdr))
    line('ALL', usable)

    with_release_bcs = [r for r in usable if r['release_keys'] > 0]
    with_commit_bcs = [r for r in usable if r['commit_keys'] > 0]
    print(f'\nIntervals with >=1 released BC:        {len(with_release_bcs)}/{len(usable)} '
          f'({100 * len(with_release_bcs) / len(usable):.1f}%)')
    print(f'Intervals with >=1 commit-level BC:    {len(with_commit_bcs)}/{len(usable)} '
          f'({100 * len(with_commit_bcs) / len(usable):.1f}%)')
    both = [r for r in usable if r['release_keys'] > 0 and r['commit_keys'] > 0]
    print(f'Intervals with both:                   {len(both)}/{len(usable)}')
    only_commit = [r for r in usable if r['release_keys'] == 0 and r['commit_keys'] > 0]
    print(f'Commit-level BCs but nothing released: {len(only_commit)}/{len(usable)}')

    per = [r['commit_keys'] / r['release_keys'] for r in usable if r['release_keys'] > 0]
    if per:
        print(f'\nPer-interval commit_keys/release_keys: median {statistics.median(per):.2f}, '
              f'mean {statistics.mean(per):.2f}')
    surv = [r['commit_and_release'] / r['commit_keys'] for r in usable if r['commit_keys'] > 0]
    if surv:
        print(f'Per-interval survival C∩R/C:           median {statistics.median(surv):.2f}, '
              f'mean {statistics.mean(surv):.2f}')


if __name__ == '__main__':
    main()
