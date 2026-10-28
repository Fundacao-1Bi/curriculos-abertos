#!/usr/bin/env python3
"""Repeat extraction to an in-memory sink; never rewrite the frozen sidecar."""
from pathlib import Path
import importlib.util,sys,hashlib,json
R=Path(__file__).resolve().parents[3];F=Path(__file__).with_name('ap-rca614-items.json');frozen=F.read_bytes()
class MemorySink:
 def write_text(self,text):self.data=text.encode();return len(text)
 def read_bytes(self):return self.data
path=Path(__file__).with_name('ap-rca614-extract.py');spec=importlib.util.spec_from_file_location('ap614_repro_source',path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);sink=MemorySink();m.OUT=sink;m.extract();assert sink.data==frozen;assert F.read_bytes()==frozen
report={'source_id':m.SID,'source_sha256':m.H,'sidecar_sha256':hashlib.sha256(frozen).hexdigest(),'repeated_output_sha256':hashlib.sha256(sink.data).hexdigest(),'byte_identical':True,'frozen_file_unchanged':True,'method':'Same own native source generator rerun with output captured in memory; no second PDF/cache/large JSON persisted','generator_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'labelled_helper_sha256':hashlib.sha256(path.with_name('ap-rca614-labelled.py').read_bytes()).hexdigest()}
(R/'docs/evidence/source-audit-ap-eief/ap614-reproduction.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
