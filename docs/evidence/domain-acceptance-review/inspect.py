"""Bounded read-only acceptance observations. No release gate execution, DB writes or extraction."""
import collections,datetime,hashlib,json,pathlib,re,urllib.request
R=pathlib.Path(__file__).resolve().parents[3];O=pathlib.Path(__file__).parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads((R/p).read_text())
report={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:domain:acceptance-review','classification':'state_audit_not_final_release_verification','mutation_policy':'Read-only public HTTP and repository metadata; no DB mutation, extraction, build, benchmark or operational restart.'}
observed={}
for route in ['/api/ready','/api/v1/publicacoes','/api/v1/ufs']:
 try:
  with urllib.request.urlopen('http://localhost:3000'+route,timeout=10) as response:
   raw=response.read(150001);assert len(raw)<=150000;value=json.loads(raw);status=response.status
  if route.endswith('/publicacoes'):value={'publication':value.get('publication'),'data':[{k:r.get(k) for k in ['id','item_count','relation_count','source_count','is_default','created_at']} for r in value.get('data',[])]}
  if route.endswith('/ufs'):value={'publication':value.get('publication'),'total':value.get('total'),'data':[{k:r.get(k) for k in ['uf','ready','status','item_count','source_count']} for r in value.get('data',[])]}
  observed[route]={'status':status,'value':value}
 except Exception as e:observed[route]={'error':type(e).__name__,'message':str(e)}
report['public_http']=observed
sources={};manifest_pins={}
for p in sorted((R/'data/manifests').glob('*.json')):
 value=json.loads(p.read_text());rows=value if isinstance(value,list) else value.get('sources',[])
 if rows:manifest_pins[str(p.relative_to(R))]=digest(p)
 for row in rows:
  if isinstance(row,dict) and row.get('id'):sources[row['id']]=row
report['source_catalogue']={'sources':len(sources),'by_uf':dict(collections.Counter(s['uf'] for s in sources.values())),'by_status':dict(collections.Counter(s.get('status','missing') for s in sources.values())),'explicit_required_flags':sum(s.get('mandatory') is True or s.get('required') is True for s in sources.values()),'required_flag_count_is_not_a_complete_curricular_denominator':True,'manifest_sha256':manifest_pins,'unavailable_or_research':[ {k:s.get(k) for k in ['id','uf','status','mandatory','required','error','inventory_status']} for s in sources.values() if s.get('status') in ['unavailable','research_pending']]}
report['data_pointer']=load('data/bundles/latest.json');coverage=load('data/coverage-manifest.json');report['coverage_manifest']={'sha256':digest(R/'data/coverage-manifest.json'),'generated_at':coverage.get('generated_at'),'publication':coverage.get('publication'),'national_release_ready':coverage.get('national_release_ready'),'ufs_ready':coverage.get('ufs_ready'),'coverage_rows':len(coverage.get('coverage',[]))}
report['reconciliation_files']=[{'path':str(p.relative_to(R)),'sha256':digest(p),'source_id':(v:=json.loads(p.read_text())).get('source_id'),'extraction_revision':v.get('extraction_revision'),'scope':v.get('scope',v.get('reconciliation_scope')),'pending_parts':v.get('pending_parts'),'inventory_complete':v.get('inventory_complete')} for p in sorted((R/'data/manifests/reconciliation').glob('*.json'))]
report['reconciliation_file_count_is_not_source_readiness']=True
jobs=[]
for name in ['national-extraction-v150-20261028','national-extraction-v150-refresh-20261028']:
 p=R/f'var/jobs/{name}.json'
 if not p.exists():continue
 v=json.loads(p.read_text());rows=v.get('results',[]);rows=rows if isinstance(rows,list) else list(rows.values());jobs.append({'path':str(p.relative_to(R)),'sha256':digest(p),'id':v['id'],'state':v['state'],'revision':v['revision'],'started_at':v['started_at'],'updated_at':v['updated_at'],'expected':v['sources_expected'],'results':len(rows),'result_statuses':dict(collections.Counter(r.get('status',r.get('state')) for r in rows)),'reported_pages':sum(r.get('pages',0) for r in rows),'reported_candidate_items':sum(r.get('items',0) for r in rows),'failed_sources':[{k:r.get(k) for k in ['source_id','status','error']} for r in rows if r.get('status')=='failed'],'parser_fingerprint_sha256':v.get('parser_fingerprint',{}).get('sha256')})
report['extraction_jobs']=jobs
p=R/'var/jobs/national-extraction-v150-20261028-config-drift.json'
if p.exists():
 v=json.loads(p.read_text());report['configuration_drift_snapshot']={'path':str(p.relative_to(R)),'sha256':digest(p),'updated_at':v.get('updated_at'),'refresh_required':len(v.get('metadata_drift_refresh_required',[])),'source_ids':[r['source_id'] for r in v.get('metadata_drift_refresh_required',[])],'limitation':'Snapshot predates the subsequent refresh and later source edits; no claim that all current configuration drift is resolved.'}
report['final_execution_wrappers_present']=(R/'docs/evidence/executions').exists();report['wrapper_files']=[str(p.relative_to(R)) for p in (R/'docs/evidence/executions').glob('*.json')]
for name in ['release-check.json','release-check-integration-review.json']:
 p=R/'docs/evidence'/name
 if p.exists():
  v=json.loads(p.read_text());report[name]={'generated_at':v.get('generated_at'),'source_tree_sha256':v.get('source_tree_sha256'),'publication':v.get('publication'),'passed':v.get('passed'),'sha256':digest(p)}
report['requirement_ids']=re.findall(r'^### ([A-Z]+-\d+)\.',(R/'docs/requirements.md').read_text(),re.M)
report['requirements_sha256']=digest(R/'docs/requirements.md');report['limits']=['Counts from job metadata are extraction outputs, not completeness evidence.','The current HTTP default and filesystem data pointer are different known partial publications; no promotion performed.','Old release reports and diagnostic tests do not verify current code/manifests or a final national dataset.','No current serving-image fingerprint or deployment acceptance is inferred from source files or health200.','Existing reconciliation files include partial scopes and older revisions; their existence is not equivalent to closed required sources.']
(O/'observed-state.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'at':report['at'],'public_default':observed.get('/api/ready',{}).get('value',{}).get('publication'),'source_catalogue':len(sources),'reconciliation_files':len(report['reconciliation_files']),'execution_wrappers_present':report['final_execution_wrappers_present'],'jobs':jobs},ensure_ascii=False))
