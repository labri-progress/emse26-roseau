"""Stage 2: anchor every released version onto the commit history the walk actually visited.

A release-level diff is only comparable with the commit-level walk if we know *which walked
commits* the release interval covers. For each release we therefore look for the commit the
release was cut from, and project it onto the walked (first-parent) history:

  tag_exact     the release's Git tag is itself a walked commit;
  tag_ancestor  the tag lives off the walked line (release branch, merged topic branch), so we
                take the newest walked commit that is an ancestor of the tag;
  timestamp     no tag matches the version, so we take the last walked commit published before
                the artefact appeared on Maven Central;
  unanchored    none of the above (release predates or postdates the walked range).

Writes releases-anchored.csv (one row per release) and intervals.csv (one row per consecutive
release pair whose anchors move forward along the walked history).
"""
import bisect
import csv
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import yaml

from coords import COORDS


def _repo_root():
    """The replication package root, two levels above benchmark/releases/."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


REPO = os.environ.get('REPO_ROOT', _repo_root())
WALK_DATA = os.path.join(REPO, 'results/longitudinal/walk/notebooks/data')
WALK_YAML = os.path.join(REPO, 'benchmark/walk/walk.yaml')
DATA = os.environ.get('RELEASE_DATA', os.path.join(REPO, 'results/releases/data'))
# walk.yaml records the clone paths as they were on the run machine; CLONES relocates them.
CLONES = os.environ.get('CLONES', '/data')


def relocate(path):
    """Rewrite a walk.yaml clone path onto this machine's clone directory."""
    return re.sub(r'^/data(/new)?/', CLONES.rstrip('/') + '/', path)


def git(gitdir, *args, check=True):
    p = subprocess.run(['git', '--git-dir', gitdir, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f'git {args}: {p.stderr.strip()}')
    return p


def parse_iso(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))


def load_walk(lib):
    """The walked commits, oldest first."""
    shas, dates = [], []
    with open(os.path.join(WALK_DATA, f'{lib}-commits.csv')) as f:
        for row in csv.DictReader(f):
            shas.append(row['commit_sha'])
            dates.append(parse_iso(row['date_utc']))
    return shas, dates


def load_tags(gitdir):
    """tag name -> (commit sha, tag date). Annotated tags are peeled to their commit."""
    out = git(gitdir, 'for-each-ref',
              '--format=%(refname:short)\t%(objectname)\t%(*objectname)\t%(creatordate:iso-strict)',
              'refs/tags').stdout
    tags = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        name, obj, peeled, date = line.split('\t')
        tags[name] = (peeled or obj, parse_iso(date))
    return tags


VERSION_START = re.compile(r'^\D*')


def tag_keys(name):
    """Normalised forms of a tag name that could denote a version number."""
    base = name.rsplit('/', 1)[-1]
    stripped = VERSION_START.sub('', base)
    keys = set()
    for candidate in (base, stripped):
        if not candidate:
            continue
        keys.add(candidate)
        keys.add(candidate.replace('_', '.'))
        keys.add(candidate.replace('-', '.'))
        keys.add(candidate.replace('_', '.').replace('-', '.'))
    return {k for k in keys if k and k[0].isdigit()}


def version_keys(version):
    keys = {version, version.replace('_', '.'), version.replace('-', '.')}
    # 31.1-jre and 31.1-android are the same release cut from the same commit
    keys.add(re.sub(r'(?i)-(jre|android)$', '', version))
    return keys


# Some Apache artefacts were published with a date for a version (commons-codec 20041127.091804).
# They order after everything and would truncate the chain, so they are left out of it.
DATE_VERSION = re.compile(r'^\d{4,}')


def version_order(version):
    """A Maven-ish comparison key: digit runs compare numerically, letter runs lexically.

    A leading non-digit prefix is dropped first, so that Guava's r03..r09 keep ordering with the
    9.0, 10.0, ... that follow them.
    """
    return tuple((0, int(t)) if t.isdigit() else (1, t)
                 for t in re.findall(r'\d+|[a-zA-Z]+', VERSION_START.sub('', version) or version))


def index_tags(tags):
    index = {}
    for name, (sha, date) in tags.items():
        for key in tag_keys(name):
            index.setdefault(key, []).append((name, sha, date))
    return index


def newest_walked_ancestor(gitdir, walk_shas, tag_sha):
    """Binary search for the newest walked commit that is an ancestor of tag_sha.

    Valid because the walked commits form a first-parent chain: if w[i] is an ancestor of the tag
    then so is every w[j<i].
    """
    lo, hi, best = 0, len(walk_shas) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        p = git(gitdir, 'merge-base', '--is-ancestor', walk_shas[mid], tag_sha, check=False)
        if p.returncode == 0:
            best = mid
            lo = mid + 1
        elif p.returncode == 1:
            hi = mid - 1
        else:
            return None
    return best


def main():
    cfg = yaml.safe_load(open(WALK_YAML))
    repos = {r['libraryId']: r for r in cfg['repositories']}

    releases = {}
    with open(os.path.join(DATA, 'releases-all.csv')) as f:
        for row in csv.DictReader(f):
            if row['is_stable'] != 'True' or row['flavour'] == 'android':
                continue
            releases.setdefault(row['library'], []).append(row)

    out_rows, interval_rows = [], []
    for lib in sorted(COORDS):
        repo = repos[lib]
        gitdir = relocate(repo['gitDir'])
        walk_shas, walk_dates = load_walk(lib)
        walk_index = {sha: i for i, sha in enumerate(walk_shas)}
        tags = load_tags(gitdir)
        tag_index = index_tags(tags)

        rows = sorted(releases.get(lib, []), key=lambda r: r['published_utc'])
        anchored = []
        for r in rows:
            published = datetime.strptime(r['published_utc'], '%Y-%m-%d %H:%M:%S') \
                .replace(tzinfo=timezone.utc)
            if not (walk_dates[0] <= published <= walk_dates[-1]):
                method, idx, tag_name = 'out_of_range', None, ''
            else:
                candidates = []
                for key in version_keys(r['version']):
                    candidates.extend(tag_index.get(key, []))
                # Several tag schemes may normalise to the same version (joda-time tags its
                # Hibernate and JSP sub-projects with the same numbers). A release is cut before it
                # is published, so prefer tags that predate publication, then the closest one.
                candidates.sort(key=lambda c: ((c[2] - published).days > 1,
                                               abs((c[2] - published).total_seconds())))
                if candidates:
                    tag_name, tag_sha, _ = candidates[0]
                    if tag_sha in walk_index:
                        method, idx = 'tag_exact', walk_index[tag_sha]
                    else:
                        idx = newest_walked_ancestor(gitdir, walk_shas, tag_sha)
                        method = 'tag_ancestor' if idx is not None else 'timestamp'
                        if idx is None:
                            idx = bisect.bisect_right(walk_dates, published) - 1
                else:
                    tag_name = ''
                    method = 'timestamp'
                    idx = bisect.bisect_right(walk_dates, published) - 1
                if idx is not None and idx < 0:
                    method, idx = 'unanchored', None

            anchored.append({
                'library': lib, 'group_id': r['group_id'], 'artifact_id': r['artifact_id'],
                'version': r['version'], 'published_utc': r['published_utc'],
                'anchor_method': method, 'tag': tag_name,
                'anchor_index': '' if idx is None else idx,
                'anchor_sha': '' if idx is None else walk_shas[idx],
                'anchor_date_utc': '' if idx is None else walk_dates[idx].isoformat(),
                'anchor_lag_days': '' if idx is None else
                    round((published - walk_dates[idx]).total_seconds() / 86400, 2),
            })
        out_rows.extend(anchored)

        # The mainline release chain: walking releases in publication order and keeping only those
        # that move forward along the walked history. What this drops are the releases cut from
        # maintenance branches the first-parent walk never visits (Spring's 6.2.x line, Jackson's
        # 2.x line, ...). The surviving chain partitions the walked history into disjoint intervals.
        # The version number must move forward too: several projects publish patch releases of an
        # old line *after* a new major (protobuf ships 3.25.9 long after 4.34.1). Those are cut from
        # a maintenance branch, so anchoring them by timestamp would silently place them on the
        # mainline head and manufacture a spurious "downgrade" interval.
        usable = [a for a in anchored
                  if a['anchor_index'] != '' and not DATE_VERSION.match(a['version'])]
        chain, head, head_version = [], -1, ()
        for a in usable:
            if a['anchor_index'] > head and version_order(a['version']) > head_version:
                chain.append(a)
                head = a['anchor_index']
                head_version = version_order(a['version'])
            else:
                a['in_chain'] = False
        for a in chain:
            a['in_chain'] = True
        for a in anchored:
            a.setdefault('in_chain', False)

        for prev, cur in zip(chain, chain[1:]):
            i, j = prev['anchor_index'], cur['anchor_index']
            interval_rows.append({
                'library': lib,
                'pair_id': f"{prev['version']}__{cur['version']}",
                'v1_version': prev['version'], 'v2_version': cur['version'],
                'v1_group_id': prev['group_id'], 'v1_artifact_id': prev['artifact_id'],
                'v2_group_id': cur['group_id'], 'v2_artifact_id': cur['artifact_id'],
                'v1_published_utc': prev['published_utc'], 'v2_published_utc': cur['published_utc'],
                'v1_anchor_sha': prev['anchor_sha'], 'v2_anchor_sha': cur['anchor_sha'],
                'v1_anchor_index': i, 'v2_anchor_index': j,
                'v1_anchor_method': prev['anchor_method'], 'v2_anchor_method': cur['anchor_method'],
                'commits_in_interval': j - i,
                # Both ends located by a Git tag: the interval's boundaries are the commits the two
                # releases were actually cut from, not a publication-date approximation.
                'tag_anchored': prev['anchor_method'].startswith('tag')
                                and cur['anchor_method'].startswith('tag'),
            })
        methods = {}
        for a in anchored:
            methods[a['anchor_method']] = methods.get(a['anchor_method'], 0) + 1
        print(f'{lib:22} {len(rows):4} stable  {len(chain):4} on mainline  {methods}', file=sys.stderr)

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, 'releases-anchored.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    with open(os.path.join(DATA, 'intervals.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(interval_rows[0].keys()))
        w.writeheader()
        w.writerows(interval_rows)
    covered = sum(r['commits_in_interval'] for r in interval_rows)
    print(f'{len(out_rows)} releases -> releases-anchored.csv', file=sys.stderr)
    print(f'{len(interval_rows)} intervals covering {covered} commits -> intervals.csv',
          file=sys.stderr)


if __name__ == '__main__':
    main()
