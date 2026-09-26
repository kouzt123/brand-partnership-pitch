"""Bounded Apify acquisition and optional yt-dlp. No LLM API calls."""
from __future__ import annotations

from datetime import datetime, timezone
import math
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener

from common import SkillError, PublicRedirects, api_request, digest, public_url, read_json, run, write_json

ACTORS = {"tiktok": "clockworks~tiktok-scraper", "youtube": "streamers~youtube-scraper", "instagram": "apify~instagram-scraper"}
API = "https://api.apify.com/v2"
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


def channel_url(value, platform=None):
    value = value.strip()
    if "://" not in value:
        if not platform:
            raise SkillError("A bare handle needs --platform; do not guess its platform")
        name = value.lstrip("@")
        if not re.fullmatch(r"[\w.\-]+", name):
            raise SkillError("Invalid channel handle")
        value = {"youtube": f"https://www.youtube.com/@{name}", "tiktok": f"https://www.tiktok.com/@{name}", "instagram": f"https://www.instagram.com/{name}/"}[platform]
    p = urlsplit(value)
    host = (p.hostname or "").lower()
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise SkillError("Use a canonical HTTPS channel URL")
    parts = [s for s in p.path.split("/") if s]
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        inferred = "youtube"
        valid = bool(parts) and ((parts[0].startswith("@") and len(parts[0]) > 1) or (parts[0] in {"channel", "c", "user"} and len(parts) >= 2))
        canonical = "/".join(parts[:1] if parts and parts[0].startswith("@") else parts[:2])
        url = f"https://www.youtube.com/{canonical}"
    elif host in {"tiktok.com", "www.tiktok.com"}:
        inferred = "tiktok"
        valid = len(parts) == 1 and parts[0].startswith("@") and len(parts[0]) > 1
        url = f"https://www.tiktok.com/{parts[0]}" if parts else ""
    elif host in {"instagram.com", "www.instagram.com"}:
        inferred = "instagram"
        valid = len(parts) == 1 and parts[0] not in {"p", "reel", "reels", "stories", "explore", "accounts"}
        url = f"https://www.instagram.com/{parts[0]}/" if parts else ""
    else:
        raise SkillError("Supported channel hosts: YouTube, TikTok, Instagram")
    if not valid or (platform and platform != inferred):
        raise SkillError("Use the creator profile URL, not a post, share link or mismatched platform")
    return inferred, url


def actor_input(platform, url, limit, video_format="mixed"):
    if platform == "tiktok":
        return {"profiles": [urlsplit(url).path.strip("/@")], "resultsPerPage": limit,
                "profileScrapeSections": ["videos"], "profileSorting": "latest",
                "shouldDownloadVideos": False, "shouldDownloadCovers": False}
    if platform == "instagram":
        return {"directUrls": [url], "resultsType": "reels", "resultsLimit": limit}
    return {"startUrls": [{"url": url}], "maxResults": limit if video_format != "short" else 0,
            "maxResultsShorts": limit if video_format != "long" else 0, "maxResultStreams": 0}


def apify_run(actor, payload, state_path, *, limit, max_charge, timeout=480):
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        raise SkillError("Set APIFY_API_TOKEN in the environment (never paste it in a prompt)")
    headers = {"Authorization": f"Bearer {token}"}
    key = digest({"actor": actor, "input": payload, "limit": limit, "max_charge": max_charge})
    state_path = Path(state_path)
    state = read_json(state_path) if state_path.exists() else None
    if state and state.get("key") != key:
        raise SkillError("Run state belongs to different inputs; choose a new state path")
    if state and not state.get("run_id"):
        raise SkillError("Previous Actor submission has an uncertain result. Check Apify console and recover its run ID before starting another paid run.")
    if not state:
        # Write intent BEFORE POST: a timeout/crash must not silently double-spend.
        write_json(state_path, {"key": key, "status": "SUBMITTING", "actor": actor})
        params = urlencode({"timeout": timeout, "maxItems": limit, "maxTotalChargeUsd": max_charge})
        response = api_request(f"{API}/acts/{actor}/runs?{params}", headers, payload)
        data = response["data"]
        state = {"key": key, "run_id": data["id"], "status": data["status"], "actor": actor}
        write_json(state_path, state)
    deadline = time.monotonic() + timeout + 30
    while True:
        data = api_request(f"{API}/actor-runs/{state['run_id']}?waitForFinish=10", headers)["data"]
        state.update(status=data["status"], dataset_id=data.get("defaultDatasetId"),
                     usage_usd=data.get("usageTotalUsd"))
        write_json(state_path, state)
        if state["status"] in TERMINAL:
            break
        if time.monotonic() > deadline:
            raise SkillError("Actor still running. Resume with the SAME state file; do not submit again.")
        time.sleep(1)
    if state["status"] != "SUCCEEDED":
        raise SkillError(f"Actor ended as {state['status']}. Saved state retained; no automatic paid rerun.")
    items = []
    while len(items) < limit:
        query = urlencode({"clean": "true", "format": "json", "offset": len(items), "limit": min(100, limit - len(items))})
        batch = api_request(f"{API}/datasets/{state['dataset_id']}/items?{query}", headers)
        if not isinstance(batch, list):
            raise SkillError("Unexpected Apify dataset shape")
        items.extend(batch)
        if not batch:
            break
    if not items:
        raise SkillError("No public videos returned; channel may be private, empty or unavailable")
    return items[:limit], state


def number(value):
    try:
        n = float(value)
        return max(0, n) if math.isfinite(n) else None
    except (TypeError, ValueError):
        return None


def duration(value):
    if isinstance(value, str) and ":" in value:
        try:
            return sum(float(part) * 60 ** i for i, part in enumerate(reversed(value.split(":"))))
        except ValueError:
            return None
    return number(value)


def normalize(platform, rows, url):
    videos, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or row.get("error"):
            continue
        if platform == "tiktok":
            meta = row.get("videoMeta") or {}
            media = row.get("mediaUrls") or []
            item = {"id": row.get("id"), "url": row.get("webVideoUrl"), "title": row.get("text", ""),
                    "published_at": row.get("createTimeISO"), "duration_seconds": duration(meta.get("duration")),
                    "views": number(row.get("playCount")), "likes": number(row.get("diggCount")),
                    "comments": number(row.get("commentCount")), "shares": number(row.get("shareCount")),
                    "media_url": media[0] if media else None}
        elif platform == "instagram":
            item = {"id": row.get("id") or row.get("shortCode"), "url": row.get("url"), "title": row.get("caption", ""),
                    "published_at": row.get("timestamp"), "duration_seconds": duration(row.get("videoDuration", row.get("duration"))),
                    "views": number(row.get("videoPlayCount", row.get("playsCount", row.get("videoViewCount", row.get("viewsCount"))))),
                    "likes": number(row.get("likesCount")), "comments": number(row.get("commentsCount")),
                    "shares": None, "media_url": row.get("videoUrl")}
        else:
            item = {"id": row.get("id"), "url": row.get("url") or row.get("webpage_url"), "title": row.get("title", ""),
                    "published_at": row.get("date") or row.get("upload_date"), "duration_seconds": duration(row.get("duration")),
                    "views": number(row.get("viewCount", row.get("view_count"))), "likes": number(row.get("likes", row.get("like_count"))),
                    "comments": number(row.get("commentsCount", row.get("comment_count"))), "shares": None, "media_url": None}
        if not item["url"] or item["url"] in seen:
            continue
        item["id"] = str(item["id"] or digest(item["url"])[:12])
        seen.add(item["url"])
        videos.append(item)
    if not videos:
        raise SkillError("Dataset contains no recognizable videos; inspect provider schema before proceeding")
    first = rows[0]
    profile = first.get("authorMeta", {}) if platform == "tiktok" else {}
    name = profile.get("nickName") or first.get("channelName") or first.get("channel") or first.get("ownerFullName") or first.get("ownerUsername") or url
    return {"schema_version": 1, "platform": platform, "url": url, "name": name,
            "fetched_at": datetime.now(timezone.utc).isoformat(), "videos": videos,
            "profile": {"bio": profile.get("signature") or first.get("channelDescription"),
                        "followers": number(profile.get("fans", first.get("numberOfSubscribers")))}}


def select_videos(videos, count, keywords=""):
    """Transparent sampling heuristic, not a prediction of future performance."""
    videos = list({v["id"]: v for v in videos}.values())
    tokens = set(re.findall(r"\w+", keywords.lower()))
    def relevance(v):
        return len(tokens & set(re.findall(r"\w+", v.get("title", "").lower())))
    def performance(v):
        return math.log1p(v.get("views") or 0) + .5 * math.log1p(v.get("likes") or 0) + .8 * math.log1p(v.get("comments") or 0)
    rankings = [(sorted(videos, key=lambda v: str(v.get("published_at") or ""), reverse=True), "recent representative"),
                (sorted(videos, key=performance, reverse=True), "high observed performance")]
    if tokens:
        rankings.append((sorted(videos, key=relevance, reverse=True), "brief keyword overlap"))
    chosen = []
    while len(chosen) < min(count, len(videos)):
        for ranking, reason in rankings:
            candidate = next((v for v in ranking if v["id"] not in {x["id"] for x in chosen}), None)
            if candidate and len(chosen) < count:
                chosen.append({**candidate, "selection_reason": reason})
    return chosen


def download_https(url, destination, max_mb=300):
    public_url(url)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    if destination.exists():
        raise SkillError("Destination already exists; use a new filename")
    try:
        with build_opener(PublicRedirects()).open(Request(url, headers={"User-Agent": "brand-partnership-pitch/1.0"}), timeout=45) as response:
            limit = max_mb * 1024 * 1024
            if int(response.headers.get("Content-Length", 0)) > limit:
                raise SkillError("Video exceeds download size limit")
            total, deadline = 0, time.monotonic() + 300
            with temporary.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > limit or time.monotonic() > deadline:
                        raise SkillError("Download exceeded size or time limit")
                    handle.write(chunk)
            if not total:
                raise SkillError("Downloaded file was empty")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def ytdlp_download(url, destination, max_mb=300):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.tiktok.com", "tiktok.com", "instagram.com", "www.instagram.com"} or p.username or p.password:
        raise SkillError("yt-dlp only accepts supported platform HTTPS URLs")
    destination = Path(destination).resolve()
    if destination.exists():
        raise SkillError("Download directory already exists; use a new directory")
    destination.mkdir(parents=True)
    run(["yt-dlp", "--ignore-config", "--no-playlist", "--no-overwrites", "--max-filesize", f"{max_mb}M",
         "--socket-timeout", "30", "--retries", "1", "--fragment-retries", "1", "--restrict-filenames",
         "-f", "bv*[height<=720]+ba/b[height<=720]/b", "--merge-output-format", "mp4",
         "--write-info-json", "--write-subs", "--sub-langs", "en.*,zh.*", "-o", str(destination / "video.%(ext)s"), "--", url], timeout=600)
    files = [p for p in destination.iterdir() if p.suffix.lower() in {".mp4", ".webm", ".mkv", ".mov"}]
    if not files:
        raise SkillError("No video downloaded; check availability or size limit")
    if any(p.stat().st_size > max_mb * 1024 * 1024 for p in files):
        raise SkillError("Downloaded media exceeds the requested size limit")
    return files[0]
