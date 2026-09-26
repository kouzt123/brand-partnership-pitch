#!/usr/bin/env python3
"""Scan release files without printing matched secret values. No network access."""
import argparse
import io
from pathlib import Path
import re
import subprocess
import sys
import zipfile

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

def scan_blob(rel, data):
    """Inspect document contents too; fail closed if parsing fails."""
    suffix = Path(rel).suffix.lower()
    if suffix == '.otf':
        return []  # Unmodified licensed font.
    parts = [data]
    try:
        if suffix == '.docx':
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if sum(x.file_size for x in archive.infolist()) > 100 * 1024 * 1024:
                    return [(rel, 'document exceeds scan size limit')]
                for member in archive.infolist():
                    raw = archive.read(member)
                    parts.append(raw)
                    if member.filename.endswith('.xml'):
                        from xml.etree import ElementTree
                        # Join runs so a split credential is still detected.
                        parts.append(''.join(ElementTree.fromstring(raw).itertext()).encode())
        elif suffix == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data), strict=True)
            if reader.is_encrypted:
                return [(rel, 'encrypted document cannot be scanned')]
            parts.append(str(reader.metadata).encode())
            parts.extend((page.extract_text() or '').encode() for page in reader.pages)
    except Exception:
        return [(rel, 'document could not be scanned; install requirements and check file')]
    return [(rel, name) for name, pattern in PATTERNS.items()
            if any(re.search(pattern, part) for part in parts)]

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
        issues += scan_blob(str(rel), data)
    return issues

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--staged',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:
        cases={'Apify token': b'apify'+b'_api_'+b'A'*24,'API secret key':b's'+b'k_'+b'b'*40,'GitHub token':b'gh'+b'p_'+b'c'*30,'private key':b'-----BEGIN '+b'PRIVATE KEY-----','developer home path':b'/Users/'+b'fixture/'}
        assert all(re.search(PATTERNS[k],v) for k,v in cases.items())
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            token = cases['Apify token']
            archive.writestr('word/document.xml', b'<doc><run>' + token[:10] + b'</run><run>' + token[10:] + b'</run></doc>')
        assert ('fixture.docx', 'Apify token') in scan_blob('fixture.docx', buffer.getvalue())
        from pypdf import PdfWriter
        writer = PdfWriter(); writer.add_blank_page(width=72, height=72)
        writer.add_metadata({'/Subject': cases['API secret key'].decode()})
        buffer = io.BytesIO(); writer.write(buffer)
        assert ('fixture.pdf', 'API secret key') in scan_blob('fixture.pdf', buffer.getvalue())
        assert scan_blob('fixture.pdf', b'broken')
        assert not scan_blob('fixture.md', b'Public example with no credentials.')
        print('Source, compressed DOCX and PDF detector checks passed; no fixture values emitted');return
    if a.staged:
        names=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=ACMR','-z'],cwd=ROOT).decode().split('\0')
        paths=[ROOT/n for n in names if n]
        # Inspect the staged blobs, not only the working files.
        issues=[]
        for path in paths:
            rel=str(path.relative_to(ROOT))
            data=subprocess.check_output(['git','show',':'+rel],cwd=ROOT)
            issues.extend((name, kind + ' (staged)') for name, kind in scan_blob(rel, data))
        issues+=inspect(paths)
    else:
        paths=[x for x in ROOT.rglob('*') if x.is_file() and not any(part in SKIP for part in x.relative_to(ROOT).parts)]
        issues=inspect(paths)
    for path,kind in issues:print(f'BLOCKED {path}: {kind}')
    print(f'Scanned {len(paths)} files; {len(issues)} findings. Matched values are never printed.')
    if issues:sys.exit(1)

if __name__=='__main__':main()
