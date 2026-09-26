# Product-faithful storyboard workflow

Brand Partnership Pitch storyboards are **black-and-white hand-drawn sketches on white paper**, with clean lines, minimal shading and clear framing. No colored editorial illustrations, photoreal render, comic lettering, speech bubbles, subtitles, labels or logos drawn as typography. Brand/scene text belongs in the document. The pictured person must be the channel's observed host, not a fictional substitute.

## Cast and references

Inspect video frames before selecting them. Save clear face/upper-body frames under the job's `references/`; include frontal and angled views when available. For an ensemble, separate each visible person into a stable cast ID with role, source-based name, visible appearance and reference provenance. Never infer a name from facial recognition. Mark truly fictional requested actors `identity: "fictional"`; do not use that escape hatch for an inaccessible real creator. A faceless scene has `cast_ids: []` and should remain faceless.

Bind each inspected frame:

```bash
python "$SKILL/scripts/brand_pitch.py" bind-reference --script JOB/script.json --cast host --image references/host-front.jpg --source 'SOURCE_VIDEO_URL' --time 8.2
python "$SKILL/scripts/brand_pitch.py" image-plan --script JOB/script.json --out JOB/image-plan.json
```

The plan includes per-scene absolute `referenced_image_paths`, appearance instructions and source hashes. Inspect local input images with the image-viewing tool, then pass these exact paths to built-in imagegen in Codex. In other agents, upload the actual referenced image bytes through the configured tool/API's image-input mechanism; filenames in a text prompt are not image inputs. A JSON list of paths does not itself supply images to the model. Never drop the reference arguments. Follow the available imagegen skill when present. Use one generation per scene. See agent-compatibility.md for non-Codex execution. Use original host frames in every host scene; add an inspected prior storyboard as a continuity reference when useful, within tool limits. Prior drawings alone are not a substitute for the original host reference.

The prompt fixes monochrome style independently of the reference photograph's color. Scene-specific `image_prompt` should describe composition/action, not override this style. Keep wardrobe, hair, facial features, props and room layout consistent; only introduce a change when the script calls for one. A product close-up need not include the host. Do not put a second recurring actor in a shot that only names the first.

## Inspect and register

Inspect each output at useful size for: black-and-white sketch treatment; resemblance to the actual reference person; correct actors/action/framing/device orientation; consistent wardrobe and props; no text; no extra limbs/people or misleading product UI. If it fails, regenerate that scene with a targeted correction. Never fix a colored generation by silently applying a grayscale filter: the line-art medium and composition matter too.

Save an actual inspection record, for example:

```json
{"black_white":true,"identity_match":true,"no_text":true,"action_match":true,"notes":"Matched short hair and face outline to reference at 8.2s; same plain shirt; monochrome lines, no lettering; phone held vertically as scripted."}
```

Then copy the generated output into `images/` and register:

```bash
python "$SKILL/scripts/brand_pitch.py" register-image --script JOB/script.json --variant v1 --scene s1 --image images/v1-s1.png --qa JOB/analysis/v1-s1-image-qa.json
```

Set `storyboard_contract: "brand-pitch-bw-v1"` in new jobs. Registration rejects obvious color and requires the inspection record. This pixel test cannot verify resemblance, absence of text, or drawing quality: those remain visual review tasks. Cast reference files and generated files are hashed. Changing a referenced face, relevant cast description, visual, style, aspect, on-screen cue or prompt invalidates affected scenes. Dialogue-only edits retain images unless the depicted action also changes.

Full image coverage applies to the selected variation. Generate another complete variation when the user selects it, with the same cast references. Keep completed images on retry. Never label a text-only variant as illustrated.
