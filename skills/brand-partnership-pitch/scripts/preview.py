"""Portable offline script preview and copyable text; never publishes a link."""
from pathlib import Path
from html import escape
import base64
from common import local_asset


def export_preview(script, base, out):
    out = Path(out)
    esc = lambda value: escape(str(value)).replace('\n', '<br>')
    brief = script['brief']
    brand_creator = f"{brief.get('brand_name', '')} × {script['channel']['name']}".strip(' ×')
    text = [script['title'], brand_creator, script['summary'], '\nTHE BRIEF']
    metadata = [(key.replace('_', ' ').title(), brief.get(key)) for key in ('objective', 'audience', 'tone', 'acceptable_formats', 'usage_context', 'campaign_goal', 'product_name', 'key_messages', 'product_features', 'must_include', 'must_avoid')]
    blocks = [f'<header><small>BRAND PARTNERSHIP PITCH / SCRIPT DOCUMENT</small><h1>{esc(script["title"])}</h1><p>{esc(brand_creator)}</p><p>{esc(script["summary"])}</p></header><h2>The Brief</h2><dl>']
    for label, value in metadata:
        if value:
            value = ', '.join(value) if isinstance(value, list) else value
            text.append(f'{label}: {value}')
            blocks.append(f'<dt>{esc(label)}</dt><dd>{esc(value)}</dd>')
    blocks.append('</dl><nav>' + ' '.join(f'<a href="#{esc(v["id"])}">{esc(v["title"])}</a>' for v in script['variations']) + '</nav>')
    for v in script['variations']:
        text.extend(['\n' + v['title'], v['angle'], v['fit_reason']])
        blocks.append(f'<section id="{esc(v["id"])}"><h2>{esc(v["title"])}{" · Recommended" if v["recommended"] else ""}</h2><p>{esc(v["angle"])}</p>')
        review = v.get('verification', {})
        if review.get('status') == 'reviewed':
            info = f"Match {review['match_score']}/100 · Production {review['production_level']} · Brand safe: {review['brand_safe']}"
            blocks.append(f'<aside>{esc(info)}<p>{esc(review["reviewer_notes"])}</p></aside>')
            text.extend([info, review['reviewer_notes']])
        blocks.append('<table><thead><tr><th>Time</th><th>Visual</th><th>Audio</th></tr></thead><tbody>')
        for s in v['scenes']:
            time = f"{s['start']:g}–{s['end']:g}s"
            image = ''
            if s.get('image'):
                asset = local_asset(base, s['image']['path'])
                from PIL import Image
                with Image.open(asset) as im:
                    mime = Image.MIME.get(im.format, 'image/png')
                image = f'<img alt="{esc(s["title"])}" src="data:{mime};base64,{base64.b64encode(asset.read_bytes()).decode()}">'
            else:
                image = '<small>Storyboard not generated</small>'
            note = ('On screen: ' + esc(s['onscreen_text']) + '<br>' if s['onscreen_text'] else '') + esc(s['notes'])
            blocks.append(f'<tr><td>{time}<br><strong>{esc(s["title"])}</strong></td><td>{image}<p>{esc(s["visual"])}</p></td><td>{esc(s["audio"])}<p class="note">{note}</p></td></tr>')
            text.extend([f'\n[{time}] {s["title"]}', 'Visual: ' + s['visual'], 'Audio: ' + s['audio'], 'On screen: ' + s['onscreen_text'], 'Notes: ' + s['notes']])
        blocks.append('</tbody></table><h3>Production</h3><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in v['production']) + '</ul><h3>Requirements</h3><ul>' + ''.join(f'<li>{esc(x)}</li>' for x in v['requirements_check']) + '</ul></section>')
    css = 'body{max-width:1100px;margin:48px auto;padding:0 28px;color:#202020;background:white;font:17px/1.6 Georgia,serif}small,nav,th,aside{font-family:Arial,sans-serif}header{border-bottom:1px solid #ddd;padding-bottom:24px}h1{font-size:36px;line-height:1.2}h2{margin-top:36px}dl{display:grid;grid-template-columns:180px 1fr}dt{font-weight:bold}dd{margin:0}nav{display:flex;gap:20px}a{color:#4f46e5}table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{border:1px solid #ddd;padding:18px;vertical-align:top}th{background:#f6f6f6;text-align:left}th:first-child{width:12%}th:nth-child(2){width:38%}img{display:block;width:100%;height:auto;max-height:360px;object-fit:contain}aside{background:#f7f7f9;padding:16px}.note,small{color:#666;font-size:13px}@media(max-width:700px){body{padding:0 12px}table,tbody,tr,td{display:block}thead{display:none}td{border-top:0}dl{display:block}dd{margin-bottom:10px}}@media print{nav{display:none}body{margin:0}tr{break-inside:avoid}}'
    (out / 'script.html').write_text('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' + esc(script['title']) + '</title><style>' + css + '</style></head><body>' + ''.join(blocks) + '</body></html>', encoding='utf-8')
    (out / 'script.txt').write_text('\n'.join(text) + '\n', encoding='utf-8')
