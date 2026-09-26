"""Portable, single-column script preview and complete production notes."""
from pathlib import Path
from html import escape
import base64
from common import local_asset


def production_sections(script):
    """Keep client-readable supporting information without copying private asset paths."""
    zh = script['language'].lower().startswith('zh')
    sections = []
    brief = []
    for key, value in script['brief'].items():
        if value:
            text = '\n'.join(str(x) for x in value) if isinstance(value, list) else str(value)
            brief.append((key.replace('_', ' ').title(), text))
    sections.append(('完整需求' if zh else 'Full brief', brief))
    if script.get('cast'):
        sections.append(('人物' if zh else 'Cast', [(c['name'], c.get('role', '')) for c in script['cast']]))
    for v in script['variations']:
        entries = [('Angle', v['angle']), ('Creator fit', v['fit_reason'])]
        review = v.get('verification', {})
        if review.get('status') == 'reviewed':
            entries.extend([('Review', f"Match {review['match_score']}/100 · Production {review['production_level']} · Brand safe: {review['brand_safe']}"), ('Reviewer notes', review['reviewer_notes'])])
        entries.extend(('Shoot checklist', item) for item in v['production'])
        entries.extend(('Requirements', item) for item in v['requirements_check'])
        entries.extend((f"Scene {i:02d} · {s['title']}", s['notes']) for i, s in enumerate(v['scenes'], 1) if s['notes'])
        sections.append((v['title'], entries))
    if script.get('evidence'):
        sections.append(('来源' if zh else 'Sources', [(e['id'], e['observation'] + '\n' + e['source'] + (f" · {e['time_seconds']:g}s" if 'time_seconds' in e else '')) for e in script['evidence']]))
    return sections


def export_preview(script, base, out):
    out = Path(out)
    esc = lambda value: escape(str(value)).replace('\n', '<br>')
    zh = script['language'].lower().startswith('zh')
    labels = {'visual': '画面', 'audio': '台词与声音', 'screen': '屏幕文字', 'note': '备注', 'scene': '场景', 'missing': '分镜图未生成', 'support': '完整需求、制作备忘与来源'} if zh else {'visual': 'Visual', 'audio': 'Audio', 'screen': 'On screen', 'note': 'Note', 'scene': 'Scene', 'missing': 'Storyboard not generated', 'support': 'Full brief, production notes and sources'}
    brief = script['brief']
    brand_creator = f"{brief.get('brand_name', '')} × {script['channel']['name']}".strip(' ×')
    text = [script['title'], brand_creator, script['summary']]
    blocks = [f'<header><h1>{esc(script["title"])}</h1><p class="meta">{esc(brand_creator)}</p><p class="context">{esc(script["summary"])}</p><p>{esc(brief["objective"])}</p></header>']
    if len(script['variations']) > 1:
        blocks.append('<nav aria-label="Scripts">' + ' '.join(f'<a href="#{esc(v["id"])}">{esc(v["title"])}</a>' for v in script['variations']) + '</nav>')
    for v in script['variations']:
        text.extend(['\n' + v['title'], v['angle'], v['fit_reason']])
        blocks.append(f'<section id="{esc(v["id"])}"><h2>{esc(v["title"])}</h2><p class="meta">{v["duration_seconds"]:g}s · {esc(v["aspect_ratio"])} · {esc(v["format"])}</p>')
        for i, s in enumerate(v['scenes'], 1):
            time = f"{s['start']:g}–{s['end']:g}s"
            if s.get('image'):
                asset = local_asset(base, s['image']['path'])
                from PIL import Image
                with Image.open(asset) as im:
                    mime = Image.MIME.get(im.format, 'image/png')
                    w, h = im.size
                picture = f'<img alt="{esc(s["visual"])}" width="{w}" height="{h}" src="data:{mime};base64,{base64.b64encode(asset.read_bytes()).decode()}">'
            else:
                picture = f'<p class="meta">{labels["missing"]}</p>'
            blocks.append(f'<article><h3>{labels["scene"]} {i:02d} · {esc(s["title"])}</h3><p class="meta">{time}</p>{picture}<p><strong>{labels["visual"]}</strong><br>{esc(s["visual"])}</p><div class="audio"><strong>{labels["audio"]}</strong>')
            for line in s['audio'].splitlines():
                speaker, colon, words = line.partition(':')
                if not colon:
                    speaker, colon, words = line.partition('：')
                dialogue = f'<strong>{esc(speaker + colon)}</strong>{esc(words)}' if colon and len(speaker) <= 40 else esc(line)
                blocks.append(f'<p>{dialogue}</p>')
            blocks.append('</div>')
            for key, label in (('onscreen_text', 'screen'), ('notes', 'note')):
                if s[key]:
                    blocks.append(f'<p class="note"><strong>{labels[label]}</strong> {esc(s[key])}</p>')
            blocks.append('</article>')
            text.extend([f'\n[{time}] {s["title"]}', 'Visual: ' + s['visual'], 'Audio: ' + s['audio'], 'On screen: ' + s['onscreen_text'], 'Notes: ' + s['notes']])
        blocks.append('</section>')
    notes = ['# ' + labels['support'], '', script['title'], '']
    blocks.append(f'<details><summary>{labels["support"]}</summary>')
    for title, entries in production_sections(script):
        blocks.append(f'<h2>{esc(title)}</h2>')
        notes.extend(['## ' + title, ''])
        text.extend(['\n' + title])
        for label, content in entries:
            blocks.append(f'<p><strong>{esc(label)}</strong><br>{esc(content)}</p>')
            notes.extend([f'**{label}**', content, ''])
            text.append(f'{label}: {content}')
    blocks.append('</details>')
    css = '''*{box-sizing:border-box}body{max-width:640px;margin:32px auto;padding:0 24px;color:#1a1a1a;background:#fff;font:17px/1.5 Arial,"Noto Sans CJK SC",sans-serif;overflow-wrap:anywhere}h1{font-size:28px;line-height:1.2;margin:0 0 12px}h2{font-size:22px;line-height:1.3;margin:28px 0 8px}h3{font-size:18px;margin:0 0 4px}p{margin:8px 0 14px}.meta,.context,.note{color:#484848}.meta{font-size:14px;margin:4px 0 12px}.context,.note{font-size:15px}article{padding:24px 0;border-bottom:1px solid #ddd}img{display:block;width:auto;height:auto;max-width:100%;max-height:360px;margin:12px auto 20px}nav{display:flex;flex-wrap:wrap;gap:14px}a{color:#3730a3}details{margin:28px 0}summary{cursor:pointer;font-weight:bold}.audio p{margin:6px 0 10px}@media(max-width:420px){body{margin:20px auto;padding:0 18px}h1{font-size:25px}img{max-height:330px}}@media print{body{margin:0}nav{display:none}h3{break-after:avoid}img{break-inside:avoid}}'''
    (out / 'script.html').write_text('<!doctype html><html lang="' + ('zh-CN' if zh else 'en') + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(script['title']) + '</title><style>' + css + '</style></head><body>' + ''.join(blocks) + '</body></html>', encoding='utf-8')
    (out / 'script.txt').write_text('\n'.join(text) + '\n', encoding='utf-8')
    (out / 'production-notes.md').write_text('\n'.join(notes).rstrip() + '\n', encoding='utf-8')
