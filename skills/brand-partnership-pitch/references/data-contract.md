# Data contract

`script.json` is the editable source of truth. All images are relative paths inside its directory; no external signed URLs in final document data. See `examples/script.json` for a complete fictional example. Helpers use schema version 1.

Top-level fields:

| Field | Value |
| --- | --- |
| schema_version | `1` |
| title, language, summary, visual_style | Nonempty strings; language such as `en` or `zh-CN` |
| channel | `{name, platform, url?}`; platform youtube/tiktok/instagram/local |
| brief | `{kind, objective, audience, facts:[], must_include:[], must_avoid:[]}` |
| cast | Array of `{id, name, appearance, role?}`; empty for faceless content |
| evidence | Array of `{id, source, observation, time_seconds?}` |
| variations | One or more complete alternatives; exactly one recommended |

`brief.kind` is sponsored, organic, tutorial, drama or other. Keep facts as sourced statements, not speculation. Track source details in the evidence and analysis files.

Each variation:

```json
{
  "id": "v1",
  "title": "A concrete creative premise",
  "angle": "The concept and chosen format",
  "hook": "The actual opening line/action",
  "format": "Dedicated tutorial",
  "fit_reason": "Why this fits the observed creator and brief",
  "recommended": true,
  "duration_seconds": 45,
  "aspect_ratio": "9:16",
  "scenes": [],
  "production": ["One kitchen, one host, a tabletop tripod"],
  "requirements_check": ["The required demonstration appears in scene s2"]
}
```

Supported aspect ratios: `9:16`, `16:9`, `1:1`, `4:5`.

Each scene:

```json
{
  "id": "s1",
  "title": "The opening problem",
  "start": 0,
  "end": 8,
  "visual": "Medium shot. The host puts two mugs on the counter and points to the smaller one.",
  "audio": "HOST: Same coffee. Different cup. Why does one feel so much stronger?",
  "onscreen_text": "Same coffee. Different cup.",
  "notes": "Leave a beat after the question.",
  "cast_ids": ["host"],
  "evidence_ids": ["e1"],
  "image_prompt": "One clean storyboard panel: host at the counter, two mugs, no text."
}
```

IDs are unique within their scope, use letters/digits/hyphen/underscore and remain stable during revisions. Every scene starts at the previous scene's end; first starts at zero and final end matches `duration_seconds`. Audio may be a silent direction such as `[No dialogue. Room tone.]`. Cast/evidence arrays can be empty when truly inapplicable; references must otherwise resolve.

`register-image` adds an `image` object with `path`, `sha256` and `visual_fingerprint`. Do not hand-forge these fields. The fingerprint links cast/style/aspect/action/on-screen text/prompt to the image. Source image bytes are also hashed. Files cannot escape the job directory, including via symlinks.

## Analysis files

Keep detailed creator/brief analysis separate from the client document. Recommended shape for channel observations:

```json
{
  "claim": "Opens demonstrations with a side-by-side comparison",
  "classification": "observed",
  "sources": [{"video_id": "source-1", "time_seconds": 2.5}],
  "confidence": "supported by 3 of 4 sampled videos",
  "implication": "A side-by-side hook is a suitable starting point"
}
```

`media.json` records source hashes, sampled frame timestamps and audio offsets. Transcript segments carry absolute source seconds after `--offset`; do not add the offset a second time. Subtitle timestamps usually already refer to the original video, so normally import with offset zero.

For separate exports, write a sibling JSON containing the desired subset of variations; set exactly one recommended in that subset. Keep its directory the same as `script.json` so image-relative paths remain valid. Preserve the complete master file.

## Product fidelity fields (new jobs)

Set `storyboard_contract: "brand-pitch-bw-v1"`. `visual_style` is black-and-white hand-drawn line art, minimal shading, no image text. New observed cast entries use `identity: "observed"`; bind actual inspected frames with `bind-reference`. `references` entries contain `{path, sha256, source, time_seconds}`. Only intentionally fictional actors use `identity: "fictional"`. Paths are local job assets. The image plan refuses observed people with no reference frames.

For sponsored work, extend `brief` with `brand_name`, `product_name`, `key_messages:[]`, `product_features:[]`, `tone`, `deliverables:[]`, `timeline`, `budget`, `acceptable_formats:[]` (integration/dedicated/ad-only or actual brief terms), `usage_context`, and `campaign_goal`. Preserve unspecified values as empty and explain important uncertainty; don't fabricate product detail. These fields feed script choices and the exported brief.

`verification` is written by `review`, contains style/brand/match scores, Low/Medium/High production effort, brand-safe boolean, notes, review provenance and script fingerprint. `status: "needs_review"` replaces outdated scores on revision. See quality-review.md for the actual review input.
