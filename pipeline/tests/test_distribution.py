import copy
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from correspondence import lexical_candidates
from distribution import write_parts
from ingest import normalize
from validate_artifact import validate_artifact


class DistributionContracts(unittest.TestCase):
    def test_shards_are_deterministic_and_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);records=[{'id':'one','text':'Redação real preservada: á.'}]
            first=write_parts(root,'isolated-test','items',records)
            second=write_parts(root,'isolated-test','items',records)
            self.assertEqual(first,second)
            part=first[0];decoded=gzip.decompress((root/part['path']).read_bytes())
            self.assertEqual(hashlib.sha256(decoded).hexdigest(),part['decoded_sha256'])
            self.assertEqual(json.loads(decoded),records[0])
            with self.assertRaises(ValueError):write_parts(root,'isolated-test','items',[{'id':'one','text':'Changed'}])

    def test_record_bounds_do_not_silently_truncate(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):write_parts(Path(directory),'isolated-test','items',[{'text':'x'*(8*1024*1024)}])

    def test_schema_hash_is_a_blocking_artifact_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data/bundles').mkdir(parents=True);(root/'data/schema').mkdir()
            (root/'data/schema/1.0.0.json').write_text('{}')
            artifact=root/'data/bundles/isolated.manifest.json'
            artifact.write_text(json.dumps({'format':'curriculos-abertos/sharded-v1','schema_version':'1.0.0','schema_path':'data/schema/1.0.0.json','schema_sha256':'0'*64}))
            artifact.with_suffix('.json.sha256').write_text(hashlib.sha256(artifact.read_bytes()).hexdigest())
            with self.assertRaisesRegex(ValueError,'schema checksum mismatch'):validate_artifact(root,artifact)

    def test_lexical_match_stays_a_candidate_and_respects_stage(self):
        def item(id,uf,stage):return {'id':id,'uf':uf,'kind':'habilidade','text':'Investigar processos naturais relacionando energia matéria ambiente sustentabilidade.','positions':[{'stage':stage}],'evidence':[{'source_id':id,'page':1,'excerpt':'Trecho'}],'review_events':[{'at':'2026-10-28T00:00:00Z'}]}
        national=item('national','BR','EF');local=item('local','SP','EF')
        relation=lexical_candidates([national,local],[],normalize)[0]
        self.assertEqual(relation['origin'],'sugestao_automatica');self.assertEqual(relation['publication_status'],'candidate_pending');self.assertEqual(relation['pedagogical_review_status'],'not_reviewed')
        different=copy.deepcopy(local);different['positions'][0]['stage']='EI'
        self.assertEqual(lexical_candidates([national,different],[],normalize),[])


if __name__=='__main__':unittest.main()
