# Setup and operations

All commands are local Python helpers; they do not run an LLM. `SKILL` is the installed skill directory and `JOB` is a separate output directory. Quote paths. Run `--help` on any subcommand for all options.

## Dependencies

- Python 3.10+, python-docx, Pillow, pypdf (listed in `requirements.txt`).
- FFmpeg/ffprobe for video and audio; headless LibreOffice and Poppler for matching DOCX/PDF/page PNGs.
- yt-dlp for YouTube downloads and optional other supported video URLs.
- faster-whisper only when local speech recognition is needed. Its first use downloads model weights; it can run offline after weights are cached. The CPU/int8 default is portable, not a promise of real-time performance.
- Codex image viewing and built-in imagegen for understanding frames and creating illustrations. These are tool capabilities, not Python packages.

In Codex first discover bundled workspace runtimes and use them if available. For standalone installation, create an isolated Python environment and install the requirement files with the Python environment manager of your choice. On this repository, preserve its pnpm-only JavaScript workflow; no root Node dependency or lockfile changes are necessary. OS executables are installed separately, not silently by the skill.

```bash
python "$SKILL/scripts/brand_pitch.py" doctor
python "$SKILL/scripts/brand_pitch.py" init --channel https://www.youtube.com/@example --brief requirement.txt --out "$JOB"
```

Use `--channel local` when supplying reference files. A bare handle needs `--platform`; platform is never guessed. Single-post/share URLs should be resolved to their creator profile before channel analysis. Missing credentials must not be read from unrelated projects; ask the user to configure an environment variable outside chat.

## Acquisition

Apify is the default public-channel acquisition backend. Read `APIFY_API_TOKEN` from the environment. Each new Actor run can charge the user's Apify account. Set an appropriate count and per-run cap within the user's authorized scope. `maxTotalChargeUsd` is an Apify run option; it is not a universal total-account cap and its enforcement depends on the Actor/pricing model. Do not assert an exact dollar cost before checking the actual Actor pricing.

```bash
python "$SKILL/scripts/brand_pitch.py" fetch --channel https://www.youtube.com/@example --format mixed --limit 15 --max-charge 1 --state "$JOB/sources/channel-run.json" --out "$JOB/sources/channel.json"
python "$SKILL/scripts/brand_pitch.py" select --input "$JOB/sources/channel.json" --count 5 --keywords 'coffee brewing' --out "$JOB/sources/selected.json"
```

Adapters: `clockworks~tiktok-scraper`, `streamers~youtube-scraper`, `apify~instagram-scraper`. Their schemas can change. The helper normalizes common current fields and fails visibly on empty/unrecognized data. Keep actual live verification separate from offline adapter tests. Instagram's Reels records may contain only a partial profile; do not invent follower count or biography.

Reuse an existing provider JSON export:

```bash
python "$SKILL/scripts/brand_pitch.py" normalize --input apify-dataset.json --platform instagram --channel https://www.instagram.com/example/ --out "$JOB/sources/channel.json"
```

Download only selected videos:

```bash
# Instagram/other provider-supplied public HTTPS media URL. Keep signed URLs out of public logs.
python "$SKILL/scripts/brand_pitch.py" download --backend https --url "$MEDIA_URL" --out "$JOB/media/reference.mp4"
# YouTube: yt-dlp downloads the selected video, available subtitles and metadata.
python "$SKILL/scripts/brand_pitch.py" download --backend yt-dlp --url https://www.youtube.com/watch?v=VIDEO_ID --out "$JOB/media/youtube-1"
# TikTok: paid download add-on, independently resumable and bounded.
python "$SKILL/scripts/brand_pitch.py" download --backend apify-tiktok --url https://www.tiktok.com/@example/video/123456789 --state "$JOB/sources/video-1-run.json" --out "$JOB/media/tiktok-1.mp4"
```

yt-dlp ignores user configuration and does not import cookies automatically. If a video requires authentication or cannot be downloaded, ask for an accessible/local reference or an explicitly authorized authentication workflow; do not search the user's browser profile for cookies. Successful metadata acquisition is not proof the media is downloadable. Signed media URLs can expire; refreshing media metadata may require a new explicitly bounded run.

HTTPS downloads reject obvious private/local addresses and recheck redirects; this is a local input guard, not a hardened multi-tenant network sandbox. Do not deploy this CLI as an untrusted remote URL-fetching server.

## Media and transcripts

```bash
python "$SKILL/scripts/brand_pitch.py" prepare --video "$JOB/media/reference.mp4" --out "$JOB/media/reference-analysis" --interval 5 --max-frames 80
python "$SKILL/scripts/brand_pitch.py" transcribe --backend subtitles --subtitles captions.srt --out "$JOB/media/transcript.json"
python "$SKILL/scripts/brand_pitch.py" transcribe --backend local --audio "$JOB/media/reference-analysis/audio.wav" --model small --out "$JOB/media/transcript-local.json"
```

For long videos, initial frames span the full requested range rather than only its beginning. Inspect contact sheets, then run `prepare --start 120 --end 150` into a new directory for uncertain sequences. If transcribing the extracted interval, pass `--offset 120`; stored transcript timestamps then refer to original source time. The command extracts all audio in the chosen range. A silent/no-audio video is valid and needs visual-only analysis, not a fabricated transcript.

ElevenLabs is opt-in and uses `ELEVENLABS_API_KEY`:

```bash
python "$SKILL/scripts/brand_pitch.py" transcribe --backend elevenlabs --audio "$JOB/media/reference-analysis/audio.wav" --model scribe_v2 --diarize --out "$JOB/media/transcript-cloud.json"
```

This uploads audio to ElevenLabs and may charge the account. It does not analyze visuals. Local transcription does not provide diarization; match voices/roles manually when grounded, or use the explicitly selected cloud backend. A transcript is not proof of intonation or emotion. Split audio over 100 MiB before cloud upload and preserve offsets.

## Briefs, scripts and export

```bash
python "$SKILL/scripts/brand_pitch.py" brief --input brief.pdf --out "$JOB/analysis/brief-text.json"
python "$SKILL/scripts/brand_pitch.py" validate --script "$JOB/script.json"
python "$SKILL/scripts/brand_pitch.py" image-plan --script "$JOB/script.json" --out "$JOB/analysis/image-plan.json"
# Codex uses built-in imagegen, inspects/copies outputs, then registers each image.
python "$SKILL/scripts/brand_pitch.py" register-image --script "$JOB/script.json" --variant v1 --scene s1 --image images/v1-s1.png
python "$SKILL/scripts/brand_pitch.py" validate --script "$JOB/script.json" --require-images
python "$SKILL/scripts/brand_pitch.py" render --script "$JOB/script.json" --out "$JOB/exports/v1" --soffice /verified/path/to/soffice
# After viewing EVERY page, use its actual page numbers and concrete observations:
python "$SKILL/scripts/brand_pitch.py" qa --export "$JOB/exports/v1" --pages 1 2 3 --notes 'Reviewed all three pages: readable glyphs, intact panels, no clipping or orphaned labels.'
```

The example page count is illustrative; read the actual export manifest. `render --docx-only` is a partial output when PDF tooling is unavailable. `--allow-missing-images` explicitly produces unillustrated scenes rather than silently omitting images.

## Provider references

Reviewed during implementation, 2026-09-22; recheck schemas when a live adapter fails:

- [Apify Actor runs](https://docs.apify.com/api/v2/actors-runs-post)
- [TikTok scraper](https://apify.com/clockworks/tiktok-scraper)
- [YouTube input](https://apify.com/streamers/youtube-scraper/input-schema)
- [Instagram input](https://apify.com/apify/instagram-scraper/input-schema)
- [ElevenLabs transcription](https://elevenlabs.io/docs/api-reference/speech-to-text/convert)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

## Product-specific commands

- `bind-reference`: register an inspected actual host/cast frame and source timestamp before `image-plan`; see storyboards.md.
- `register-image --qa`: enforce monochrome output and record an actual identity/action/text inspection for `brand-pitch-bw-v1` jobs.
- `review`: aggregate real recorded Codex review passes, rank alternatives, track score freshness; see quality-review.md.
- `revise`: enforce approved visual/audio locks and save snapshots/feedback; `restore`: preserve current state and return to a snapshot; see revisions.md.
- `render`: also produces self-contained AV-table HTML and plain text. HTML is local until a separately authorized host publishes it.

Use Python 3.10+ for yt-dlp too; older Python can silently limit pip to an obsolete downloader version. If YouTube changes its download protocol or blocks the environment, retain metadata and report missing video evidence. Use another accessible source of the same clip or user-provided local video; do not claim metadata alone constitutes visual analysis. Never import browser cookies automatically.

Compact single-column Word/PDF is the default. The same export writes `production-notes.md` with the complete brief, review, checklist and sources. Add `--include-notes` to `render` for an all-in-one document.
