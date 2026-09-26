"""Small, provider-neutral utilities. Never imports the Brand Partnership Pitch application."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.error import HTTPError, URLError


class SkillError(Exception):
    pass


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_asset(base, name):
    """Artifacts may only read assets inside the job, including resolved symlinks."""
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise SkillError("Asset paths must be relative to the script JSON directory")
    root = Path(base).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise SkillError(f"Missing or out-of-project asset: {name}")
    return path


def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise SkillError("Only public HTTPS URLs without embedded credentials are accepted")
    if parsed.port not in (None, 443):
        raise SkillError("Nonstandard URL ports are not accepted")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise SkillError("Could not resolve media host") from exc
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise SkillError("Local/private network URLs are not accepted")
    return url


class PublicRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl)
        # No provider credentials are ever passed to this media-only opener.
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SkillError("Unexpected redirect from provider API; request stopped")


def api_request(url, headers, payload=None, *, method=None, timeout=60, raw=False):
    body = payload if raw else (json.dumps(payload).encode() if payload is not None else None)
    request_headers = {"User-Agent": "brand-partnership-pitch/1.0", **headers}
    if body is not None and not raw:
        request_headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with build_opener(NoRedirects()).open(request, timeout=timeout) as response:
            data = response.read(32 * 1024 * 1024 + 1)
            if len(data) > 32 * 1024 * 1024:
                raise SkillError("Provider response exceeds 32 MiB")
            return json.loads(data)
    except HTTPError as exc:
        # Deliberately omit response body and URL: providers can echo secrets.
        raise SkillError(f"Provider HTTP {exc.code}; check credentials, quota and input. No automatic paid retry.") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise SkillError("Provider connection failed; inspect saved run state before retrying") from None


def run(args, *, timeout=300, env=None):
    try:
        result = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout, env=env)
    except FileNotFoundError:
        raise SkillError(f"Required executable not found: {args[0]}") from None
    except subprocess.TimeoutExpired:
        raise SkillError(f"Command exceeded {timeout} seconds: {Path(str(args[0])).name}") from None
    if result.returncode:
        # Keep URL-bearing stderr out of user logs (signed media URLs, cookies).
        raise SkillError(f"{Path(str(args[0])).name} failed (exit {result.returncode}); check input format and installed dependencies")
    return result.stdout
