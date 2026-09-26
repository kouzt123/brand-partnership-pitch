#!/usr/bin/env python3
"""CLI helpers for the Codex skill. Codex owns analysis, writing and imagegen."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import zipfile
from urllib.parse import urlsplit

from common import SkillError, file_digest, read_json, write_json

ROOT = Path(__file__).resolve().parent.parent


def integer(value):
    n = int(value)
    if not 1 <= n <= 200:
        raise argparse.ArgumentTypeError("must be between 1 and 200")
    return n


def positive(value):
    n = float(value)
    if not 0 < n < 100000:
        raise argparse.ArgumentTypeError("must be positive and finite")
    return n


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Report executable/module/key presence; never print secrets")
    q = sub.add_parser("init", help="Create a private local job; no network calls")
    q.add_argument("--out", required=True)
    q.add_argument("--channel", required=True, help="Profile URL, handle with platform, or 'local'")
    q.add_argument("--platform", choices=["youtube", "tiktok", "instagram"])
    q.add_argument("--brief", required=True, help="Path to UTF-8 requirement text")
    q = sub.add_parser("fetch", help="Fetch channel through Apify; paid, explicit bounded run")
    q.add_argument("--channel", required=True)
    q.add_argument("--platform", choices=["youtube", "tiktok", "instagram"])
    q.add_argument("--out", required=True)
    q.add_argument("--state", required=True)
    q.add_argument("--limit", type=integer, default=15)
    q.add_argument("--max-charge", type=positive, default=1.0, help="Apify maxTotalChargeUsd per Actor run, not a global account cap")
    q.add_argument("--format", choices=["short", "long", "mixed"], default="mixed")
    q = sub.add_parser("recover-run", help="Recover an uncertain Apify submission after checking console")
    q.add_argument("--state", required=True)
    q.add_argument("--run-id", required=True)
    q = sub.add_parser("normalize", help="Normalize an existing Apify/yt-dlp dataset, offline")
    q.add_argument("--input", required=True)
    q.add_argument("--platform", choices=["youtube", "tiktok", "instagram"], required=True)
    q.add_argument("--channel", required=True)
    q.add_argument("--out", required=True)
    q = sub.add_parser("select", help="Select recent, high-performing and relevant samples")
    q.add_argument("--input", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--count", type=integer, default=5)
    q.add_argument("--keywords", default="")
    q = sub.add_parser("download", help="Download a selected video")
    q.add_argument("--url", required=True)
    q.add_argument("--out", required=True, help="File for https/apify-tiktok; new directory for yt-dlp")
    q.add_argument("--backend", choices=["https", "yt-dlp", "apify-tiktok"], default="https")
    q.add_argument("--state", help="Required for a paid TikTok download Actor run")
    q.add_argument("--max-mb", type=integer, default=200)
    q.add_argument("--max-charge", type=positive, default=1.0)
    q = sub.add_parser("prepare", help="Extract contact sheets, frames and mono audio")
    q.add_argument("--video", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--interval", type=positive, default=5)
    q.add_argument("--max-frames", type=integer, default=80)
    q.add_argument("--start", type=float, default=0)
    q.add_argument("--end", type=positive)
    q = sub.add_parser("transcribe", help="Import subtitles, run local ASR, or explicitly call ElevenLabs")
    q.add_argument("--audio")
    q.add_argument("--subtitles")
    q.add_argument("--out", required=True)
    q.add_argument("--backend", choices=["local", "subtitles", "elevenlabs"], default="local")
    q.add_argument("--model", default="small")
    q.add_argument("--language")
    q.add_argument("--offset", type=float, default=0)
    q.add_argument("--diarize", action="store_true")
    q = sub.add_parser("brief", help="Extract local TXT/MD/DOCX/PPTX/PDF text")
    q.add_argument("--input", required=True)
    q.add_argument("--out", required=True)
    q = sub.add_parser("validate", help="Validate script, timing, evidence and image freshness")
    q.add_argument("--script", required=True)
    q.add_argument("--require-images", action="store_true")
    q = sub.add_parser("image-plan", help="Export per-scene prompts for Codex's built-in imagegen")
    q.add_argument("--script", required=True)
    q.add_argument("--out", required=True)
    q = sub.add_parser("register-image", help="Bind an inspected image to a scene's current visual fingerprint")
    q.add_argument("--script", required=True)
    q.add_argument("--variant", required=True)
    q.add_argument("--scene", required=True)
    q.add_argument("--image", required=True, help="Path relative to script JSON")
    q.add_argument("--qa", help="Path to actual storyboard visual inspection JSON")
    q = sub.add_parser("bind-reference", help="Bind an inspected source frame to a cast member")
    q.add_argument("--script", required=True)
    q.add_argument("--cast", required=True)
    q.add_argument("--image", required=True)
    q.add_argument("--source", required=True)
    q.add_argument("--time", type=float, required=True)
    q = sub.add_parser("review", help="Aggregate recorded Codex review passes and rank alternatives")
    q.add_argument("--script", required=True)
    q.add_argument("--reviews", required=True)
    q = sub.add_parser("revise", help="Apply a proposed revision while enforcing scene locks and saving history")
    q.add_argument("--script", required=True)
    q.add_argument("--proposed", required=True)
    q.add_argument("--feedback", required=True)
    q = sub.add_parser("restore", help="Restore a saved script version, preserving the current version first")
    q.add_argument("--script", required=True)
    q.add_argument("--snapshot", required=True)
    q = sub.add_parser("diff", help="Classify revision changes and identify stale storyboards")
    q.add_argument("--before", required=True)
    q.add_argument("--after", required=True)
    q = sub.add_parser("render", help="Create DOCX, PDF and page PNGs in a new directory")
    q.add_argument("--script", required=True)
    q.add_argument("--out", required=True)
    q.add_argument("--theme")
    q.add_argument("--soffice", help="Verified bundled LibreOffice executable in Codex")
    q.add_argument("--docx-only", action="store_true")
    q.add_argument("--include-notes", action="store_true", help="Append full brief, review and source notes to the compact DOCX/PDF")
    q.add_argument("--allow-missing-images", action="store_true", help="Explicit text-only/degraded export; visibly labels missing illustrations")
    q = sub.add_parser("qa", help="Record a real human/agent visual inspection of all exported pages")
    q.add_argument("--export", required=True)
    q.add_argument("--pages", type=int, nargs="+", required=True)
    q.add_argument("--notes", required=True)
    q = sub.add_parser("package", help="Build a source-only installable ZIP using an explicit allowlist")
    q.add_argument("--out", required=True)
    return p


def execute(a):
    from providers import ACTORS, apify_run, channel_url, actor_input, normalize, select_videos, download_https, ytdlp_download
    from script_data import validate, visual_fingerprint, register_image, revision_diff
    if a.command == "doctor":
        return {"python": sys.version.split()[0], "modules": {m: bool(importlib.util.find_spec(m)) for m in ("docx", "PIL", "pypdf", "faster_whisper")},
                "executables": {n: shutil.which(n) for n in ("ffmpeg", "ffprobe", "yt-dlp", "soffice", "pdftoppm")},
                "credentials_present": {n: bool(os.environ.get(n)) for n in ("APIFY_API_TOKEN", "ELEVENLABS_API_KEY")},
                "agent_checks": ["Confirm image viewing and reference-image generation: Codex imagegen preferred; other agents need a configured image tool/API", "In Codex resolve bundled LibreOffice, not the user's desktop installation"]}
    if a.command == "init":
        out = Path(a.out)
        if out.exists():
            raise SkillError("Job directory already exists; resume it instead of overwriting")
        platform, url = ("local", None) if a.channel == "local" else channel_url(a.channel, a.platform)
        brief = Path(a.brief).read_text(encoding="utf-8")
        if not brief.strip():
            raise SkillError("Requirement text is empty")
        out.mkdir(parents=True, mode=0o700)
        for name in ("sources", "media", "analysis", "images", "revisions", "exports"):
            (out / name).mkdir()
        write_json(out / "request.json", {"schema_version": 1, "channel": {"platform": platform, "url": url}, "request": brief,
                   "created_at": datetime.now(timezone.utc).isoformat()})
        (out / ".gitignore").write_text("*\n", encoding="utf-8")
        return {"job": str(out.resolve()), "next": "Fetch or import source evidence, then follow SKILL.md"}
    if a.command == "fetch":
        platform, url = channel_url(a.channel, a.platform)
        payload = actor_input(platform, url, a.limit, a.format)
        raw, state = apify_run(ACTORS[platform], payload, a.state, limit=a.limit, max_charge=a.max_charge)
        result = normalize(platform, raw, url)
        result["provider"] = {"actor": ACTORS[platform], "run_id": state["run_id"], "usage_usd": state.get("usage_usd")}
        write_json(a.out, result)
        return {"output": a.out, "videos": len(result["videos"]), "run_id": state["run_id"]}
    if a.command == "recover-run":
        state = read_json(a.state)
        if state.get("run_id") or not re.fullmatch(r"[A-Za-z0-9]+", a.run_id):
            raise SkillError("Only an uncertain submission can be recovered; use an exact Apify run ID")
        state.update(run_id=a.run_id, status="RECOVERED")
        write_json(a.state, state)
        return {"next": "Repeat the original fetch/download command with this same state path"}
    if a.command == "normalize":
        rows = read_json(a.input)
        if isinstance(rows, dict):
            rows = rows.get("entries", [rows])
        result = normalize(a.platform, rows, a.channel)
        write_json(a.out, result)
        return {"output": a.out, "videos": len(result["videos"])}
    if a.command == "select":
        result = select_videos(read_json(a.input)["videos"], a.count, a.keywords)
        write_json(a.out, result)
        return {"output": a.out, "selected": [{"id": v["id"], "reason": v["selection_reason"]} for v in result]}
    if a.command == "download":
        if a.backend == "yt-dlp":
            return {"video": str(ytdlp_download(a.url, a.out, a.max_mb))}
        url = a.url
        if a.backend == "apify-tiktok":
            p = urlsplit(url)
            if p.scheme != "https" or p.hostname not in {"www.tiktok.com", "tiktok.com"} or not re.fullmatch(r"/@[^/]+/video/\d+", p.path) or p.username or p.password:
                raise SkillError("Use the canonical TikTok video URL")
            if not a.state:
                raise SkillError("--state is required for resumable paid download")
            raw, _ = apify_run(ACTORS["tiktok"], {"postURLs": [url], "shouldDownloadVideos": True, "resultsPerPage": 1}, a.state, limit=1, max_charge=a.max_charge)
            urls = raw[0].get("mediaUrls") or []
            if not urls:
                raise SkillError("Actor returned no downloadable video; do not resubmit automatically")
            url = urls[0]
        download_https(url, a.out, a.max_mb)
        return {"video": a.out, "sha256": file_digest(a.out)}
    if a.command == "prepare":
        from media import prepare
        result = prepare(a.video, a.out, interval=a.interval, max_frames=a.max_frames, start=a.start, end=a.end)
        return {"output": a.out, "frames": len(result["frames"]), "audio": result["audio"], "range": result["range"]}
    if a.command == "transcribe":
        from media import transcribe
        if a.backend == "subtitles" and not a.subtitles or a.backend != "subtitles" and not a.audio:
            raise SkillError("Supply --subtitles for subtitle import, or --audio for ASR")
        if a.offset < 0 or not math.isfinite(a.offset):
            raise SkillError("Offset must be finite and nonnegative")
        result = transcribe(a.audio, a.out, backend=a.backend, subtitle=a.subtitles, model=a.model, language=a.language, offset=a.offset, diarize=a.diarize)
        return {"output": a.out, "segments": len(result["segments"]), "backend": result["backend"]}
    if a.command == "brief":
        from media import extract_brief
        result = extract_brief(a.input, a.out)
        return {"output": a.out, "pages": len(result["pages"]), "needs_visual_review": result["needs_visual_review"]}
    if a.command == "validate":
        result = validate(read_json(a.script), Path(a.script).parent, require_images=a.require_images)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1
    if a.command == "image-plan":
        doc = read_json(a.script)
        from workflow import image_plan
        result = image_plan(doc, Path(a.script).resolve().parent)
        write_json(a.out, result)
        return {"output": a.out, "images": len(result), "executor": "Agent image tool; Codex built-in imagegen recommended. This command only prepares prompts/references."}
    if a.command == "register-image":
        return register_image(a.script, a.variant, a.scene, a.image, read_json(a.qa) if a.qa else None)
    if a.command == "bind-reference":
        from workflow import bind_reference
        return bind_reference(a.script, a.cast, a.image, a.source, a.time)
    if a.command == "review":
        from workflow import apply_reviews
        result = apply_reviews(read_json(a.script), read_json(a.reviews))
        write_json(a.script, result)
        return {"ranking": [{"id": v["id"], "verification": v["verification"]} for v in result["variations"]]}
    if a.command == "revise":
        from workflow import save_revision
        return save_revision(a.script, a.proposed, a.feedback)
    if a.command == "restore":
        from workflow import restore_revision
        return restore_revision(a.script, a.snapshot)
    if a.command == "diff":
        return revision_diff(read_json(a.before), read_json(a.after))
    if a.command == "render":
        from documents import render
        result = render(a.script, a.out, theme_path=a.theme, docx_only=a.docx_only, soffice=a.soffice, allow_missing_images=a.allow_missing_images, include_notes=a.include_notes)
        return {"export": a.out, "pages": len(result["pages"]), "visual_qa": result["visual_qa"]}
    if a.command == "qa":
        from documents import record_qa
        return record_qa(a.export, a.pages, a.notes)
    if a.command == "package":
        allowed = ["SKILL.md", "README.md", "LICENSE", ".gitignore", "requirements.txt", "requirements-transcription.txt"]
        files = [ROOT / n for n in allowed]
        for folder, suffixes in {"agents": {".yaml"}, "references": {".md"}, "assets": {".json", ".otf", ".txt"}, "scripts": {".py"}, "tests": {".py"}, "examples": {".json", ".srt", ".txt"}}.items():
            files.extend(p for p in (ROOT / folder).rglob("*") if p.suffix in suffixes and "__pycache__" not in p.parts)
        target = Path(a.out).resolve()
        if target.exists():
            raise SkillError("Package already exists; use a versioned filename")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(files):
                if path.is_symlink() or not path.is_file():
                    raise SkillError(f"Invalid distribution file: {path.name}")
                archive.write(path, Path("brand-partnership-pitch") / path.relative_to(ROOT))
        return {"archive": str(target), "files": len(files), "sha256": file_digest(target)}


def main():
    try:
        result = execute(parser().parse_args())
        if isinstance(result, int):
            return result
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (SkillError, ValueError, KeyError, TypeError, OSError, ImportError) as exc:
        # URLs or credentials can be present in low-level exception messages.
        message = str(exc) if isinstance(exc, SkillError) else ("A required Python module is missing; run doctor and install the relevant requirements into this Python environment" if isinstance(exc, ImportError) else f"Invalid input or local operation failed ({type(exc).__name__}); check input files and doctor output")
        print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
