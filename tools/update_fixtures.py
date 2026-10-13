"""Refresh/check the combat baseline from a pinned upstream Git commit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
FILES=('run.py','config.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref',default='origin/main')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',args.ref+'^{commit}']).decode().strip()
    contents={name:subprocess.check_output(['git','-C',str(ROOT),'show',commit+':dva/'+name]).replace(b'\r\n',b'\n') for name in FILES}
    directory=ROOT/'tests/fixtures/dva'
    metadata={'repository':'gogabs/dead-vs-alive','commit':commit,
              'sha256':{name:hashlib.sha256(data).hexdigest() for name,data in contents.items()}}
    meta=directory.parent/'origin.json'
    if args.check:
        valid=meta.exists() and json.loads(meta.read_text(encoding='utf8'))==metadata
        valid=valid and all((directory/name).read_bytes().replace(b'\r\n',b'\n')==data for name,data in contents.items())
        if not valid: raise SystemExit('Fixture is stale; run tools/update_fixtures.py after fetching origin/main')
    else:
        directory.mkdir(parents=True,exist_ok=True)
        for name,data in contents.items(): (directory/name).write_bytes(data)
        meta.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    print('Fixture checked at '+commit)


if __name__=='__main__': main()
