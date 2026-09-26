# Script document design

Deliver a compact, editable DOCX and a PDF rendered from that same DOCX. Default to a narrow 5.5 × 8.5 inch portrait page with 0.38 inch margins, 12 pt sans-serif body text and a single reading column. This improves fit-width reading on a phone; actual Word mobile reflow depends on the reader's app. Never shrink dialogue to fit a target page count.

Lead with a short subject title, creator/brand and one or two sentences of essential context. Retain mandatory concept/disclosure language. Keep detailed background out of the summary. Start the first scene on the first page when it fits; do not create a separate cover or overview page. Each scene reads in order: scene number/title, time range, inline storyboard, Visual, Audio, on-screen copy and concise scene notes. Keep dialogue selectable and editable, with speaker names in bold. Avoid side-by-side AV tables and floating text boxes.

Preserve every scene's complete visual direction, dialogue, screen text and notes. Group short scenes so their image and dialogue stay together; let long scenes flow naturally instead of shrinking text or forcing an entire long scene onto one page. Compress RGB/grayscale images only in the embedded DOCX copy when this reduces file size; preserve original resolution and retain the original source files. Preserve image aspect ratios, and adapt image size through the theme. Page count follows readable content, not a promise of fewer pages.

Full brief fields, cast, creative rationale, scores/reviewer provenance, production checklist, requirement checks and timestamped source references are exported to `production-notes.md`. They also remain in the complete copyable `script.txt` and a collapsed supporting-notes section of `script.html`. Keep practical scene-specific direction next to its scene. Use `--include-notes` when the user wants the full supporting material appended to the Word/PDF itself. Deliver the supporting notes with a compact script so context is available without filling the main reading flow.

The default theme is `assets/theme.json`. Copy it into the job to customize fonts, page dimensions, margins, body size or `image_max_height_inches`. A print-oriented A4/Letter page can use the same single-column structure. Default Latin is Arial and CJK is the included OFL-licensed Noto Sans CJK SC. Fonts are made available to the rendering subprocess without installation into the OS. Other DOCX editors may substitute fonts; check the actual target reader when available. Never distribute proprietary fonts from the user's machine.

```bash
python "$SKILL/scripts/brand_pitch.py" render --script "$JOB/script-recommended.json" --out "$JOB/exports/v2" --soffice /verified/path/to/soffice
# Optional all-in-one document:
python "$SKILL/scripts/brand_pitch.py" render --script "$JOB/script-recommended.json" --out "$JOB/exports/v2-full" --include-notes --soffice /verified/path/to/soffice
```

In Codex, resolve bundled LibreOffice through workspace dependencies; never silently use the user's desktop installation. Standalone users can supply their own verified headless executable. Poppler's `pdftoppm` must be on PATH. Each export uses an isolated temporary LibreOffice profile and refuses to overwrite earlier deliveries.

Use the documents skill's `render_docx.py` as the canonical additional render check when available. Set its subprocess `FONTCONFIG_FILE` to the export's absolute `fontconfig.conf`. Keep that machine-specific configuration private. Inspect every final page, including the first page and long-scene continuations; fix clipping, orphaned labels, missing glyphs and avoidable blank cover pages. Also inspect fit-width readability at roughly 390 px. A desktop render is not proof of a physical phone's Word app behavior.

`export.json` records hashes, layout settings, page PNGs and pending/passed visual QA. Every dialogue line must be extractable from the PDF, but text verification does not replace visual review. Record inspection with `qa` only after checking all pages. `--docx-only` and `--allow-missing-images` are explicit degraded export modes, never a fully verified illustrated delivery.

The self-contained HTML uses the same single-column scene order, readable mobile typography and embedded images with no external tracking. Open it at desktop and narrow widths and verify there is no horizontal scrolling. It is a local file, not a hosted share link.
