from copy import deepcopy
import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from common import SkillError, read_json, write_json
from script_data import validate, register_image, revision_diff
from workflow import bind_reference, image_plan, apply_reviews, apply_revision, save_revision, restore_revision

ROOT = Path(__file__).resolve().parents[1]
QA = {'black_white': True, 'identity_match': True, 'no_text': True, 'action_match': True, 'notes': 'Synthetic test fixture; not a real visual assessment.'}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.doc = read_json(ROOT / 'examples/script.json')
        self.path = self.root / 'script.json'
        write_json(self.path, self.doc)
    def tearDown(self): self.tmp.cleanup()
    def reviews(self):
        row = {'reviewer':'creator pass', 'mode':'separate_pass', 'style_match':90, 'brand_alignment':80, 'production_level':'Low', 'brand_safe':True, 'notes':'s1 uses comparison; s2 has explicit action.'}
        return {'v1':[row, dict(row, reviewer='brand pass', style_match=80, brand_alignment=86, production_level='Medium')]}
    def test_real_host_requires_bound_frame_and_plan_passes_paths(self):
        self.doc['cast'][0]['identity']='observed'
        with self.assertRaises(SkillError): image_plan(self.doc, self.root)
        write_json(self.path, self.doc)
        from PIL import Image
        Image.new('RGB',(100,100),'gray').save(self.root/'host.png')
        bind_reference(self.path,'host','host.png','https://example.org/source',3)
        plan=image_plan(read_json(self.path),self.root)
        self.assertEqual(plan[0]['referenced_image_paths'],[str((self.root/'host.png').resolve())])
        self.assertIn('black and white',plan[0]['prompt'])
        Image.new('RGB',(100,100),'black').save(self.root/'host.png')
        self.assertFalse(validate(read_json(self.path),self.root)['valid'])
    def test_color_and_unreviewed_images_rejected(self):
        from PIL import Image
        Image.new('RGB',(100,100),'teal').save(self.root/'frame.png')
        with self.assertRaises(SkillError): register_image(self.path,'v1','s1','frame.png',QA)
        Image.new('RGB',(100,100),'gray').save(self.root/'frame.png')
        with self.assertRaises(SkillError): register_image(self.path,'v1','s1','frame.png')
        register_image(self.path,'v1','s1','frame.png',QA)
    def test_unused_actor_change_does_not_invalidate_scene(self):
        new=deepcopy(self.doc)
        new['cast'].append({'id':'unused','name':'Off screen','appearance':'plain shirt'})
        self.assertEqual(revision_diff(self.doc,new)['regenerate_images'],[])
    def test_aggregation_and_review_staleness(self):
        reviewed=apply_reviews(self.doc,self.reviews())
        v=reviewed['variations'][0]
        self.assertEqual(v['verification']['match_score'],84)
        self.assertEqual(v['verification']['production_level'],'Medium')
        self.assertTrue(validate(reviewed,self.root)['valid'])
        v['scenes'][0]['audio']+=' extra words'
        self.assertFalse(validate(reviewed,self.root)['valid'])
    def test_rank_and_brand_safety_and_no_fake_success(self):
        other=deepcopy(self.doc['variations'][0]);other['id']='v2';self.doc['variations'].append(other)
        reviews=self.reviews();reviews['v2']=[dict(reviews['v1'][0],style_match=99,brand_alignment=99,brand_safe=False)]
        result=apply_reviews(self.doc,reviews)
        self.assertEqual(result['variations'][0]['id'],'v2')
        self.assertFalse(result['variations'][0]['verification']['brand_safe'])
        with self.assertRaises(SkillError): apply_reviews(self.doc,{'v1':reviews['v1']})
    def test_full_and_partial_lock_enforcement(self):
        proposal=deepcopy(self.doc)
        for s in proposal['variations'][0]['scenes']:
            s['visual']='changed';s['audio']='changed';s['image_prompt']='changed'
        f={'variation_id':'v1','scenes':[{'scene_id':'s1','approved':True},{'scene_id':'s2','approved':True,'lock_visual':True,'lock_audio':False}]}
        out,changed=apply_revision(self.doc,proposal,f)
        a,b=out['variations'][0]['scenes']
        self.assertEqual(a,self.doc['variations'][0]['scenes'][0])
        self.assertEqual(b['visual'],self.doc['variations'][0]['scenes'][1]['visual'])
        self.assertEqual(b['audio'],'changed')
        self.assertEqual(changed,[])
    def test_dialogue_reuses_image_visual_change_drops_it(self):
        from PIL import Image
        Image.new('RGB',(100,100),'gray').save(self.root/'frame.png')
        for sid in ('s1','s2'): register_image(self.path,'v1',sid,'frame.png',QA)
        old=read_json(self.path);proposal=deepcopy(old)
        proposal['variations'][0]['scenes'][0]['audio']='new dialogue'
        proposal['variations'][0]['scenes'][1]['visual']='new shot'
        result,changed=apply_revision(old,proposal,{'variation_id':'v1','scenes':[]})
        self.assertIn('image',result['variations'][0]['scenes'][0])
        self.assertNotIn('image',result['variations'][0]['scenes'][1])
        self.assertEqual(changed,['s2'])
    def test_scene_structure_and_global_changes_rejected(self):
        proposed=deepcopy(self.doc);proposed['variations'][0]['scenes'].reverse()
        with self.assertRaises(SkillError):apply_revision(self.doc,proposed,{'variation_id':'v1'})
        proposed=deepcopy(self.doc);proposed['cast'][0]['appearance']='new face'
        with self.assertRaises(SkillError):apply_revision(self.doc,proposed,{'variation_id':'v1'})
    def test_snapshot_and_restore_preserve_both_versions(self):
        proposed=deepcopy(self.doc);proposed['variations'][0]['scenes'][0]['audio']='Revised line.'
        write_json(self.root/'proposed.json',proposed)
        write_json(self.root/'feedback.json',{'variation_id':'v1','scenes':[]})
        saved=save_revision(self.path,self.root/'proposed.json',self.root/'feedback.json')
        self.assertNotEqual(read_json(self.path),self.doc)
        restore_revision(self.path,saved['snapshot'])
        self.assertEqual(read_json(self.path),self.doc)
        self.assertEqual(len(list((self.root/'revisions').glob('*before-restore.json'))),1)

if __name__=='__main__': unittest.main()
