import assert from 'node:assert/strict';
import { mkdir,readFile,writeFile,readdir,realpath,lstat,rm,rmdir } from 'node:fs/promises';
import {resolve,basename} from 'node:path';
import {randomUUID} from 'node:crypto';
import {pool} from '../src/db/client';
import {withQaRun,currentQaRun} from './qa-executor';
import {hashArtifactFile} from './audit-artifact';
import { StructureResultSchema } from '../src/mcp/contracts';
import { downloadAndHash, validatePublishedJsonFile, validatePublishedCsvFile } from './api-export-stream';

const base=process.env.TEST_BASE_URL??process.env.VERIFY_BASE_URL??process.env.PUBLIC_URL??'http://localhost:3000';
const clientRoot=resolve('var/qa-downloads',randomUUID());
const clientFiles:{resource:string;path:string;bytes:number;sha256:string}[]=[];let exportRequests=0;
const clientGuardAbort=new AbortController();
const checks:{name:string;status:number;success:boolean}[]=[];
const dataFailures:string[]=[];
const started_at=new Date().toISOString();
const verificationTimeoutMs=Math.max(5_000,Math.min(550_000,Number(process.env.API_VERIFY_TIMEOUT_MS)||540_000));
const verificationDeadline=Date.now()+verificationTimeoutMs;
let publication:string|undefined;let expectedSources:number|undefined,expectedRelations:number|undefined,expectedSample:{id:string;text:string;evidence?:unknown}|undefined;
const exportTimeoutMs=Math.max(1_000,Math.min(500_000,Number(process.env.API_EXPORT_TIMEOUT_MS)||240_000));
async function request(path:string,expected=200,init?:RequestInit){
 currentQaRun().checkpoint();
 const response=await fetch(base+'/api/v1/'+path,{...init,signal:AbortSignal.any([init?.signal??AbortSignal.timeout(30_000),currentQaRun().signal,clientGuardAbort.signal])});checks.push({name:`${init?.method??'GET'} ${path}`,status:response.status,success:response.status===expected});
 if(response.status!==expected)assert.equal(response.status,expected,`${path}: ${(await response.text()).slice(0,4000)}`);assert.ok(response.headers.get('x-request-id'),'Request ID obrigatório');return response;
}
async function json(path:string,expected=200,init?:RequestInit){const response=await request(path,expected,init);return response.json();}
const post=(body:unknown)=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const pin=(path:string)=>`${path}${path.includes('?')?'&':'?'}publication=${encodeURIComponent(publication!)}`;
async function exportAndRead(format:'json'|'csv',extra:Record<string,unknown>={}){
 const qa=currentQaRun();assert.ok(++exportRequests<=5,'API QA may request at most five complete export views');
 const count=Number((await pool.query("SELECT count(*) AS n FROM jobs WHERE type='export'")).rows[0].n);assert.ok(count<15,'QA export retention limit reached; consolidate existing outputs before allocating more');
 const requestResource=qa.registerResource({kind:'export-request',id:'api-export-request-'+exportRequests,owned:true,disposition:'retain',metadata:{view:String(extra.view??'search'),format,ownership_known:false}});qa.checkpoint();
 const job=await json('exportacoes',202,post({publication,format,...extra}));assert.equal(typeof job.id,'string');assert.match(job.id,/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);assert.equal(job.publication,publication);qa.markResource(requestResource,'created',{allocated_id:job.id,ownership_known:false});
 const serverResource=qa.registerResource({kind:'job',id:job.id,owned:false,disposition:'retain',metadata:{ownership_known:false,deduplicated_public_api:true}});qa.markResource(serverResource,'retained');const after=Number((await pool.query("SELECT count(*) AS n FROM jobs WHERE type='export'")).rows[0].n);assert.ok(after<=15,'Concurrent exports exceeded QA retention limit; preserve outputs and reconcile before continuing');let status=job;const exportStarted=Date.now(),deadline=Math.min(exportStarted+exportTimeoutMs,verificationDeadline);let fileUnavailableChecked=false;
 while(Date.now()<deadline){
  status=await json(`exportacoes/${job.id}`);assert.equal(status.publication,publication,'Job pendente deve preservar sua publicação fixada.');if(status.status==='succeeded')break;if(status.status==='failed')throw new Error(`Exportação ${job.id} falhou.`);
  if(!fileUnavailableChecked){await json(`exportacoes/${job.id}/arquivo`,409);fileUnavailableChecked=true;}
  await new Promise(resolve=>setTimeout(resolve,Math.min(1000,Math.max(1,deadline-Date.now()))));
 }
 assert.equal(status.status,'succeeded',`Exportação ${job.id} não concluiu em ${Date.now()-exportStarted} ms (limite ${exportTimeoutMs} ms; estado ${status.status}).`);assert.equal(status.publication,publication);assert.ok(status.download_url);assert.ok(status.sha256);
 const file=await request(`exportacoes/${job.id}/arquivo`);assert.equal(file.headers.get('x-data-publication'),publication);
 const path=resolve(clientRoot,`${exportRequests}-${job.id}.${format}`),localResource=qa.registerResource({kind:'file',id:'api-download-'+exportRequests,path,owned:true,disposition:'disposable'});qa.checkpoint();
 const saved=await downloadAndHash(file,path);clientFiles.push({resource:localResource,...saved});qa.markResource(localResource,'created',{bytes:saved.bytes,sha256:saved.sha256});assert.equal(saved.sha256,status.sha256);assert.equal(saved.bytes,status.size);
 if(extra.view&&extra.view!=='search'){assert.ok(saved.bytes<128*1024*1024,'Relatório excede o teto de materialização do teste; usar parser incremental também neste recorte.');const payload=JSON.parse(await readFile(saved.path,'utf8'));assert.equal(payload.publication,publication);assert.equal(payload.export_manifest.publication,publication);assert.equal(payload.export_manifest.unpaginated,true);assert.ok(Array.isArray(payload.sources));return payload;}
 const expected={publication:publication!,record_count:Number(status.record_count),source_count:expectedSources,relation_count:expectedRelations,sample:expectedSample};
 const summary=format==='json'?await validatePublishedJsonFile(saved.path,expected):await validatePublishedCsvFile(saved.path,expected);
 report.downloads??=[];(report.downloads as unknown[]).push({...saved,...summary});return summary;
}
const report:Record<string,unknown>={started_at,base,client:'Node fetch HTTP',checks,data_failures:dataFailures,server_export_constraint:'Public export deduplication does not prove ownership; admission count/budget limits do not enforce a hard server filesystem quota and never authorize pausing or cancelling unknown jobs.'};
async function main(){try{await withQaRun({kind:'api',purpose:'Isolated real HTTP API/export QA with bounded retained server cache',requiresDocker:true,project:process.env.QA_COMPOSE_PROJECT,inputs:{base:new URL(base).origin}},async qa=>{
 await qa.assertQaDatabase(statement=>pool.query(statement),process.env.QA_COMPOSE_PROJECT,base);
 const selected=(await pool.query('SELECT id,sha256 FROM publications WHERE id=coalesce($1,(SELECT publication_id FROM current_publication WHERE singleton=true))',[process.env.TEST_PUBLICATION??null])).rows[0];assert.ok(selected,'Pinned QA publication must exist');
 const measured=(await pool.query(`SELECT
  (SELECT coalesce(sum(octet_length(payload::text)),0) FROM items WHERE publication_id=$1) AS items,
  (SELECT coalesce(sum(octet_length(payload::text)),0) FROM relations WHERE publication_id=$1) AS relations,
  (SELECT coalesce(sum(octet_length(payload::text)),0) FROM sources WHERE publication_id=$1) AS sources,
  (SELECT coalesce(octet_length(payload::text),0) FROM publications WHERE id=$1) AS metadata,
  (SELECT coalesce(sum(octet_length(payload::text)),0) FROM publication_coverage WHERE publication_id=$1) AS coverage,
  (SELECT coalesce(sum(octet_length(id)+4),0) FROM items WHERE publication_id=$1) AS ids`,[selected.id])).rows[0];
 const sizes=Object.fromEntries(Object.entries(measured).map(([key,value])=>[key,Number(value)]));assert.ok(Object.values(sizes).every(value=>Number.isSafeInteger(value)&&value>=0));
 const jsonUpper=2*(sizes.items+sizes.relations+sizes.sources+4*(sizes.metadata+sizes.coverage+sizes.ids))+1024**2;
 assert.ok(Number.isSafeInteger(jsonUpper)&&jsonUpper>0);
 const reserve=2*1024**3;qa.reserve({stage:'api',required_free_bytes:10*jsonUpper+reserve,reserve_bytes:reserve});
 qa.onGuardFailure(()=>{clientGuardAbort.abort();qa.recordReport('api-export-capacity-guard.json',{client_requests_aborted:true,server_jobs_stopped:false,foreign_jobs_mutated:false,hard_server_quota:false,retention_blocked:true,reason:'Ownership of deduplicated public exports is unknown; preserve jobs and reconcile server outputs instead of pausing another requester work.'});});
 qa.setInputs({publication:selected.id,publication_sha256:selected.sha256,export_json_upper_bytes:jsonUpper});
 const rootResource=qa.registerResource({kind:'directory',id:'api-download-root',path:clientRoot,owned:true,disposition:'disposable'});
 qa.checkpoint();await mkdir(resolve('var/qa-downloads'),{recursive:true});await mkdir(clientRoot,{mode:0o700});qa.markResource(rootResource,'created');
try{
 const spec=await json('openapi.json');assert.equal(spec.openapi,'3.1.0');assert.ok(spec.paths['/aprendizagens/consulta-lote']);
 const versions=await json('publicacoes');publication=process.env.TEST_PUBLICATION??versions.publication;assert.ok(publication&&publication!=='none','Publicação real deve estar carregada.');assert.equal(publication,selected.id,'HTTP and SQL must identify the same pinned QA publication');report.publication=publication;const selectedVersion=versions.data.find((row:{id:string})=>row.id===publication);expectedSources=selectedVersion?.source_count;expectedRelations=selectedVersion?.relation_count;
 const ufsResponse=await request(pin('ufs'));const ufs=await ufsResponse.json();assert.equal(ufs.publication,publication);assert.equal(ufs.data.length,27);assert.equal(new Set(ufs.data.map((r:{uf:string})=>r.uf)).size,27);
 const etag=ufsResponse.headers.get('etag');assert.ok(etag);await request(pin('ufs'),304,{headers:{'If-None-Match':etag}});
 for(const op of ['redes','curriculos','cobertura','fontes','analises','correspondencias']){const data=await json(pin(op));assert.equal(data.publication,publication);assert.ok('data'in data);}
 const curricula=await json(pin('curriculos'));assert.ok(curricula.data.length>0);const curriculum=curricula.data[0];await json(pin(`curriculos/${encodeURIComponent(curriculum.id)}`));const structure=StructureResultSchema.parse(await json(pin(`curriculos/${encodeURIComponent(curriculum.id)}/estrutura`)));assert.equal(structure.hierarchy.total,structure.hierarchy.nodes.length);const parent=structure.hierarchy.nodes.find(node=>node.child_count>0);if(parent){const children=await json(pin(`aprendizagens?parent_id=${encodeURIComponent(parent.id)}&limit=100`));assert.equal(children.total,parent.child_count);for(const child of children.data)assert.equal(child.parent_id,parent.id);report.hierarchy_parent_id=parent.id;}
 const sources=await json(pin('fontes'));assert.ok(sources.data.length>0);await json(pin(`fontes/${encodeURIComponent(sources.data[0].id)}`));
 const first=await json(pin('aprendizagens?limit=2'));assert.ok(first.data.length>0,'Busca deve consultar registros reais, não scaffold.');const item=first.data[0];assert.ok(item.evidence?.length>0);assert.ok(item.text?.length>0);report.real_item_id=item.id;expectedSample={id:item.id,text:item.text,evidence:item.evidence};
 const itemResult=await json(pin(`aprendizagens/${encodeURIComponent(item.id)}`));assert.equal(itemResult.data.text,item.text);assert.deepEqual(itemResult.data.evidence,item.evidence);
 const next=await json(pin('aprendizagens?limit=2&page=2'));assert.equal(next.publication,publication);const firstIds=new Set(first.data.map((r:{id:string})=>r.id));for(const r of next.data)assert.ok(!firstIds.has(r.id));
 const local=await json(pin('aprendizagens?limit=1&uf=SP'));for(const r of local.data)assert.equal(r.uf,'SP');
 if(item.code){const exact=await json(pin(`aprendizagens?limit=100&q=${encodeURIComponent(item.code)}`));assert.ok(exact.data.some((r:{id:string})=>r.id===item.id));}
 const token=(item.text.match(/[A-Za-zÀ-ÿ]{5,}/g)??[])[0];if(token){const noAccent=token.normalize('NFD').replace(/[\u0300-\u036f]/g,'');await json(pin(`aprendizagens?limit=2&q=${encodeURIComponent(noAccent)}`));}
 const batch=await json('aprendizagens/consulta-lote',200,post({publication,ids:[item.id,'controlled-not-found-id','',null,{},'x'.repeat(501)]}));assert.deepEqual(batch.data.map((r:{status:string})=>r.status),['found','not_found','invalid','invalid','invalid','invalid']);assert.equal(batch.data[0].item.text,item.text);
 const national=await json(pin('aprendizagens?uf=BR&limit=1'));let nationalId:string|undefined;if(national.data.length){nationalId=String(national.data[0].id);report.national_item_id=nationalId;const panorama=await json(pin(`bncc/aprendizagens/${encodeURIComponent(nationalId)}/panorama`));assert.equal(panorama.data.ufs.length,27);}else{dataFailures.push('Panorama não verificável: BNCC real ausente na publicação.');}
 await json('comparacoes',200,post({publication,ufs:['AC','SP'],limit:2}));await json('comparacoes',200,post({publication,ufs:['RR','PE','SP'],stage:'EI',limit:2}));
 await json('comparacoes',400,post({publication,ufs:['SP']}));await json('comparacoes',400,post({publication,ufs:['SP','SP']}));
 await json('aprendizagens?limit=101',400);await json('aprendizagens?page=0',400);await json('aprendizagens?uf=ZZ',400);await json('aprendizagens?include_unpositioned=maybe',400);await json('aprendizagens?sql=select',400);await json('aprendizagens?publication=controlled-nonexistent-publication',404);await json(pin('aprendizagens/controlled-nonexistent-id'),404);await json('controlled-not-found-route',404);
 await json('aprendizagens/consulta-lote',400,post({ids:Array(101).fill(item.id)}));await json('exportacoes',400,post({view:'panorama'}));await json('exportacoes',400,post({view:'comparison'}));await json('exportacoes',400,post({view:'comparison',ufs:'ZZ,SP'}));await json('exportacoes',400,post({view:'comparison',ufs:'SP,SP'}));await json('comparacoes',415,{method:'POST',headers:{'Content-Type':'text/plain'},body:'{}'});await json('comparacoes',413,post({q:'x'.repeat(70000)}));
 await json('ufs',403,{headers:{Origin:'https://controlled-invalid-origin.example'}});
 const contributionResource=qa.registerResource({kind:'contribution',id:'api-contribution',owned:true,disposition:'retain'});
 const contribution=await json('contribuicoes',201,post({kind:'error',record_id:item.id,record_url:`/aprendizagens/${encodeURIComponent(item.id)}`,description:'Verificação automatizada da fila persistente; sem dados pessoais. Não alterar os dados curriculares.'}));assert.ok(contribution.data.id);qa.markResource(contributionResource,'created',{allocated_id:contribution.data.id});const tracking=await json(`contribuicoes/${contribution.data.id}`);assert.equal(tracking.data.status,'pending');assert.ok(!('description'in tracking.data));report.test_contribution_id=contribution.data.id;
 await json('contribuicoes',400,post({description:'Verificação de honeypot automatizada',website:'spam'}));
 const exported=await exportAndRead('json');await exportAndRead('csv');assert.equal(exported.id,publication);report.exported_items=exported.items;
 const comparisonReport=await exportAndRead('json',{view:'comparison',ufs:['SP','PE']});assert.equal(comparisonReport.data.columns.length,2);for(const column of comparisonReport.data.columns)assert.equal(column.items.length,column.total,'Relatório de comparação não pode cortar resultados.');
 const analysesReport=await exportAndRead('json',{view:'analyses'});assert.ok(analysesReport.data.matrix);assert.equal(analysesReport.data.matrix.rows.length,analysesReport.data.matrix.total,'Relatório da matriz não pode cortar resultados.');
 if(nationalId){const panoramaReport=await exportAndRead('json',{view:'panorama',item_id:nationalId});assert.equal(panoramaReport.data.ufs.length,27);for(const uf of panoramaReport.data.ufs)assert.equal(uf.items.length,uf.total,'Relatório do panorama não pode cortar resultados.');}
 report.data_failures=dataFailures;assert.equal(dataFailures.length,0,dataFailures.join(' '));report.success=true;
}catch(error){report.success=false;report.error=error instanceof Error?error.message:String(error);process.exitCode=1;}
qa.recordReport('api-verification-proof.json',report);
if(report.success===true){
 try{report.cleanup=await qa.guardCleanup([rootResource,...clientFiles.map(file=>file.resource)],async()=>{
  assert.equal(await realpath(clientRoot),clientRoot,'Owned download root cannot be a symlink');
  const names=await readdir(clientRoot);assert.deepEqual(names.sort(),clientFiles.map(file=>basename(file.path)).sort(),'Unknown files block cleanup');
  for(const file of clientFiles){const st=await lstat(file.path);assert.ok(st.isFile()&&!st.isSymbolicLink());assert.equal(st.size,file.bytes);assert.equal(await hashArtifactFile(file.path),file.sha256);}
  qa.recordReport('api-download-cleanup-proof.json',{root:clientRoot,files:clientFiles,server_exports_removed:false,reason:'Public export deduplication does not prove request ownership; server cache is retained under the QA export-count limit'});
  for(const file of clientFiles){await rm(file.path);qa.markResource(file.resource,'cleaned');}await rmdir(clientRoot);qa.markResource(rootResource,'cleaned');
  return{client_files_removed:clientFiles.length,server_exports_preserved:true,ownership_limit:15};
 });}catch(error){report.success=false;report.cleanup_error=error instanceof Error?error.message:String(error);process.exitCode=1;}
}else report.failure_artifacts_preserved=true;
report.finished_at=new Date().toISOString();qa.recordReport('api-verification.json',report);await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/api-verification.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
});}finally{await pool.end();}}
if(process.argv.includes('--help'))console.log('Usage: QA_COMPOSE_PROJECT=<isolated project> TEST_BASE_URL=<QA URL> node --import tsx scripts/api-verify.ts; DATABASE_URL must target the same curriculos_qa cluster. Five export views maximum; verified client downloads are cleaned on success, deduplicated server outputs are retained under a count limit.');else await main();
