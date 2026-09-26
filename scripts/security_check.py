#!/usr/bin/env python3
"""Scan release files without printing matched secret values. No network access."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'Apify token': rb'apify_api_[A-Za-z0-9]{15,}',
    'API secret key': rb'\bsk[_-](?:proj-)?[A-Za-z0-9_-]{20,}',
    'GitHub token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',
    'cloud access key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'private key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    'credential in URL': rb'https?://[^\s/]+:[^\s/]+@',
    'signed or credential URL': rb'[?&](?:X-Amz-Signature|api_key|api_token|access_token)=[A-Za-z0-9_%+-]{12,}',
    'literal credential assignment': rb'''(?i)(?:api[_-]?key|api[_-]?token|secret|password)["']?\s*[:=]\s*["'][A-Za-z0-9_+/-]{24,}["']''',
    'developer home path': rb'/Users/[A-Za-z0-9_.-]+/',
}
SKIP = {'.git', '__pycache__', '.venv', 'node_modules'}
PRIVATE_DIRS = {'jobs','output','outputs','dist','backups','media','exports','revisions','live-tests'}
PRIVATE_EXTS = {'.mp4','.mov','.webm','.wav','.mp3','.m4a','.pem','.p12','.key','.zip','.log','.pyc'}

def inspect(paths):
    issues=[]
    for path in paths:
        rel=path.relative_to(ROOT)
        if path.is_symlink():
            issues.append((str(rel),'symlink is not a distributable file'));continue
        if not path.is_file():continue
        if any(x in PRIVATE_DIRS for x in rel.parts) or path.suffix.lower() in PRIVATE_EXTS or path.name.startswith(('.env','cookies')):
            issues.append((str(rel),'private/runtime file is not allowed'));continue
        data=path.read_bytes()
        # The unmodified licensed OTF is the only binary asset class in this source release.
        if path.suffix == '.otf':continue
        for name,pattern in PATTERNS.items():
            if re.search(pattern,data):issues.append((str(rel),name))
    return issues

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--staged',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:
        cases={'Apify token': b'apify'+b'_api_'+b'A'*24,'API secret key':b's'+b'k_'+b'b'*40,'GitHub token':b'gh'+b'p_'+b'c'*30,'private key':b'-----BEGIN '+b'PRIVATE KEY-----','developer home path':b'/Users/'+b'fixture/'}
        assert all(re.search(PATTERNS[k],v) for k,v in cases.items())
        print('Scanner detector self-test passed; no fixture values emitted');return
    if a.staged:
        names=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'],cwd=ROOT).decode().split('\0')
        paths=[ROOT/n for n in names if n]
        # Inspect the staged blobs, not only the working files.
        issues=[]
        for path in paths:
            rel=str(path.relative_to(ROOT))
            data=subprocess.check_output(['git','show',':'+rel],cwd=ROOT)
            for name,pattern in PATTERNS.items():
                if path.suffix != '.otf' and re.search(pattern,data):issues.append((rel,name+' (staged)'))
        issues+=inspect(paths)
    else:
        paths=[x for x in ROOT.rglob('*') if x.is_file() and not any(part in SKIP for part in x.relative_to(ROOT).parts)]
        issues=inspect(paths)
    for path,kind in issues:print(f'BLOCKED {path}: {kind}')
    print(f'Scanned {len(paths)} files; {len(issues)} findings. Matched values are never printed.')
    if issues:sys.exit(1)

if __name__=='__main__':main()
