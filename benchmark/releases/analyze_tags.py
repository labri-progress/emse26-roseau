"""Stage 3 of the tag-level study: commit-level vs. tag-level walk of the same branch.

Two views of every interval between consecutive release tags on the default branch:

  C  the commit-level walk's breaking changes, summed over the commits in the interval
  T  one Roseau diff between the two tagged commits

Same branch, same source roots, same exclusion rules, same extractor, same Roseau build: the only
thing that differs is the step size. C∖T is churn that the project undid before tagging; T∖C is a
breaking change that no single commit pair produced.

Writes tag-comparison.csv, tag-comparison-fate-by-kind.csv and tag-comparison-unattributed.csv.
"""
import argparse
import collections
import csv
import os
import statistics
import sys

from prepare_pairs import DATA, WALK_DATA

csv.field_size_limit(10 ** 8)


def strip_generics(s):
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


def load_tag_bcs(path, public_only, erased):
    by_pair = collections.defaultdict(set)
    details = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            if public_only and row['is_excluded_symbol'] == 'true':
                continue
            k = key(row['kind'], row['impacted_symbol_fqn'], erased)
            by_pair[(row['library'], row['pair_id'])].add(k)
            details[k] = row['impacted_package_fqn']
    return by_pair, details


def load_errors(path):
    with open(path) as f:
        return {(r['library'], r['pair_id']): r['error'] for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prefix', default='tag')
    ap.add_argument('--erased', action='store_true',
                    help='match breaking changes on generics-erased signatures')
    ap.add_argument('--all-symbols', action='store_true',
                    help='include breaking changes on symbols excluded from the public API')
    args = ap.parse_args()
    public_only = not args.all_symbols
    p = args.prefix

    intervals = list(csv.DictReader(open(os.path.join(DATA, f'{p}-intervals.csv'))))
    tag_bcs, packages = load_tag_bcs(os.path.join(DATA, f'{p}-bcs.csv'), public_only, args.erased)
    errors = load_errors(os.path.join(DATA, f'{p}-pairs.csv'))

    rows = []
    fate = collections.Counter()
    unattributed = collections.Counter()
    for lib in sorted({r['library'] for r in intervals}):
        index, by_commit = {}, collections.defaultdict(set)
        with open(os.path.join(WALK_DATA, f'{lib}-commits.csv')) as f:
            for i, row in enumerate(csv.DictReader(f)):
                index[row['commit_sha']] = i
        with open(os.path.join(WALK_DATA, f'{lib}-bcs.csv')) as f:
            for row in csv.DictReader(f):
                if public_only and row['is_excluded_symbol'] == 'true':
                    continue
                i = index.get(row['commit'])
                if i is not None:
                    by_commit[i].add(key(row['kind'], row['impacted_symbol_fqn'], args.erased))

        events = collections.Counter()
        with open(os.path.join(WALK_DATA, f'{lib}-bcs.csv')) as f:
            for row in csv.DictReader(f):
                if public_only and row['is_excluded_symbol'] == 'true':
                    continue
                i = index.get(row['commit'])
                if i is not None:
                    events[i] += 1

        for r in (x for x in intervals if x['library'] == lib):
            i, j = int(r['v1_index']), int(r['v2_index'])
            pair = (lib, r['pair_id'])
            ok = pair in errors and not errors[pair]

            c_keys = set()
            for k in range(i + 1, j + 1):
                c_keys |= by_commit[k]
            t_keys = tag_bcs.get(pair, set()) if ok else set()

            if ok:
                for k in c_keys:
                    fate[(k[0], 'kept_at_tag' if k in t_keys else 'undone_before_tag')] += 1
                for k in t_keys - c_keys:
                    unattributed[(lib, k[0], packages.get(k, ''))] += 1

            rows.append({
                'library': lib, 'pair_id': r['pair_id'],
                'v1_version': r['v1_version'], 'v2_version': r['v2_version'],
                'commits_in_interval': j - i,
                'commits_with_bcs': sum(1 for k in range(i + 1, j + 1) if by_commit[k]),
                'has_tag_diff': ok,
                'commit_events': sum(events[k] for k in range(i + 1, j + 1)),
                'commit_keys': len(c_keys),
                'tag_keys': len(t_keys),
                'commit_and_tag': len(c_keys & t_keys),
                'commit_only': len(c_keys - t_keys),
                'tag_only': len(t_keys - c_keys),
            })

    out = os.path.join(DATA, f'{p}-comparison.csv')
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} intervals -> {out}', file=sys.stderr)

    with open(os.path.join(DATA, f'{p}-comparison-fate-by-kind.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['kind', 'kept_at_tag', 'undone_before_tag'])
        for k in sorted({k for k, _ in fate}):
            w.writerow([k, fate[(k, 'kept_at_tag')], fate[(k, 'undone_before_tag')]])

    with open(os.path.join(DATA, f'{p}-comparison-unattributed.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['library', 'kind', 'impacted_package_fqn', 'tag_bcs_not_in_any_commit'])
        for (lib, kind, pkg), n in sorted(unattributed.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([lib, kind, pkg, n])

    report([r for r in rows if r['has_tag_diff']], fate, unattributed)


def pct(a, b):
    return f'{100 * a / b:5.1f}%' if b else '     -'


def report(usable, fate, unattributed):
    hdr = (f"{'library':22}{'iv':>5}{'commits':>9}{'C evt':>8}{'C key':>8}{'T key':>8}"
           f"{'evt/T':>7}{'C∩T/C':>8}{'C∩T/T':>8}")
    print(f'\n{len(usable)} intervals with a tag-level diff\n')
    print(hdr)
    print('-' * len(hdr))

    def line(name, rs):
        c_evt = sum(r['commit_events'] for r in rs)
        c = sum(r['commit_keys'] for r in rs)
        t = sum(r['tag_keys'] for r in rs)
        ct = sum(r['commit_and_tag'] for r in rs)
        ratio = f'{c_evt / t:.2f}' if t else '   -'
        print(f'{name:22}{len(rs):>5}{sum(r["commits_in_interval"] for r in rs):>9}'
              f'{c_evt:>8}{c:>8}{t:>8}{ratio:>7}{pct(ct, c):>8}{pct(ct, t):>8}')

    libs = sorted({r['library'] for r in usable})
    for lib in libs:
        line(lib, [r for r in usable if r['library'] == lib])
    print('-' * len(hdr))
    line('ALL (pooled)', usable)

    # mockito-core alone contributes a third of the intervals, so the pooled figures are also
    # reported as a median over libraries.
    surv, cov, rat = [], [], []
    for lib in libs:
        rs = [r for r in usable if r['library'] == lib]
        c = sum(r['commit_keys'] for r in rs)
        t = sum(r['tag_keys'] for r in rs)
        ct = sum(r['commit_and_tag'] for r in rs)
        if c:
            surv.append(ct / c)
        if t:
            cov.append(ct / t)
            rat.append(sum(r['commit_events'] for r in rs) / t)
    print(f'\nMedian over the {len(libs)} libraries: '
          f'events/T {statistics.median(rat):.2f} · survival {statistics.median(surv):.1%} · '
          f'coverage {statistics.median(cov):.1%}')

    per_s = [r['commit_and_tag'] / r['commit_keys'] for r in usable if r['commit_keys']]
    per_c = [r['commit_and_tag'] / r['tag_keys'] for r in usable if r['tag_keys']]
    print(f'Median over the {len(usable)} intervals: '
          f'survival {statistics.median(per_s):.1%} · coverage {statistics.median(per_c):.1%}')

    with_t = sum(1 for r in usable if r['tag_keys'])
    with_c = sum(1 for r in usable if r['commit_keys'])
    only_c = sum(1 for r in usable if r['commit_keys'] and not r['tag_keys'])
    print(f'\nIntervals breaking something at tag level: {with_t}/{len(usable)} ({pct(with_t, len(usable))})')
    print(f'Intervals with commit-level BCs:           {with_c}/{len(usable)} ({pct(with_c, len(usable))})')
    print(f'  ... of which nothing survives to the tag: {only_c}')

    kept = sum(v for (_, s), v in fate.items() if s == 'kept_at_tag')
    undone = sum(v for (_, s), v in fate.items() if s == 'undone_before_tag')
    print(f'\nDistinct commit-level BCs: {kept + undone} '
          f'({pct(kept, kept + undone)} kept at the next tag, {pct(undone, kept + undone)} undone)')
    print(f'Tag-level BCs not attributable to any single commit: {sum(unattributed.values())}')

    print('\nSurvival by kind (top 12 by volume)')
    kinds = sorted({k for k, _ in fate},
                   key=lambda k: -(fate[(k, 'kept_at_tag')] + fate[(k, 'undone_before_tag')]))
    print(f"{'kind':48}{'total':>8}{'kept':>8}{'kept %':>9}")
    for k in kinds[:12]:
        a, b = fate[(k, 'kept_at_tag')], fate[(k, 'undone_before_tag')]
        print(f'{k:48}{a + b:>8}{a:>8}{pct(a, a + b):>9}')


if __name__ == '__main__':
    main()
