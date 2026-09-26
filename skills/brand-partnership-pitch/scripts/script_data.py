"""Structural and temporal checks; creative judgments remain with Codex."""
from __future__ import annotations

import math
from pathlib import Path
import re

from common import SkillError, digest, file_digest, local_asset, read_json, write_json


def visual_fingerprint(script, variant, scene):
    return digest({"style": script.get("visual_style"), "cast": [c for c in script.get("cast", []) if c["id"] in scene.get("cast_ids", [])],
                   "aspect_ratio": variant.get("aspect_ratio"), "visual": scene.get("visual"),
                   "onscreen_text": scene.get("onscreen_text"), "prompt": scene.get("image_prompt")})


def validate(script, base, *, require_images=False):
    errors, warnings = [], []
    def text(value):
        return isinstance(value, str) and bool(value.strip())
    def numeric(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if not isinstance(script, dict):
        return {"valid": False, "errors": ["Script must be a JSON object"], "warnings": []}
    if script.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for field in ("title", "language", "summary", "visual_style"):
        if not text(script.get(field)):
            errors.append(f"{field} must be a nonempty string")
    channel = script.get("channel")
    if not isinstance(channel, dict) or not text(channel.get("name")) or channel.get("platform") not in {"youtube", "instagram", "tiktok", "local"}:
        errors.append("channel needs name and platform (youtube/instagram/tiktok/local)")
    brief = script.get("brief")
    if not isinstance(brief, dict):
        errors.append("brief must be an object")
        brief = {}
    if brief.get("kind") not in {"sponsored", "organic", "tutorial", "drama", "other"}:
        errors.append("brief.kind must be sponsored/organic/tutorial/drama/other")
    for field in ("objective", "audience"):
        if not text(brief.get(field)):
            errors.append(f"brief.{field} must be nonempty")
    for field in ("must_include", "must_avoid", "facts"):
        if not isinstance(brief.get(field), list) or not all(text(v) for v in brief[field]):
            errors.append(f"brief.{field} must be an array of strings")
    cast = script.get("cast", [])
    if not isinstance(cast, list) or not all(isinstance(c, dict) and text(c.get("id")) and text(c.get("name")) and text(c.get("appearance")) for c in cast):
        errors.append("cast must contain id, name, appearance objects (or be empty)")
        cast = []
    for c in cast:
        for ref in c.get("references", []):
            try:
                if file_digest(local_asset(base, ref["path"])) != ref.get("sha256"):
                    errors.append(f"{c['id']}: creator reference file changed")
            except (SkillError, KeyError, OSError, TypeError):
                errors.append(f"{c['id']}: invalid creator reference")
    cast_ids = [c["id"] for c in cast]
    if len(set(cast_ids)) != len(cast_ids):
        errors.append("cast IDs must be unique")
    evidence = script.get("evidence", [])
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
        evidence = []
    evidence_ids = set()
    for e in evidence:
        if not isinstance(e, dict) or not all(text(e.get(f)) for f in ("id", "source", "observation")):
            errors.append("evidence needs id, source, observation")
            continue
        if e["id"] in evidence_ids:
            errors.append("evidence IDs must be unique")
        evidence_ids.add(e["id"])
        if "time_seconds" in e and (not numeric(e["time_seconds"]) or e["time_seconds"] < 0):
            errors.append(f"Evidence {e['id']}: invalid timestamp")
    variations = script.get("variations")
    if not isinstance(variations, list) or not variations:
        errors.append("variations must be a nonempty array")
        variations = []
    ids, recommended = set(), 0
    for v in variations:
        if not isinstance(v, dict):
            errors.append("Every variation must be an object")
            continue
        verification = v.get("verification", {})
        if require_images and script.get("storyboard_contract") == "brand-pitch-bw-v1" and verification.get("status") != "reviewed":
            errors.append("Illustrated delivery needs a current recorded script review")
        if verification.get("status") == "reviewed":
            from workflow import review_fingerprint
            if verification.get("script_fingerprint") != review_fingerprint(v):
                errors.append("Review is stale after script changes; review again")
        label = str(v.get("id", "unknown"))
        if not text(v.get("id")) or not re.fullmatch(r"[a-zA-Z0-9_-]+", label) or label in ids:
            errors.append(f"Variation {label}: ID must be unique and filesystem-safe")
        ids.add(label)
        recommended += v.get("recommended") is True
        if not isinstance(v.get("recommended"), bool):
            errors.append(f"{label}: recommended must be boolean")
        for f in ("title", "angle", "hook", "format", "fit_reason"):
            if not text(v.get(f)):
                errors.append(f"{label}.{f} must be nonempty")
        if v.get("aspect_ratio") not in {"9:16", "16:9", "1:1", "4:5"}:
            errors.append(f"{label}: invalid aspect_ratio")
        target = v.get("duration_seconds")
        if not numeric(target) or target <= 0:
            errors.append(f"{label}: invalid duration_seconds")
        scenes = v.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            errors.append(f"{label}: scenes must be nonempty")
            continue
        scene_ids, previous = set(), 0
        for scene in scenes:
            if not isinstance(scene, dict):
                errors.append(f"{label}: scene must be an object")
                continue
            sid = str(scene.get("id", "unknown"))
            prefix = f"{label}/{sid}"
            if not text(scene.get("id")) or not re.fullmatch(r"[a-zA-Z0-9_-]+", sid) or sid in scene_ids:
                errors.append(f"{prefix}: ID must be unique and filesystem-safe")
            scene_ids.add(sid)
            for f in ("title", "visual", "audio", "onscreen_text", "notes", "image_prompt"):
                if not isinstance(scene.get(f), str) or (f in {"title", "visual", "audio", "image_prompt"} and not text(scene[f])):
                    errors.append(f"{prefix}.{f}: missing or invalid string")
            start, end = scene.get("start"), scene.get("end")
            if not numeric(start) or not numeric(end) or start < 0 or end <= start:
                errors.append(f"{prefix}: invalid time range")
            else:
                if abs(start - previous) > .05:
                    errors.append(f"{prefix}: gap/overlap; starts at {start}, previous ends at {previous}")
                previous = end
                audio = scene.get("audio", "")
                spoken = re.sub(r"\[[^]]*\]|\([^)]*\)|^[\w \-]+:", "", audio if isinstance(audio, str) else "", flags=re.M)
                cjk = len(re.findall(r"[\u3400-\u9fff]", spoken))
                latin = len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", spoken))
                estimated = cjk / 4.5 + latin / 2.6
                if estimated > (end - start) * 1.2:
                    warnings.append(f"{prefix}: speech estimate {estimated:.1f}s exceeds {end - start:.1f}s; perform a read-through")
            for field, known in (("cast_ids", set(cast_ids)), ("evidence_ids", evidence_ids)):
                refs = scene.get(field)
                if not isinstance(refs, list) or not all(isinstance(r, str) and r in known for r in refs):
                    errors.append(f"{prefix}: invalid {field}")
            if require_images and script.get("storyboard_contract") == "brand-pitch-bw-v1":
                for person in cast:
                    if person["id"] in scene.get("cast_ids", []) and person.get("identity", "observed") == "observed" and not person.get("references"):
                        errors.append(f"{prefix}: observed actor has no bound reference")
            image = scene.get("image")
            if require_images and not image:
                errors.append(f"{prefix}: storyboard image missing")
            if image:
                if not isinstance(image, dict) or not text(image.get("path")):
                    errors.append(f"{prefix}: malformed image record")
                else:
                    if script.get("storyboard_contract") == "brand-pitch-bw-v1":
                        qa = image.get("qa") or {}
                        if not all(qa.get(k) is True for k in ("black_white", "identity_match", "no_text", "action_match")) or not qa.get("notes"):
                            errors.append(f"{prefix}: storyboard inspection record missing")
                    try:
                        path = local_asset(base, image["path"])
                        if image.get("sha256") != file_digest(path):
                            errors.append(f"{prefix}: image file changed; inspect and register again")
                        if image.get("visual_fingerprint") != visual_fingerprint(script, v, scene):
                            errors.append(f"{prefix}: image is stale after a visual/cast/style change")
                        from PIL import Image
                        with Image.open(path) as im:
                            im.verify()
                    except (SkillError, OSError, ValueError) as exc:
                        errors.append(f"{prefix}: invalid image asset ({exc})")
        if numeric(target) and abs(previous - target) > .1:
            errors.append(f"{label}: final scene ends at {previous}, expected {target}")
        for field in ("production", "requirements_check"):
            if not isinstance(v.get(field), list) or not all(text(x) for x in v[field]):
                errors.append(f"{label}.{field} must be an array of strings")
    if recommended != 1:
        errors.append("Exactly one variation must be recommended")
    if not evidence:
        warnings.append("No channel evidence is recorded; disclose limited personalization")
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def register_image(script_path, variant_id, scene_id, image_path, qa=None):
    script_path = Path(script_path)
    script = read_json(script_path)
    asset = local_asset(script_path.parent, image_path)
    from PIL import Image
    with Image.open(asset) as image:
        image.verify()
    for variant in script["variations"]:
        for scene in variant["scenes"]:
            if variant["id"] == variant_id and scene["id"] == scene_id:
                if script.get("storyboard_contract") == "brand-pitch-bw-v1":
                    from PIL import ImageChops, ImageStat
                    with Image.open(asset) as im:
                        rgb = im.convert("RGB").resize((128, 128))
                        r, g, b = rgb.split()
                        chroma = max(ImageStat.Stat(ImageChops.difference(r, g)).mean[0], ImageStat.Stat(ImageChops.difference(g, b)).mean[0])
                    if chroma > 3:
                        raise SkillError("Storyboard contains color; regenerate as a black-and-white sketch")
                    if not qa or not all(qa.get(k) is True for k in ("black_white", "identity_match", "no_text", "action_match")) or not qa.get("notes", "").strip():
                        raise SkillError("Storyboard registration requires an actual inspection record: black_white, identity_match, no_text, action_match, notes")
                scene["image"] = {"path": image_path, "sha256": file_digest(asset),
                                  "visual_fingerprint": visual_fingerprint(script, variant, scene), "qa": qa}
                write_json(script_path, script)
                return scene["image"]
    raise SkillError("Variation/scene ID not found")


def revision_diff(old, new):
    def indexed(doc):
        return {(v["id"], s["id"]): (v, s) for v in doc["variations"] for s in v["scenes"]}
    a, b = indexed(old), indexed(new)
    report = {"added": [], "removed": [], "regenerate_images": [], "text_only": [], "unchanged": []}
    for key in sorted(a.keys() | b.keys()):
        label = "/".join(key)
        if key not in a:
            report["added"].append(label)
        elif key not in b:
            report["removed"].append(label)
        elif visual_fingerprint(old, *a[key]) != visual_fingerprint(new, *b[key]):
            report["regenerate_images"].append(label)
        elif a[key][1] != b[key][1]:
            report["text_only"].append(label)
        else:
            report["unchanged"].append(label)
    return report
