"""Local frame/audio preparation and interchangeable transcription backends."""
from __future__ import annotations

import html
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import uuid

from common import SkillError, api_request, file_digest, read_json, run, write_json


def prepare(video, out, *, interval=5.0, max_frames=80, start=0.0, end=None):
    from PIL import Image, ImageDraw
    source, out = Path(video).resolve(), Path(out).resolve()
    if out.exists():
        raise SkillError("Preparation output already exists; reuse its manifest or choose a new directory")
    probe = json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", source]))
    total = float(probe.get("format", {}).get("duration", 0))
    end = min(total, end if end is not None else total)
    if not math.isfinite(total) or not total > 0 or not 0 <= start < end or interval <= 0 or max_frames < 2:
        raise SkillError("Invalid media duration, range, interval or frame limit")
    if not any(s["codec_type"] == "video" for s in probe["streams"]):
        raise SkillError("Input has no video stream")
    out.mkdir(parents=True)
    frames_dir = out / "frames"
    frames_dir.mkdir()
    # Allocate across the WHOLE requested range, while enriching the opening.
    video_end = min(end, next((float(s["duration"]) for s in probe["streams"] if s["codec_type"] == "video" and s.get("duration") not in (None, "N/A")), end))
    end_sample = max(start, video_end - .15)
    base_count = min(max_frames - 1, max(2, math.ceil((end - start) / interval) + 1))
    times = {round(start + (end_sample - start) * i / (base_count - 1), 3) for i in range(base_count)}
    for t in (.5, 1, 2, 3):
        if len(times) < max_frames and start + t < end_sample:
            times.add(round(start + t, 3))
    frames = []
    for i, timestamp in enumerate(sorted(times)):
        target = frames_dir / f"frame-{i + 1:03d}.jpg"
        run(["ffmpeg", "-nostdin", "-v", "error", "-ss", timestamp, "-i", source,
             "-frames:v", "1", "-vf", "scale=960:960:force_original_aspect_ratio=decrease:out_range=full", "-pix_fmt", "yuvj420p", "-q:v", "3", target])
        if not target.is_file():
            raise SkillError("A requested frame could not be decoded")
        frames.append({"time_seconds": timestamp, "path": str(target.relative_to(out))})
    sheets = []
    for offset in range(0, len(frames), 12):
        batch = frames[offset:offset + 12]
        sheet = Image.new("RGB", (1200, math.ceil(len(batch) / 3) * 250), "#edf0f4")
        draw = ImageDraw.Draw(sheet)
        for j, frame in enumerate(batch):
            with Image.open(out / frame["path"]) as im:
                im = im.convert("RGB")
                im.thumbnail((384, 216))
                x, y = (j % 3) * 400, (j // 3) * 250
                sheet.paste(im, (x + (400 - im.width) // 2, y + 6))
                draw.text((x + 10, y + 227), f"{frame['time_seconds']:.2f}s | {Path(frame['path']).name}", fill="#172339")
        path = out / f"contact-{offset // 12 + 1:02d}.jpg"
        sheet.save(path, quality=90)
        sheets.append(path.name)
    audio = None
    if any(s["codec_type"] == "audio" for s in probe["streams"]):
        audio = "audio.wav"
        run(["ffmpeg", "-nostdin", "-v", "error", "-ss", start, "-i", source, "-t", end - start,
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out / audio], timeout=600)
    manifest = {"schema_version": 1, "source_sha256": file_digest(source), "duration_seconds": total,
                "range": {"start": start, "end": end}, "audio_offset_seconds": start, "audio": audio,
                "frames": frames, "contact_sheets": sheets,
                "coverage": "sampled frames; continuous motion and untranscribed audio are not fully observed"}
    write_json(out / "media.json", manifest)
    return manifest


def seconds(value):
    parts = value.strip().replace(",", ".").split(":")
    return sum(float(v) * 60 ** i for i, v in enumerate(reversed(parts)))


def subtitles(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    segments = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if " --> " in line), None)
        if timing is None:
            continue
        left, right = lines[timing].split(" --> ", 1)
        try:
            start, end = seconds(left), seconds(right.split()[0])
        except ValueError:
            continue
        words = html.unescape(re.sub(r"<[^>]+>", "", " ".join(lines[timing + 1:]))).strip()
        if 0 <= start < end and math.isfinite(end) and words:
            segments.append({"start": start, "end": end, "text": words, "speaker": None})
    if not segments:
        raise SkillError("No timed subtitle cues found; use SRT or VTT")
    return segments


def transcribe(audio, out, *, backend="local", subtitle=None, model="small", language=None, offset=0, diarize=False):
    out = Path(out)
    source = Path(subtitle if backend == "subtitles" else audio).resolve()
    fingerprint = {"sha256": file_digest(source), "backend": backend, "model": model,
                   "language": language, "offset": offset, "diarize": diarize}
    if out.exists():
        cached = read_json(out)
        if cached.get("input") == fingerprint:
            return cached
        raise SkillError("Transcript output contains different inputs; choose a new file")
    words = []
    if backend == "subtitles":
        if not subtitle:
            raise SkillError("--subtitles is required for the subtitles backend")
        segments = subtitles(subtitle)
        actual_model = "provided-subtitles"
    elif backend == "local":
        if diarize:
            raise SkillError("Local transcription does not identify speakers; omit --diarize or explicitly use ElevenLabs")
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise SkillError("faster-whisper is not installed. Use subtitles or install requirements-transcription.txt") from None
        engine = WhisperModel(model, device="cpu", compute_type="int8")
        result, info = engine.transcribe(str(source), language=language, word_timestamps=True, vad_filter=True)
        segments = []
        for segment in result:
            segments.append({"start": segment.start, "end": segment.end, "text": segment.text.strip(), "speaker": None})
            words.extend({"start": w.start, "end": w.end, "text": w.word, "speaker": None} for w in (segment.words or []))
        language, actual_model = info.language, model
    else:
        key = os.environ.get("ELEVENLABS_API_KEY")
        if not key:
            raise SkillError("Set ELEVENLABS_API_KEY in the environment to use ElevenLabs")
        if source.stat().st_size > 100 * 1024 * 1024:
            raise SkillError("Split audio before cloud transcription: upload limit is 100 MiB per request")
        actual_model = "scribe_v2" if model == "small" else model
        boundary = "brand-pitch-" + uuid.uuid4().hex
        fields = {"model_id": actual_model, "timestamps_granularity": "word", "diarize": str(diarize).lower(), "tag_audio_events": "true"}
        if language:
            fields["language_code"] = language
        body = bytearray()
        for name, value in fields.items():
            body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio{source.suffix}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
        body.extend(source.read_bytes())
        body.extend(f"\r\n--{boundary}--\r\n".encode())
        intent = out.with_suffix(out.suffix + ".request.json")
        if intent.exists():
            raise SkillError("An earlier ElevenLabs request has no saved transcript. Inspect provider history before explicitly removing the request marker and retrying.")
        write_json(intent, {"input": fingerprint, "status": "submitting"})
        data = api_request("https://api.elevenlabs.io/v1/speech-to-text", {"xi-api-key": key, "Content-Type": f"multipart/form-data; boundary={boundary}"}, bytes(body), timeout=600, raw=True)
        write_json(out.with_suffix(out.suffix + ".provider.json"), data)
        language = data.get("language_code", language)
        words = [{"start": w["start"], "end": w["end"], "text": w["text"], "speaker": w.get("speaker_id"), "type": w.get("type", "word")} for w in data.get("words", [])]
        segments = []
        # Preserve speaker turns rather than turning diarized words into one blob.
        for word in words:
            if word.get("type") == "spacing":
                continue
            if not segments or segments[-1]["speaker"] != word["speaker"] or word["start"] - segments[-1]["end"] > 1.5 or word["end"] - segments[-1]["start"] > 15:
                segments.append({"start": word["start"], "end": word["end"], "text": word["text"], "speaker": word["speaker"]})
            else:
                segments[-1]["text"] += " " + word["text"]
                segments[-1]["end"] = word["end"]
        if not segments and data.get("text"):
            raise SkillError("ElevenLabs returned text without usable timing; preserve provider result before retry")
    for item in segments + words:
        item["start"] = round(item["start"] + offset, 3)
        item["end"] = round(item["end"] + offset, 3)
    result = {"schema_version": 1, "input": fingerprint, "backend": backend, "model": actual_model,
              "language": language, "segments": segments, "words": words,
              "text": "\n".join(s["text"] for s in segments), "no_speech_detected": not bool(segments)}
    write_json(out, result)
    return result


def extract_brief(path, out):
    """Text extraction only; Codex inspects visual pages and structures facts."""
    import zipfile
    from xml.etree import ElementTree
    source = Path(path)
    ext = source.suffix.lower()
    if source.stat().st_size > 50 * 1024 * 1024:
        raise SkillError("Brief exceeds the 50 MiB input limit")
    if ext in {".docx", ".pptx"}:
        with zipfile.ZipFile(source) as archive:
            names = (["word/document.xml"] if ext == ".docx" else sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.search(r"slide(\d+)", n)[1])))
            if sum(archive.getinfo(n).file_size for n in names) > 50 * 1024 * 1024:
                raise SkillError("Expanded brief exceeds 50 MiB")
            pages = []
            for name in names:
                root = ElementTree.fromstring(archive.read(name))
                paragraphs = ["".join(node.itertext()) for node in root.iter() if node.tag.endswith("}t")]
                pages.append({"source": name, "text": "\n".join(paragraphs)})
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise SkillError("PDF extraction requires pypdf") from None
        doc = PdfReader(source)
        pages = [{"page": i + 1, "text": page.extract_text() or ""} for i, page in enumerate(doc.pages)]
    elif ext in {".txt", ".md", ".csv", ".json"}:
        pages = [{"text": source.read_text(encoding="utf-8-sig")}]
    else:
        raise SkillError("Use TXT, MD, DOCX, PPTX or PDF. Inspect image briefs directly with Codex image tools.")
    result = {"source_name": source.name, "sha256": file_digest(source), "pages": pages,
              "needs_visual_review": ext in {".pdf", ".pptx", ".docx"},
              "empty_text": not any(p["text"].strip() for p in pages)}
    write_json(out, result)
    return result
