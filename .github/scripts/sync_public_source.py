#!/usr/bin/env python3
"""Pull public canonical files into this repository; never push across repositories.

Install at .github/scripts/sync_public_source.py. The state file is bootstrapped
once from the reviewed, matching initial copy, then committed with the workflow.
The hub's render step must run after copying and before finalize.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

STATE = Path('.github/sync-state.json')
SOURCES = {'profile': 'TED-H-com/teddashh', 'hub': 'TED-H-com/ted-h-com.github.io'}
FILES = {'profile': {'README.md', 'README.zh-TW.md'},
         'hub': {'README.md', 'README.zh-TW.md', 'LICENSE', 'hub.json'}}
PREFIXES = {'profile': ('assets/', 'projects/'), 'hub': ('kit/',)}

def git(*args, cwd=None):
    return subprocess.check_output(['git', *args], cwd=cwd)

def digest(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RuntimeError(f'Symlink refused: {path}')
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def allowed(path, kind):
    p = Path(path)
    return (not p.is_absolute() and '..' not in p.parts and
            (path in FILES[kind] or path.startswith(PREFIXES[kind])))

def manifest(kind):
    names = git('ls-files', '-z').decode().split('\0')
    return {p: digest(Path(p)) for p in names if p and
            (allowed(p, kind) or (kind == 'hub' and p.startswith('site/')))}

def stage_managed(kind):
    # Tracked paths include deletions; untracked paths include new generated files.
    names = set(git('ls-files', '-c', '-o', '--exclude-standard', '-z').decode().split('\0'))
    names = sorted(p for p in names if p and
                   (allowed(p, kind) or (kind == 'hub' and p.startswith('site/'))))
    if names:
        subprocess.run(['git', '--literal-pathspecs', 'add', '-A', '--pathspec-from-file=-', '--pathspec-file-nul'],
                       input=('\0'.join(names) + '\0').encode(), check=True)

def fetch_inputs(source, sha, kind):
    with tempfile.TemporaryDirectory(prefix='public-source-') as d:
        git('init', '--quiet', d)
        git('fetch', '--quiet', '--depth=1', f'https://github.com/{source}.git', sha, cwd=d)
        incoming = {}
        for entry in git('ls-tree', '-r', '-z', 'FETCH_HEAD', cwd=d).split(b'\0'):
            if not entry:
                continue
            meta, raw_path = entry.split(b'\t', 1)
            mode, type_, blob = meta.decode().split()
            name = raw_path.decode('utf-8')
            if not allowed(name, kind):
                continue
            if mode not in ('100644', '100755') or type_ != 'blob':
                raise RuntimeError(f'Non-regular canonical file refused: {name}')
            incoming[name] = (git('cat-file', 'blob', blob, cwd=d), mode)
        return incoming

def state_write(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')

def output(value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'changed={str(value).lower()}\n')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=SOURCES)
    ap.add_argument('--initialize', metavar='REVIEWED_SOURCE_SHA')
    ap.add_argument('--finalize', action='store_true')
    args = ap.parse_args()
    kind, source = args.kind, SOURCES[args.kind]
    if args.initialize:
        if STATE.exists() or not re.fullmatch('[0-9a-f]{40}', args.initialize):
            raise RuntimeError('Initialize requires a new state file and a full reviewed source SHA')
        incoming = fetch_inputs(source, args.initialize, kind)
        actual = {p: h for p, h in manifest(kind).items() if allowed(p, kind)}
        expected = {p: hashlib.sha256(data).hexdigest() for p, (data, _) in incoming.items()}
        if actual != expected:
            raise RuntimeError('Initial personal inputs do not match the reviewed canonical SHA')
        state_write({'source': source, 'sha': args.initialize, 'files': manifest(kind)})
        return
    state = json.loads(STATE.read_text())
    if state['source'] != source:
        raise RuntimeError('Unexpected canonical source')
    if args.finalize:
        stage_managed(kind)
        state['files'] = manifest(kind)
        state_write(state)
        git('add', '--', str(STATE))
        return
    remote = f'https://github.com/{source}.git'
    refs = git('ls-remote', '--exit-code', remote, 'refs/heads/main').decode().split()
    sha = refs[0]
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise RuntimeError('Invalid source SHA')
    if kind == 'hub':
        for name in git('ls-files', '-z', 'site').decode().split('\0'):
            if name and name not in state['files']:
                raise RuntimeError(f'Unmanaged personal site file; review before regenerating: {name}')
    for name, expected in state['files'].items():
        if not (allowed(name, kind) or (kind == 'hub' and name.startswith('site/'))):
            raise RuntimeError('Unexpected managed path')
        if digest(Path(name)) != expected:
            raise RuntimeError(f'Personal edit detected; reconcile with canonical source first: {name}')
    if sha == state['sha']:
        output(False)
        return
    incoming = fetch_inputs(source, sha, kind)
    for name in incoming:
        p = Path(name)
        if any(parent.is_symlink() for parent in (p, *p.parents)):
            raise RuntimeError(f'Symlink path refused: {name}')
        if p.exists() and name not in state['files']:
            raise RuntimeError(f'Unmanaged personal file collision: {name}')
    # Validate all paths before changing anything. Delete only previously managed inputs.
    for name in state['files']:
        if allowed(name, kind) and name not in incoming:
            Path(name).unlink(missing_ok=True)
    for name, (content, mode) in incoming.items():
        p = Path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content)
        p.chmod(0o755 if mode == '100755' else 0o644)
    state['sha'] = sha
    state_write(state)
    output(True)
    print(f'Copied allowlisted inputs from {source}@{sha}')

if __name__ == '__main__':
    main()
