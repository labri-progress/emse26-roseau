"""Stage 1: release inventory of every studied library, from the Maven Central index.

One HTTP request per group:artifact: the repo1 directory listing gives both the version list and
the publication date of each version directory.
"""
import csv
import os
import re
import subprocess
import sys
import time

from coords import COORDS


def _repo_root():
    """The replication package root, two levels above benchmark/releases/."""
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


REPO = os.environ.get('REPO_ROOT', _repo_root())
WALK_DATA = os.path.join(REPO, 'results/longitudinal/walk/notebooks/data')
WALK_YAML = os.path.join(REPO, 'benchmark/walk/walk.yaml')
DATA = os.environ.get('RELEASE_DATA', os.path.join(REPO, 'results/releases/data'))

BASE = 'https://repo1.maven.org/maven2'
UA = 'roseau-release-study/1.0 (research)'
ENTRY = re.compile(r'<a href="([^"/]+)/"[^>]*>[^<]*</a>\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})')

# A release is stable unless its version carries a pre-release qualifier.
PRERELEASE = re.compile(
    r'(?i)(^|[-._])(alpha|beta|rc|cr|m\d|milestone|snapshot|preview|ea|dev|pre|b\d+|incubat\w*|'
    r'candidate|test|early|nightly)([-._0-9]|$)')
# Some libraries ship parallel flavours of the same release (guava -jre/-android); keep one lane.
FLAVOUR = re.compile(r'(?i)-(android|jre)$')


def get(url):
    for attempt in range(5):
        p = subprocess.run(['curl', '-sSfL', '--max-time', '120', '-A', UA, url],
                           capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout
        if attempt == 4:
            raise RuntimeError(f'{url}: {p.stderr.strip()}')
        time.sleep(2 * (attempt + 1))


def is_stable(v):
    return PRERELEASE.search(FLAVOUR.sub('', v)) is None


def main():
    rows = []
    for lib, gas in COORDS.items():
        for (g, a) in gas:
            html = get(f'{BASE}/{g.replace(".", "/")}/{a}/')
            found = [(v, d) for v, d in ENTRY.findall(html) if not v.endswith('.xml')]
            for version, date in found:
                m = FLAVOUR.search(version)
                rows.append({
                    'library': lib, 'group_id': g, 'artifact_id': a, 'version': version,
                    'published_utc': date + ':00',
                    'flavour': m.group(1).lower() if m else '',
                    'is_stable': is_stable(version),
                })
            stable = sum(1 for v, _ in found if is_stable(v))
            print(f'{lib:22} {g}:{a:26} {len(found):5} versions ({stable} stable)', file=sys.stderr)
    rows.sort(key=lambda r: (r['library'], r['published_utc']))
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, 'releases-all.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} rows -> {DATA}/releases-all.csv', file=sys.stderr)


if __name__ == '__main__':
    main()
