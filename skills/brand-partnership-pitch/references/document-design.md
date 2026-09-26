# Script document design

Deliver editable DOCX and a PDF rendered from that same DOCX. The bundled editorial theme uses A4 portrait, generous margins, restrained indigo labels and black body text, large section titles and scene panels. It deliberately avoids screenshotting text into images.

Default sequence: title and creative overview; goal/audience/confirmed requirements; complete script alternatives; scene panels with time range, visual, dialogue, screen text and production notes; shoot checklist; brief requirements review; concise source appendix. Keep analysis internals in the job's analysis directory.

The helper uses paired editable Visual/Audio cells with storyboard images, aiming for two short scenes per page. Long dialogue may flow across pages. Shoot preparation, reviewer notes, requirements and evidence occupy the final section. Inspect pagination for each actual script; do not shrink or omit text to force a page count. Adapt long-form scenes into sensible beat-sized units when needed.

The default theme is `assets/theme.json`. Copy it into the job to change colors, fonts, page dimensions or body size. Default Latin is Georgia and CJK is Noto Sans CJK SC. The package includes the unmodified OFL-licensed CJK font and a process-local fontconfig setup; it does not install an OS font. Check font substitution for other languages and platforms. DOCX editors outside this renderer may need the supplied font installed or a compatible local substitute. Do not distribute a commercial font from the user's machine.

```bash
python "$SKILL/scripts/brand_pitch.py" render --script "$JOB/script-recommended.json" --out "$JOB/exports/v1" --soffice /verified/path/to/soffice
```

In Codex, use the bundled LibreOffice path returned by dependency discovery. The command's explicit path prevents silently launching a desktop installation. Standalone users can provide their own verified headless LibreOffice executable. Poppler's `pdftoppm` must be on PATH. Each export uses a unique temporary LibreOffice profile and refuses to overwrite earlier deliveries.

If the documents skill exists, use its `render_docx.py` as the canonical additional DOCX-to-PNG check, with the bundled runtime. Set that subprocess's `FONTCONFIG_FILE` to the export's absolute `fontconfig.conf` path so it uses the same packaged CJK font. Keep this machine-specific QA configuration private with the job. Otherwise the packaged PDF-to-PNG path provides a portable inspection set. Review the final render after any DOCX change, not earlier PNGs. `export.json` hashes files and page PNGs, and stores pending/passed visual QA. The renderer also verifies that every dialogue line is extractable from the PDF; this catches missing text but does not replace inspecting pixels.

`--docx-only` is useful when PDF tooling is absent but does not constitute complete DOCX/PDF delivery. `--allow-missing-images` supports deliberately text-only alternatives and reported image-tool failures. It must not hide missing image output.

Keep headings with subsequent text, retain dialogue as paragraphs, preserve image aspect ratio, and check that production notes do not become isolated blank-looking pages. Page count follows readable content rather than a fixed marketing promise.

The same render also creates `script.html` (self-contained images, Time/Visual/Audio table, brief and review notes, no external tracking) and `script.txt` for copying. These are local files, not hosted share links. HTML should be opened and checked at desktop and narrow widths; preserve all dialogue as selectable text.
