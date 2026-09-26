"""Editable DOCX + matching PDF + inspectable page PNGs. No browser runtime."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata
from xml.sax.saxutils import escape

from common import SkillError, file_digest, local_asset, read_json, run, write_json
from script_data import validate


def render(script_path, out, *, theme_path=None, docx_only=False, soffice=None, allow_missing_images=False):
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from PIL import Image

    script_path, out = Path(script_path).resolve(), Path(out).resolve()
    script = read_json(script_path)
    report = validate(script, script_path.parent, require_images=not allow_missing_images)
    if not report["valid"]:
        raise SkillError("Script validation failed: " + "; ".join(report["errors"]))
    if out.exists():
        raise SkillError("Export directory already exists. Use a new revision directory.")
    theme = read_json(theme_path or Path(__file__).resolve().parent.parent / "assets/theme.json")
    out.mkdir(parents=True)
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(theme["page_width_inches"]), Inches(theme["page_height_inches"])
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, attr, Inches(theme["margin_inches"]))
    width = theme["page_width_inches"] - 2 * theme["margin_inches"]
    for name in ("Normal", "Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "Caption"):
        style = doc.styles[name]
        style.font.name = theme["font"]
        rpr = style.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.append(fonts)
        fonts.set(qn("w:eastAsia"), theme["east_asia_font"])
        for attribute in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
            fonts.attrib.pop(qn("w:" + attribute), None)
        ppr = style.element.find(qn("w:pPr"))
        if ppr is not None:
            for tag in ("pBdr", "numPr"):
                for child in list(ppr.findall(qn("w:" + tag))):
                    ppr.remove(child)
        style.font.color.rgb = RGBColor.from_string(theme["ink"])
    normal = doc.styles["Normal"]
    normal.font.size = Pt(theme["body_size"])
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    doc.styles["Title"].font.size = Pt(34)
    doc.styles["Title"].font.bold = True
    doc.styles["Caption"].font.bold = False
    for name, size in (("Heading 1", 23), ("Heading 2", 16), ("Heading 3", 11)):
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].font.color.rgb = RGBColor.from_string(theme["accent"])
    doc.core_properties.title = script["title"]
    doc.core_properties.author = "Brand Partnership Pitch"
    doc.core_properties.subject = "Video production script"
    chinese = script["language"].lower().startswith("zh")
    labels = ({"overview": "创意概览", "brief": "创作目标", "recommended": "推荐方案", "visual": "画面与调度", "audio": "台词与声音", "onscreen": "屏幕文字", "notes": "拍摄备注", "production": "拍摄准备", "checks": "需求核对", "sources": "创作依据", "cast": "人物", "scene": "场景", "sample": "分镜示意", "missing": "分镜图未生成", "objective": "目标", "audience": "受众", "include": "必须包含", "avoid": "避免", "facts": "已确认信息"}
              if chinese else {"overview": "Creative overview", "brief": "The brief", "recommended": "Recommended", "visual": "Visual & direction", "audio": "Dialogue & sound", "onscreen": "On-screen text", "notes": "Production notes", "production": "Shoot checklist", "checks": "Requirements review", "sources": "Creative references", "cast": "Cast", "scene": "Scene", "sample": "Storyboard illustration", "missing": "Storyboard not generated", "objective": "Objective", "audience": "Audience", "include": "Must include", "avoid": "Must avoid", "facts": "Confirmed facts"})

    def para(text, style=None):
        return doc.add_paragraph(text, style)

    def tagged(label, content):
        if content:
            p = para("")
            p.add_run(label + "  ").bold = True
            p.add_run(content)
        return

    def tc(seconds):
        return f"{int(seconds // 60):02d}:{seconds % 60:04.1f}"

    p = para("BRAND PARTNERSHIP PITCH  /  SCRIPT DOCUMENT")
    p.runs[0].font.color.rgb = RGBColor.from_string(theme["accent"])
    p.runs[0].font.size = Pt(9)
    para(script["title"], "Title")
    para(f"{script['brief'].get('brand_name', '')} × {script['channel']['name']}  ·  {datetime.now().strftime('%Y-%m-%d')}".strip(" ×"), "Subtitle")
    para(script["summary"])
    para(labels["brief"], "Heading 2")
    brief = script["brief"]
    tagged(labels["objective"], brief["objective"])
    tagged(labels["audience"], brief["audience"])
    for key, label in (("tone", "语气 / Tone"), ("product_name", "产品 / Product"), ("usage_context", "使用场景 / Usage"), ("campaign_goal", "商业目标 / Goal")):
        tagged(label if chinese else label.split(" / ")[-1], brief.get(key, ""))
    tagged("可选形式" if chinese else "Acceptable formats", ", ".join(brief.get("acceptable_formats", [])))
    for key, label in (("must_include", "include"), ("must_avoid", "avoid"), ("facts", "facts")):
        if brief[key]:
            tagged(labels[label], " · ".join(brief[key]))
    para(labels["overview"], "Heading 2")
    for i, v in enumerate(script["variations"], 1):
        tagged(f"{i:02d}  {v['title']}" + (f"  /  {labels['recommended']}" if v["recommended"] else ""), v["angle"])
    for variant in script["variations"]:
        doc.add_page_break()
        para(variant["title"], "Heading 1")
        para(f"{variant['format']}  /  {variant['duration_seconds']:g}s  /  {variant['aspect_ratio']}", "Subtitle")
        para(variant["fit_reason"])
        review = variant.get("verification", {})
        if review.get("status") == "reviewed":
            tagged("REVIEW", f"Match {review['match_score']}/100 · Production {review['production_level']} · Brand safe: {review['brand_safe']}")

        if script.get("cast"):
            tagged(labels["cast"], " · ".join(c["name"] + (f" — {c['role']}" if c.get("role") else "") for c in script["cast"]))
        has_storyboards = any(s.get("image") for s in variant["scenes"])
        # Product AV view: paired Visual/Audio cells with editable text and embedded sketch.
        for i, scene in enumerate(variant["scenes"], 1):
            if has_storyboards and i > 1 and i % 2 == 1:
                doc.add_page_break()
            para(f"{labels['scene']} {i:02d}   {tc(scene['start'])} – {tc(scene['end'])}   {scene['title']}", "Heading 3")
            table = doc.add_table(rows=1, cols=2)
            table.autofit = False
            table.columns[0].width = Inches(width * .48)
            table.columns[1].width = Inches(width * .52)
            left, right = table.rows[0].cells
            left.width, right.width = Inches(width * .48), Inches(width * .52)
            for cell, label in ((left, labels['visual']), (right, labels['audio'])):
                cell.paragraphs[0].add_run(label).bold = True
                cell.paragraphs[0].paragraph_format.space_after = Pt(5)
            if scene.get('image'):
                asset = local_asset(script_path.parent, scene['image']['path'])
                with Image.open(asset) as im:
                    w, h = im.size
                p = left.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                drawing = p.add_run().add_picture(str(asset), width=Inches(min(width * .44, 2.3 * w / h)))
                drawing._inline.docPr.set('descr', scene['visual'])
            else:
                left.add_paragraph(labels['missing'], 'Caption')
            left.add_paragraph(scene['visual'])
            for line in scene['audio'].splitlines():
                right.add_paragraph(line)
            for key in ('onscreen_text', 'notes'):
                if scene[key]:
                    p = right.add_paragraph()
                    p.add_run(labels['onscreen' if key == 'onscreen_text' else 'notes'] + '  ').bold = True
                    p.add_run(scene[key])
            for cell in (left, right):
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(5)
                    p.paragraph_format.line_spacing = 1.08
                    for r in p.runs:
                        r.font.size = Pt(10)
        if has_storyboards:
            doc.add_page_break()
        para(labels["production"], "Heading 1")
        for item in variant["production"]:
            para(item, "List Bullet")
        if review.get("status") == "reviewed":
            para("Reviewer notes", "Heading 2")
            para(review['reviewer_notes'])
        para(labels["checks"], "Heading 2")
        for item in variant["requirements_check"]:
            para(item, "List Bullet")
    if script.get("evidence"):
        para(labels["sources"], "Heading 2")
        for item in script["evidence"]:
            tagged(item["id"], item["observation"])
            source = item["source"]
            if "time_seconds" in item:
                source += f"  /  {tc(item['time_seconds'])}"
            para(source, "Caption")
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run("BRAND PARTNERSHIP PITCH  /  ").font.size = Pt(8)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    path = out / "script.docx"
    doc.save(path)
    from preview import export_preview
    export_preview(script, script_path.parent, out)
    manifest = {"script_sha256": file_digest(script_path), "created_at": datetime.now(timezone.utc).isoformat(),
                "files": {"docx": {"path": "script.docx", "sha256": file_digest(path)},
                          "html": {"path": "script.html", "sha256": file_digest(out / "script.html")},
                          "text": {"path": "script.txt", "sha256": file_digest(out / "script.txt")}},
                "validation": report, "visual_qa": "pending", "pages": []}
    write_json(out / "export.json", manifest)
    if docx_only:
        return manifest
    if not soffice:
        raise SkillError("DOCX created. PDF requires --soffice pointing to a verified LibreOffice executable; in Codex use its bundled runtime")
    with tempfile.TemporaryDirectory(prefix="brand-pitch-lo-") as profile:
        # Load distributable CJK font without installing it into the user's OS.
        fonts_dir = Path(__file__).resolve().parent.parent / "assets/fonts"
        config = out / "fontconfig.conf"
        font_dirs = [fonts_dir, Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
                     Path("/System/Library/Fonts"), Path("/Library/Fonts")]
        config.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>' +
                          ''.join(f'<dir>{escape(str(p))}</dir>' for p in font_dirs if p.is_dir()) +
                          f'<cachedir>{escape(str(out / ".font-cache"))}</cachedir></fontconfig>', encoding="utf-8")
        child_env = {**os.environ, "FONTCONFIG_FILE": str(config)}
        run([str(Path(soffice).resolve()), "-env:UserInstallation=" + Path(profile).as_uri(), "--headless",
             "--convert-to", "pdf", "--outdir", out, path], timeout=180, env=child_env)
    pdf = out / "script.pdf"
    if not pdf.is_file() or pdf.stat().st_size == 0:
        raise SkillError("LibreOffice did not produce a PDF; DOCX retained, export not complete")
    from pypdf import PdfReader
    reader = PdfReader(pdf)
    normalize_text = lambda s: re.sub(r"\s+", "", unicodedata.normalize("NFKC", s))
    extracted = normalize_text("\n".join(page.extract_text() or "" for page in reader.pages))
    expected_lines = [line for v in script["variations"] for s in v["scenes"] for line in s["audio"].splitlines() if line.strip()]
    missing = [line for line in expected_lines if normalize_text(line) not in extracted]
    if missing:
        raise SkillError("PDF text verification failed: dialogue is missing or unreadable. Check fonts/layout before delivery; DOCX and PDF retained for diagnosis.")
    manifest["pdf_text_check"] = {"dialogue_lines": len(expected_lines), "all_present": True}
    previews = out / "pages"
    previews.mkdir()
    page_count = len(reader.pages)
    run(["pdftoppm", "-r", "100", "-png", pdf, previews / "page"], timeout=180)
    rendered = sorted(previews.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
    if len(rendered) != page_count:
        raise SkillError("PDF page render is incomplete")
    for target in rendered:
        manifest["pages"].append({"path": str(target.relative_to(out)), "sha256": file_digest(target)})
    manifest["files"]["pdf"] = {"path": "script.pdf", "sha256": file_digest(pdf)}
    write_json(out / "export.json", manifest)
    return manifest


def record_qa(export_dir, pages, notes):
    root = Path(export_dir).resolve()
    manifest = read_json(root / "export.json")
    expected = set(range(1, len(manifest["pages"]) + 1))
    if not expected or set(pages) != expected:
        raise SkillError("Record QA only after inspecting ALL exported page PNGs; supply each page number")
    for item in list(manifest["files"].values()) + manifest["pages"]:
        if file_digest(local_asset(root, item["path"])) != item["sha256"]:
            raise SkillError("An export or preview changed after rendering; render and review again")
    if not notes.strip():
        raise SkillError("Record concrete visual observations, not an empty approval")
    manifest["visual_qa"] = {"status": "passed", "pages_reviewed": sorted(expected), "notes": notes,
                             "recorded_at": datetime.now(timezone.utc).isoformat()}
    write_json(root / "export.json", manifest)
    return manifest["visual_qa"]
