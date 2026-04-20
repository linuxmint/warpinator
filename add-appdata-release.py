#!/usr/bin/env python3
"""Prepend a new <release> entry to the appdata template.

Pulls the version, date, and bullet list from the most recent
debian/changelog entry. Intended to be run manually after a release
has been tagged and the changelog updated. Review and edit the
generated description before committing.
"""
import re
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
CHANGELOG = REPO_ROOT / 'debian' / 'changelog'
APPDATA = REPO_ROOT / 'data' / 'org.x.Warpinator.appdata.xml.in.in'

HEADER_RE = re.compile(r'^\S+\s+\(([^)]+)\)')
TRAILER_RE = re.compile(r'^ -- .+?<.+?>\s+(.+)$')
BULLET_RE = re.compile(r'^\s*\*\s+(.+?)\s*$')


def parse_top_entry(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    m = HEADER_RE.match(lines[0])
    if not m:
        sys.exit(f"Couldn't parse version from first line of {path}")
    version = m.group(1)

    bullets = []
    date = None
    for line in lines[1:]:
        trailer = TRAILER_RE.match(line)
        if trailer:
            date = parsedate_to_datetime(trailer.group(1).strip()).strftime('%Y-%m-%d')
            break
        bullet = BULLET_RE.match(line)
        if bullet:
            bullets.append(bullet.group(1))

    if date is None:
        sys.exit(f"Couldn't find trailer line in top entry of {path}")

    return version, date, bullets


def xml_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def build_release_block(version, date, bullets):
    lines = [f'    <release version="{version}" date="{date}">',
             '      <description translatable="no" translate="no">']
    if len(bullets) <= 1:
        text = bullets[0] if bullets else 'Maintenance release.'
        lines.append(f'        <p>{xml_escape(text)}</p>')
    else:
        lines.append('        <ul>')
        for b in bullets:
            lines.append(f'          <li>{xml_escape(b)}</li>')
        lines.append('        </ul>')
    lines += ['      </description>', '    </release>', '']
    return '\n'.join(lines)


def main():
    version, date, bullets = parse_top_entry(CHANGELOG)

    text = APPDATA.read_text(encoding='utf-8')
    if re.search(rf'<release version="{re.escape(version)}"', text):
        sys.exit(f"Release {version} is already present in {APPDATA.name}")

    marker = '  <releases>\n'
    if marker not in text:
        sys.exit(f"Couldn't find <releases> block in {APPDATA.name}")

    block = build_release_block(version, date, bullets)
    APPDATA.write_text(text.replace(marker, marker + block, 1), encoding='utf-8')

    print(f"Added release {version} ({date}) to {APPDATA.relative_to(REPO_ROOT)}")
    print(f"  bullets: {len(bullets)}")
    print("Review the description and edit wording before committing.")


if __name__ == '__main__':
    main()
