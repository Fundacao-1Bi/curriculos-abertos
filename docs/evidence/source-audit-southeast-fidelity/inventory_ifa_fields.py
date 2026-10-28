#!/usr/bin/env python3
import json
import audit_es_native as a
from es_table_paths_proposal import table_paths_without_nested_text_backgrounds
s=next(s for s in json.loads((a.ROOT/'data/manifests/bncc-southeast.json').read_text())if s['id']=='es-ifa-lingchsa-6-1');a.OUT=a.OUT/'ifa-field64';r=a.inventory(s,paths_filter=lambda p:table_paths_without_nested_text_backgrounds(p,max_nested_height=64),include_uncoded_pages=True);print('all',r['document_pages'],'cells',len(r['cells']))
