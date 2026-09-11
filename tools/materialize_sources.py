#!/usr/bin/env python3
"""Materialize exactly one source-root inventory, resolving shared main copies."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]

def safe_relative(value):
    p = Path(value)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'Unsafe relative path: {value}')
    return p

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true')
    p.add_argument('--root-id')
    p.add_argument('--destination', type=Path)
    args = p.parse_args()
    entries = [json.loads(s) for s in (BASE/'manifests/files.jsonl').read_text().splitlines()]
    ids = sorted(set(e['root_id'] for e in entries))
    if args.list:
        print('\n'.join(ids)); return
    if args.root_id not in ids or args.destination is None:
        p.error('--root-id must exist and --destination is required')
    selected = [e for e in entries if e['root_id']==args.root_id]
    for e in selected:
        source = BASE/safe_relative(e['archive_path'])
        safe_relative(e['relative_path'])
        if hashlib.sha256(source.read_bytes()).hexdigest()!=e['sha256']:
            raise RuntimeError(f'Hash mismatch: {source}')
    dest = args.destination.expanduser().absolute()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError(f'Destination must not already exist: {dest}')
    dest.mkdir(parents=True, exist_ok=False)
    for e in selected:
        target = dest/safe_relative(e['relative_path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BASE/safe_relative(e['archive_path']), target)
    print(json.dumps({'root_id':args.root_id,'files':len(selected),'destination':str(dest)}))

if __name__=='__main__': main()
