import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { downloadAndHash, validatePublishedJsonFile, validatePublishedCsvFile } from './api-export-stream';

const base=process.env.TEST_BASE_URL??process.env.VERIFY_BASE_URL??process.env.PUBLIC_URL??'http://localhost:3000';
const checks:{name:string;status:number;success:boolean}[]=[];
const dataFailures:string[]=[];
const started_at=new Date().toISOString();
let publication:string|undefined;let expectedSources:number|undefined,expectedRelations:number|undefined,expectedSample:{id:string;text:string;evidence?:unknown}|undefined;
async function request(path:string,expected=200,init?:RequestInit){
 const response=await fetch(base+'/api/v1/'+path,init);checks.push({name:`${init?.method??'GET'} ${path}`,status:response.status,success:response.status===expected});
 if(response.status!==expected)assert.equal(response.status,expected,`${path}: ${(await response.text()).slice(0,4000)}`);assert.ok(response.headers.get('x-request-id'),'Request ID obrigatório');return response;
}
async function json(path:string,expected=200,init?:RequestInit){const response=await request(path,expected,init);return response.json();}
const post=(body:unknown)=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const pin=(path:string)=>`${path}${path.includes('?')?'&':'?'}publication=${encodeURIComponent(publication!)}`;
async function exportAndRead(format:'json'|'csv',extra:Record<string,unknown>={}){
 const job=await json('exportacoes',202,post({publication,format,...extra}));assert.ok(job.id);assert.equal(job.publication,publication);let status=job;
 for(let attempt=0;attempt<120;attempt++){
  status=await json(`exportacoes/${job.id}`);if(status.status==='succeeded')break;if(status.status==='failed')throw new Error(`Exportação ${job.id} falhou.`);
  if(attempt===0)await json(`exportacoes/${job.id}/arquivo`,409);
  await new Promise(resolve=>setTimeout(resolve,1000));
 }
 assert.equal(status.status,'succeeded','Worker deve concluir exportação.');assert.equal(status.publication,publication);assert.ok(status.download_url);assert.ok(status.sha256);
 const file=await request(`exportacoes/${job.id}/arquivo`);assert.equal(file.headers.get('x-data-publication'),publication);
 const saved=await downloadAndHash(file,`var/qa-downloads/${job.id}.${format}`);assert.equal(saved.sha256,status.sha256);assert.equal(saved.bytes,status.size);
 if(extra.view&&extra.view!=='search'){assert.ok(saved.bytes<128*1024*1024,'Relatório excede o teto de materialização do teste; usar parser incremental também neste recorte.');const payload=JSON.parse(await readFile(saved.path,'utf8'));assert.equal(payload.publication,publication);assert.equal(payload.export_manifest.publication,publication);assert.equal(payload.export_manifest.unpaginated,true);assert.ok(Array.isArray(payload.sources));return payload;}
 const expected={publication:publication!,record_count:Number(status.record_count),source_count:expectedSources,relation_count:expectedRelations,sample:expectedSample};
 const summary=format==='json'?await validatePublishedJsonFile(saved.path,expected):await validatePublishedCsvFile(saved.path,expected);
 report.downloads??=[];(report.downloads as unknown[]).push({...saved,...summary});return summary;
}
const report:Record<string,unknown>={started_at,base,client:'Node fetch HTTP',checks,data_failures:dataFailures};
try{
 const spec=await json('openapi.json');assert.equal(spec.openapi,'3.1.0');assert.ok(spec.paths['/aprendizagens/consulta-lote']);
 const versions=await json('publicacoes');publication=process.env.TEST_PUBLICATION??versions.publication;assert.ok(publication&&publication!=='none','Publicação real deve estar carregada.');report.publication=publication;const selected=versions.data.find((row:{id:string})=>row.id===publication);expectedSources=selected?.source_count;expectedRelations=selected?.relation_count;
 const ufsResponse=await request(pin('ufs'));const ufs=await ufsResponse.json();assert.equal(ufs.publication,publication);assert.equal(ufs.data.length,27);assert.equal(new Set(ufs.data.map((r:{uf:string})=>r.uf)).size,27);
 const etag=ufsResponse.headers.get('etag');assert.ok(etag);await request(pin('ufs'),304,{headers:{'If-None-Match':etag}});
 for(const op of ['redes','curriculos','cobertura','fontes','analises','correspondencias']){const data=await json(pin(op));assert.equal(data.publication,publication);assert.ok('data'in data);}
 const curricula=await json(pin('curriculos'));assert.ok(curricula.data.length>0);const curriculum=curricula.data[0];await json(pin(`curriculos/${encodeURIComponent(curriculum.id)}`));await json(pin(`curriculos/${encodeURIComponent(curriculum.id)}/estrutura`));
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
 const contribution=await json('contribuicoes',201,post({kind:'error',record_id:item.id,record_url:`/aprendizagens/${encodeURIComponent(item.id)}`,description:'Verificação automatizada da fila persistente; sem dados pessoais. Não alterar os dados curriculares.'}));assert.ok(contribution.data.id);const tracking=await json(`contribuicoes/${contribution.data.id}`);assert.equal(tracking.data.status,'pending');assert.ok(!('description'in tracking.data));report.test_contribution_id=contribution.data.id;
 await json('contribuicoes',400,post({description:'Verificação de honeypot automatizada',website:'spam'}));
 const exported=await exportAndRead('json');await exportAndRead('csv');assert.equal(exported.id,publication);report.exported_items=exported.items;
 const comparisonReport=await exportAndRead('json',{view:'comparison',ufs:['SP','PE']});assert.equal(comparisonReport.data.columns.length,2);for(const column of comparisonReport.data.columns)assert.equal(column.items.length,column.total,'Relatório de comparação não pode cortar resultados.');
 const analysesReport=await exportAndRead('json',{view:'analyses'});assert.ok(analysesReport.data.matrix);assert.equal(analysesReport.data.matrix.rows.length,analysesReport.data.matrix.total,'Relatório da matriz não pode cortar resultados.');
 if(nationalId){const panoramaReport=await exportAndRead('json',{view:'panorama',item_id:nationalId});assert.equal(panoramaReport.data.ufs.length,27);for(const uf of panoramaReport.data.ufs)assert.equal(uf.items.length,uf.total,'Relatório do panorama não pode cortar resultados.');}
 report.data_failures=dataFailures;assert.equal(dataFailures.length,0,dataFailures.join(' '));report.success=true;
}catch(error){report.success=false;report.error=error instanceof Error?error.message:String(error);process.exitCode=1;}
report.finished_at=new Date().toISOString();await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/api-verification.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
