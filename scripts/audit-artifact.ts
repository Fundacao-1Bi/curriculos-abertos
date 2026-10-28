/** Bounded artifact inspection. A manifest is never accepted without reading every declared shard. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createReadStream,existsSync,statSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { resolve,join } from 'node:path';
import { loadBundleFile } from '../src/domain/bundle-file';
import { shardRecords,validateShardedManifest,type ShardedManifest,type ShardPart } from '../src/domain/shards';
import { LearningSchema,RelationSchema } from '../src/mcp/contracts';
import type { Bundle,Learning,Relation,Source,UF } from '../src/shared/contracts';
export const canonical=(value:unknown):string=>Array.isArray(value)?'['+value.map(canonical).join(',')+']':value&&typeof value==='object'?'{'+Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([key,v])=>JSON.stringify(key)+':'+canonical(v)).join(',')+'}':JSON.stringify(value)??'null';
export const digestValue=(value:unknown)=>createHash('sha256').update(canonical(value)).digest('hex');
export const digestText=(value:string)=>createHash('sha256').update(value).digest('hex');
export async function hashArtifactFile(path:string){const digest=createHash('sha256');for await(const chunk of createReadStream(path))digest.update(chunk);return digest.digest('hex');}
export interface SampleReference {id:string;uf:UF|'BR';source_id:string;code:string|null;kind:string;text_sha256:string;text_length:number;evidence_sha256:string;positions_sha256:string;}
export interface ArtifactHandle {path:string;root:string;header:Bundle|ShardedManifest;format:'embedded-v1'|'curriculos-abertos/sharded-v1';sha256:string;item_count:number;relation_count:number;parts:ShardPart[];collection_hashes:Partial<Record<'items'|'relations',string>>;records(kind:'items'|'relations'):AsyncGenerator<Learning|Relation>;}
export interface ArtifactInspection {publication:string;format:ArtifactHandle['format'];manifest_path:string;manifest_sha256:string;items:number;relations:number;sources:number;parts_verified:number;collection_hashes:Partial<Record<'items'|'relations',string>>;compressed_bytes:number;decoded_bytes:number;by_uf:Record<string,number>;coded_by_uf:Record<string,number>;stages_by_uf:Record<string,string[]>;samples:SampleReference[];national:SampleReference|null;item_errors:number;relation_errors:number;errors:{kind:string;id:string;message:string}[];passed:boolean;}
async function smallJson(path:string,max=8*1024*1024){assert.ok(statSync(path).size<=max,'Metadados excedem limite explícito; não carregar JSON nacional como metadados.');return JSON.parse(await readFile(path,'utf8')) as Record<string,unknown>;}
export async function latestAuditPublication(repoRoot=process.cwd()){const latest=await smallJson(resolve(repoRoot,'data/bundles/latest.json'),1024*1024);assert.equal(typeof latest.id,'string');return latest.id as string;}
/** repoRoot also permits verifying a restored tree without rewriting or following original part paths. */
export async function openAuditArtifact(publication:string,repoRoot=process.cwd()):Promise<ArtifactHandle> {
 assert.match(publication,/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,159}$/,'Identificador de publicação inválido');
 const root=resolve(repoRoot,'data/bundles');let path:string|undefined;let expected:Record<string,unknown>|undefined;
 const pointer=join(root,'latest.json');if(existsSync(pointer)){const latest=await smallJson(pointer,1024*1024);if(latest.id===publication&&typeof latest.path==='string'){path=resolve(repoRoot,latest.path);expected=latest;}}
 if(!path)path=[join(root,publication+'.manifest.json'),join(root,publication+'.json'),join(root,publication+'.json.gz')].find(p=>existsSync(p));
 assert.ok(path,'Artefato entregue correspondente à publicação servida não foi localizado');
 // Legacy support is deliberately bounded. National distribution must use shards rather than raising a string/heap limit.
 const loaded=await loadBundleFile(path,{root,expected,maxFileBytes:64*1024*1024,maxDecodedBytes:64*1024*1024});
 assert.equal(loaded.bundle.id,publication,'ID do manifesto diverge da publicação solicitada');
 if(loaded.bundle.format==='curriculos-abertos/sharded-v1'){
  validateShardedManifest(loaded.bundle);const manifest=loaded.bundle as unknown as ShardedManifest;const collection_hashes:Partial<Record<'items'|'relations',string>>={};
  return{path,root,header:manifest,format:manifest.format,sha256:loaded.file_sha256,item_count:manifest.item_count,relation_count:manifest.relation_count,parts:manifest.parts,collection_hashes,async *records(kind){const aggregate=createHash('sha256');for(const part of manifest.parts.filter(p=>p.kind===kind)){const located={...part,path:resolve(repoRoot,part.path)};for await(const record of shardRecords(located,root,chunk=>aggregate.update(chunk)))yield record;}collection_hashes[kind]=aggregate.digest('hex');}};
 }
 const legacy=loaded.bundle;assert.ok(Array.isArray(legacy.items)&&Array.isArray(legacy.relations),'Artefato legado não contém coleções');
 return{path,root,header:legacy,format:'embedded-v1',sha256:loaded.file_sha256,item_count:legacy.items.length,relation_count:legacy.relations.length,parts:[],collection_hashes:{},async *records(kind){for(const record of legacy[kind])yield record;}};
}
export function sampleReference(item:Learning):SampleReference{return{id:item.id,uf:item.uf,source_id:item.source_id,code:item.code,kind:item.kind,text_sha256:digestText(item.text),text_length:item.text.length,evidence_sha256:digestValue(item.evidence),positions_sha256:digestValue(item.positions)};}
export function matchSample(item:Learning,sample:SampleReference){assert.equal(item.id,sample.id);assert.equal(item.uf,sample.uf);assert.equal(item.source_id,sample.source_id);assert.equal(item.code,sample.code);assert.equal(item.kind,sample.kind);assert.equal(digestText(item.text),sample.text_sha256,'Texto canônico diverge da parte verificada');assert.equal(digestValue(item.evidence),sample.evidence_sha256,'Evidências divergem da parte verificada');assert.equal(digestValue(item.positions),sample.positions_sha256,'Posicionamentos divergem da parte verificada');}
export async function inspectAuditArtifact(artifact:ArtifactHandle):Promise<ArtifactInspection>{
 const sources=new Map<string,Source>(artifact.header.sources.map(s=>[s.id,s]));assert.equal(sources.size,artifact.header.sources.length,'IDs de fontes duplicados');
 if(typeof artifact.header.source_count==='number')assert.equal(artifact.header.source_count,sources.size,'Contagem de fontes difere do manifesto');
 const ids=new Set<string>(),relationIds=new Set<string>(),parents=new Map<string,string>();const byUF:Record<string,number>={},coded:Record<string,number>={};const stages=new Map<string,Set<string>>(),samples=new Map<string,SampleReference>();const longest:SampleReference[]=[];let national:SampleReference|null=null,items=0,relations=0,itemErrors=0,relationErrors=0;const errors:ArtifactInspection['errors']=[];
 const failure=(kind:string,id:string,error:unknown)=>{if(errors.length<50)errors.push({kind,id,message:error instanceof Error?error.message:String(error)});};
 for await(const record of artifact.records('items')){
  const item=record as Learning;items++;
  try{
   LearningSchema.parse(item);assert.equal(typeof item.id,'string');assert.ok(item.id.length>0&&!ids.has(item.id),'ID ausente ou duplicado');ids.add(item.id);if(item.parent_id){assert.notEqual(item.parent_id,item.id);parents.set(item.id,item.parent_id);}
   const source=sources.get(item.source_id);assert.ok(source,'Fonte inexistente');assert.equal(item.uf,source.uf,'UF diverge da fonte');assert.match(source.sha256||'',/^[a-f0-9]{64}$/,'Item extraído exige hash real do artefato da fonte');
   assert.equal(typeof item.text,'string');assert.ok(item.text.trim(),'Texto canônico vazio');assert.equal(typeof item.normalized_text,'string');assert.equal(typeof item.kind,'string');assert.equal(typeof item.curriculum_id,'string');assert.ok(item.curriculum_id);assert.ok(item.code===null||typeof item.code==='string');
   assert.ok(Array.isArray(item.positions));assert.ok(item.positions.length||typeof item.position_unknown_reason==='string'&&item.position_unknown_reason.trim().length>0,'Posicionamento ausente sem razão explícita');
   for(const p of item.positions){assert.ok(source.stages.includes(p.stage),'Etapa não declarada na fonte');assert.ok(p.years===null||Array.isArray(p.years)&&p.years.every(y=>Number.isInteger(y)&&y>=1&&y<=12),'Anos/blocos inválidos');}
   assert.ok(Array.isArray(item.evidence)&&item.evidence.length>0,'Evidência ausente');assert.ok(item.evidence.some(e=>e.source_id===item.source_id),'Evidência primária ausente');for(const e of item.evidence){assert.ok(sources.has(e.source_id),'Fonte da evidência inexistente');assert.ok(typeof e.excerpt==='string'&&e.excerpt.trim());assert.ok(e.page!==null&&Number.isInteger(e.page)&&e.page>0||typeof e.section==='string'&&e.section.trim(),'Localizador ausente');}
   assert.ok(item.is_fixture!==true&&item.synthetic!==true,'Registro sintético no corpus');
   byUF[item.uf]=(byUF[item.uf]||0)+1;if(item.code)coded[item.uf]=(coded[item.uf]||0)+1;const scope=stages.get(item.uf)||new Set<string>();for(const p of item.positions)scope.add(p.stage);stages.set(item.uf,scope);
   const reference=sampleReference(item);const positions=item.positions.length?item.positions:[null];for(const p of positions){const key=[item.source_id,p?.stage||'unknown',p?.component||p?.area||'unknown'].join('|');if(!samples.has(key))samples.set(key,reference);}
   if(item.code&&/[.*-]/.test(item.code)&&!samples.has('edge-local:'+item.uf))samples.set('edge-local:'+item.uf,reference);
   if(item.positions.length>1&&!samples.has('edge-multiple-positions'))samples.set('edge-multiple-positions',reference);
   if(item.evidence.length>1&&!samples.has('edge-multiple-evidence'))samples.set('edge-multiple-evidence',reference);
   longest.push(reference);longest.sort((a,b)=>b.text_length-a.text_length||a.id.localeCompare(b.id));if(longest.length>3)longest.pop();
   if(!national&&item.uf==='BR'&&item.code&&!['secao_normativa','referencia_no_documento'].includes(item.kind))national=reference;
  }catch(error){itemErrors++;failure('item',typeof item.id==='string'?item.id:'invalid-id',error);}
 }
 for(const[id,parent]of parents)if(!ids.has(parent)){itemErrors++;failure('hierarchy',id,new Error('Pai inexistente'));}
 const completed=new Set<string>();for(const id of parents.keys()){const active=new Set<string>();let current:string|undefined=id;while(current&&parents.has(current)&&!completed.has(current)){if(active.has(current)){itemErrors++;failure('hierarchy',id,new Error('Hierarquia cíclica'));break;}active.add(current);current=parents.get(current);}for(const entry of active)completed.add(entry);}
 for await(const record of artifact.records('relations')){
  const r=record as Relation;relations++;
  try{RelationSchema.parse(r);assert.equal(typeof r.id,'string');assert.ok(r.id&&!relationIds.has(r.id),'ID relação ausente ou duplicado');relationIds.add(r.id);for(const field of ['relation_type','origin','technical_validation_status','pedagogical_review_status','publication_status','method'])assert.ok(typeof r[field]==='string'&&r[field]);assert.ok(Array.isArray(r.members)&&r.members.some(m=>m.role==='source')&&r.members.some(m=>m.role==='target'),'Direção ausente');const members=new Set<string>();for(const m of r.members){assert.ok(ids.has(m.item_id),'Membro inexistente');assert.ok(['source','target'].includes(m.role));assert.equal(typeof m.scope,'string');const key=m.item_id+':'+m.role;assert.ok(!members.has(key),'Membro repetido');members.add(key);}assert.ok(Array.isArray(r.evidence));for(const e of r.evidence)assert.ok(sources.has(e.source_id));if(/code|código|codigo|literal/i.test(r.method)&&/automatic|automática|automatica/i.test(r.origin))assert.ok(!/equiv|official|oficial/i.test(r.relation_type),'Inferência automática marcada equivalente/oficial');if(/human|humana/.test(r.pedagogical_review_status))assert.ok(Array.isArray(r.review_events)&&r.review_events.some(event=>event&&typeof event==='object'&&event.actor_type==='human'&&typeof event.actor_id==='string'&&event.actor_id),'Revisão humana sem evento humano identificado');}catch(error){relationErrors++;failure('relation',typeof r.id==='string'?r.id:'invalid-id',error);}
 }
 if(artifact.format==='curriculos-abertos/sharded-v1'){const identity=artifact.header.content_identity as {items_jsonl_sha256?:string;relations_jsonl_sha256?:string}|undefined;assert.match(identity?.items_jsonl_sha256||'',/^[a-f0-9]{64}$/,'Identidade global de itens ausente');assert.match(identity?.relations_jsonl_sha256||'',/^[a-f0-9]{64}$/,'Identidade global de relações ausente');assert.equal(artifact.collection_hashes.items,identity?.items_jsonl_sha256,'Identidade global da coleção de itens diverge dos bytes JSONL lidos');assert.equal(artifact.collection_hashes.relations,identity?.relations_jsonl_sha256,'Identidade global da coleção de relações diverge dos bytes JSONL lidos');}
 assert.equal(items,artifact.item_count,'Contagem de itens real difere do manifesto');assert.equal(relations,artifact.relation_count,'Contagem de relações real difere do manifesto');
 for(const entry of longest)samples.set('edge-long:'+entry.id,entry);
 const unique=new Map([...samples.values()].map(row=>[row.id,row]));
 return{publication:artifact.header.id,format:artifact.format,manifest_path:artifact.path,manifest_sha256:artifact.sha256,items,relations,sources:sources.size,parts_verified:artifact.parts.length,collection_hashes:artifact.collection_hashes,compressed_bytes:artifact.parts.reduce((n,p)=>n+p.bytes,0),decoded_bytes:artifact.parts.reduce((n,p)=>n+p.decoded_bytes,0),by_uf:byUF,coded_by_uf:coded,stages_by_uf:Object.fromEntries([...stages].map(([uf,values])=>[uf,[...values].sort()])),samples:[...unique.values()].sort((a,b)=>a.id.localeCompare(b.id)),national,item_errors:itemErrors,relation_errors:relationErrors,errors,passed:itemErrors===0&&relationErrors===0};
}
