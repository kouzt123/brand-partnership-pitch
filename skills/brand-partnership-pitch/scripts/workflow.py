"""Brand Partnership Pitch's cast reference, review, and revision contracts without a model API."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import math
from common import SkillError, digest, file_digest, local_asset, read_json, write_json
from script_data import visual_fingerprint, validate

STORYBOARD_STYLE = 'Simple black and white hand-drawn storyboard sketch. Clean lines, minimal shading, white paper, clear composition and camera angle. No color, no text, no labels, no captions, no watermark. Not a polished advertising illustration.'


def bind_reference(script_path, cast_id, image, source, time_seconds):
    path = Path(script_path)
    doc = read_json(path)
    if not source.strip() or not math.isfinite(time_seconds) or time_seconds < 0:
        raise SkillError('Reference needs a source and a finite nonnegative timestamp')
    asset = local_asset(path.parent, image)
    from PIL import Image
    with Image.open(asset) as im:
        im.verify()
    person = next((c for c in doc['cast'] if c['id'] == cast_id), None)
    if person is None:
        raise SkillError('Unknown cast ID')
    ref = {'path': image, 'sha256': file_digest(asset), 'source': source, 'time_seconds': time_seconds}
    person['references'] = [r for r in person.get('references', []) if r['path'] != image] + [ref]
    write_json(path, doc)
    return ref


def image_plan(doc, base):
    report = validate(doc, base)
    if not report['valid']:
        raise SkillError('; '.join(report['errors']))
    result = []
    for v in doc['variations']:
        for s in v['scenes']:
            cast = [c for c in doc['cast'] if c['id'] in s['cast_ids']]
            refs, descriptions = [], []
            for c in cast:
                if c.get('identity', 'observed') == 'observed' and not c.get('references'):
                    raise SkillError(f"{c['id']}: bind an inspected creator frame before generating storyboards; do not invent a host")
                descriptions.append(f"{c['name']} ({c.get('role', '')}): {c['appearance']}")
                for r in c.get('references', []):
                    refs.append({'cast_id': c['id'], **r, 'absolute_path': str(local_asset(base, r['path']))})
            brief = doc['brief']
            prompt = f"{STORYBOARD_STYLE}\nAspect: {v['aspect_ratio']}. One scene per image.\nBrand/product: {brief.get('brand_name', '')} / {brief.get('product_name', '')}. Product usage: {brief.get('usage_context', '')}.\nCharacters (match reference faces, hair, visible features and wardrobe precisely): {'; '.join(descriptions) if descriptions else 'No visible person in this shot; do not add a host.'}\nVisual: {s['visual']}\nAudio context (do NOT draw this text): {s['audio']}\nTime: {s['start']}–{s['end']}s.\nScene details: {s['image_prompt']}\nPreserve actual creator identity across scenes. Use photographs as identity references, not as color/style references. All writing stays outside the image."
            result.append({'variant': v['id'], 'scene': s['id'], 'aspect_ratio': v['aspect_ratio'], 'prompt': prompt,
                           'references': refs, 'referenced_image_paths': list(dict.fromkeys(r['absolute_path'] for r in refs)),
                           'visual_fingerprint': visual_fingerprint(doc, v, s), 'suggested_path': f"images/{v['id']}-{s['id']}.png"})
    return result


def apply_reviews(doc, reviews):
    """Aggregate actually performed Codex reviews; never simulate model consensus."""
    result = deepcopy(doc)
    levels = ['Low', 'Medium', 'High']
    for v in result['variations']:
        rows = reviews.get(v['id'], [])
        if not rows:
            raise SkillError(f"Missing review for {v['id']}")
        seen = set()
        for row in rows:
            for field in ('reviewer', 'mode', 'notes'):
                if not isinstance(row.get(field), str) or not row[field].strip():
                    raise SkillError('Reviews need reviewer, mode and concrete notes')
            if row['mode'] not in ('self_review', 'separate_pass', 'independent_agent') or row['reviewer'] in seen:
                raise SkillError('Invalid review mode or duplicate reviewer')
            seen.add(row['reviewer'])
            for field in ('style_match', 'brand_alignment'):
                val = row.get(field)
                if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or not 0 <= val <= 100:
                    raise SkillError('Review scores must be finite numbers from 0 to 100')
            if row.get('production_level') not in levels or type(row.get('brand_safe')) is not bool:
                raise SkillError('Review needs production_level and boolean brand_safe')
        mean = lambda field: sum(row[field] for row in rows) / len(rows)
        v['verification'] = {'style_match': round(mean('style_match')), 'brand_alignment': round(mean('brand_alignment')),
            'match_score': math.floor((mean('style_match') + mean('brand_alignment')) / 2 + .5),
            'production_level': levels[math.floor(sum(levels.index(row['production_level']) for row in rows) / len(rows) + .5)],
            'brand_safe': all(row['brand_safe'] for row in rows),
            'reviewer_notes': '\n'.join(f"{row['reviewer']} ({row['mode']}): {row['notes']}" for row in rows),
            'reviews': rows, 'script_fingerprint': review_fingerprint(v), 'status': 'reviewed'}
    result['variations'].sort(key=lambda v: v['verification']['match_score'], reverse=True)
    for i, v in enumerate(result['variations']):
        v['recommended'] = i == 0
    return result


def review_fingerprint(variation):
    return digest({k: v for k, v in variation.items() if k not in ('verification', 'recommended', 'revision_history') and k != 'scenes'} | {
        'scenes': [{k: v for k, v in s.items() if k != 'image'} for s in variation['scenes']]})


def apply_revision(original, proposed, feedback):
    """Keep stable scene structure; deterministically restore locked fields."""
    result = deepcopy(original)
    vid = feedback['variation_id']
    old = next((v for v in original['variations'] if v['id'] == vid), None)
    new = next((v for v in proposed['variations'] if v['id'] == vid), None)
    if old is None or new is None:
        raise SkillError('Revision variation not found')
    if [(s['id']) for s in old['scenes']] != [(s['id']) for s in new['scenes']]:
        raise SkillError('A scene revision must preserve scene IDs and order; structural rewrites need a new version explicitly')
    if any(original.get(k) != proposed.get(k) for k in ('cast', 'visual_style', 'brief', 'channel')):
        raise SkillError('Scene revision cannot silently change global cast, style, brief or channel')
    updated = deepcopy(new)
    feedbacks = {f['scene_id']: f for f in feedback.get('scenes', [])}
    if set(feedbacks) - {s['id'] for s in old['scenes']}:
        raise SkillError('Feedback refers to an unknown scene')
    changed = []
    for index, (before, after) in enumerate(zip(old['scenes'], updated['scenes'])):
        f = feedbacks.get(before['id'], {})
        if f.get('approved'):
            lv, la = f.get('lock_visual', True), f.get('lock_audio', True)
            if lv and la:
                updated['scenes'][index] = deepcopy(before)
                continue
            if lv:
                for field in ('visual', 'cast_ids', 'image_prompt', 'onscreen_text'):
                    after[field] = deepcopy(before[field])
            if la:
                after['audio'] = before['audio']
            for field in ('start', 'end', 'notes'):
                after[field] = before[field]
        if visual_fingerprint(original, old, before) == visual_fingerprint(result, updated, after):
            if 'image' in before:
                after['image'] = deepcopy(before['image'])
            else:
                after.pop('image', None)
        else:
            after.pop('image', None)
            changed.append(after['id'])
    updated['verification'] = {'status': 'needs_review', 'reviewer_notes': 'Script revised; previous scores are not current.'}
    result['variations'] = [updated if v['id'] == vid else v for v in result['variations']]
    return result, changed


def save_revision(script_path, proposed_path, feedback_path):
    path = Path(script_path)
    old = read_json(path)
    revised, changed = apply_revision(old, read_json(proposed_path), read_json(feedback_path))
    report = validate(revised, path.parent)
    if not report['valid']:
        raise SkillError('; '.join(report['errors']))
    history = path.parent / 'revisions'
    history.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    snapshot = history / f'{stamp}-{digest(old)[:10]}.json'
    write_json(snapshot, old)
    write_json(history / f'{stamp}-feedback.json', read_json(feedback_path))
    write_json(path, revised)
    return {'snapshot': str(snapshot), 'regenerate_scenes': changed, 'review': 'required'}


def restore_revision(script_path, snapshot_path):
    path, snapshot = Path(script_path), Path(snapshot_path)
    restored = read_json(snapshot)
    report = validate(restored, path.parent)
    if not report['valid']:
        raise SkillError('Snapshot assets are missing/stale: ' + '; '.join(report['errors']))
    history = path.parent / 'revisions'
    history.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    write_json(history / f'{stamp}-before-restore.json', read_json(path))
    write_json(path, restored)
    return {'restored': str(snapshot), 'script': str(path)}
