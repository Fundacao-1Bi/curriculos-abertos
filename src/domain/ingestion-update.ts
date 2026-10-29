import {createHash} from 'node:crypto';
import {relative,resolve} from 'node:path';
import {readFile} from 'node:fs/promises';
import type pg from 'pg';
import {pool} from '../db/client';
import type {Learning,Relation,Source} from '../shared/contracts';
import {DomainError} from './errors';
import {loadBundleFile} from './bundle-file';
import {importShardedManifest,shardRecords,verifyShardedManifest,type ShardedManifest} from './shards';
import {writeShardedArtifact} from './shard-writer';
import {publishVisibility,type PublicationActor} from './visibility';
import {mergeIngestionCoverage} from './ingestion-coverage';
import {prepareIngestionProvenance,assertIngestionProvenanceUnchanged,provenanceDigest,type IngestionProvenanceInput,type PreparedIngestionProvenance} from './ingestion-provenance';

const VERSION='base-plus-source-update-v1';
const digest=(value:string)=>createHash('sha256').update(value).digest('hex');
// JSON numeric spelling (1.0/1) is not a changed value; exact JSONB equality is checked separately below.
const semanticJson=(text:string)=>JSON.stringify(JSON.parse(text));
async function diagnosticStep<T>(label:string,action:()=>Promise<T>):Promise<T>{try{return await action();}catch(error){if(error instanceof Error)error.message=label+': '+error.message;throw error;}}
const hashValid=(value:string)=>/^[a-f0-9]{64}$/.test(value);
function targets(input:string[]){if(!Array.isArray(input)||!input.length||input.length>500||input.some(x=>typeof x!=='string'||!x||x.length>500)||new Set(input).size!==input.length)throw new DomainError(422,'INVALID_UPDATE_TARGETS','Declare fontes alvo únicas e explícitas.');return[...input].sort();}
async function baseRecord(client:pg.PoolClient,id:string){
 const row=(await client.query(`SELECT p.id,p.sha256,p.schema_version,p.created_at,p.extraction_revision,p.mapping_revision,(p.payload-'items'-'relations'-'sources'-'coverage'-'parts') AS metadata FROM publications p JOIN publication_visibility v ON v.publication_id=p.id AND v.status='published' WHERE p.id=$1`,[id])).rows[0];
 if(!row)throw new DomainError(404,'PUBLICATION_NOT_FOUND','Base publicada inexistente.');return row;
}
async function* queryRecords<T>(client:pg.PoolClient,table:'items'|'relations'|'ingestion_items'|'ingestion_relations',publication?:string,where='',signal?:AbortSignal):AsyncGenerator<T>{
 let last='';for(;;){signal?.throwIfAborted();const values=publication?[publication,last]:[last];const rows=await client.query(`SELECT id,payload FROM ${table} WHERE ${publication?'publication_id=$1 AND id>$2':'id>$1'} ${where} ORDER BY id LIMIT 50`,values);if(!rows.rowCount)break;for(const row of rows.rows){signal?.throwIfAborted();last=row.id;yield row.payload as T;}}
}
/** Immutable BR context exported from the pinned DB snapshot, never from unrelated extraction caches. */
export async function exportIngestionBase(input:{base_publication:string;directory:string}){
 const client=await pool.connect();try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');const base=await baseRecord(client,input.base_publication);
  const sources=(await client.query("SELECT payload FROM sources WHERE publication_id=$1 AND uf='BR' ORDER BY id",[base.id])).rows.map(x=>x.payload as Source);
  const count=(await client.query("SELECT count(*)::int count FROM items WHERE publication_id=$1 AND uf='BR'",[base.id])).rows[0].count;if(!count||!sources.length)throw new DomainError(422,'NATIONAL_CONTEXT_UNAVAILABLE','A base fixada não contém contexto nacional; a atualização não pode perder ligações por ausência de BR.');
  if(!/^\d+\.\d+\.\d+$/.test(base.schema_version))throw new DomainError(422,'UNSUPPORTED_CONTEXT_SCHEMA','A base exige versão de schema identificada por arquivo imutável.');
  const schemaPath=`data/schema/${base.schema_version}.json`,schemaSha=createHash('sha256').update(await readFile(schemaPath)).digest('hex');
  if(base.metadata.schema_sha256&&base.metadata.schema_sha256!==schemaSha)throw new DomainError(409,'CONTEXT_SCHEMA_CHANGED','Schema da publicação base diverge do arquivo imutável.');
  const header={id:'ca-context-'+digest('ingestion-national-context-v1\0'+base.id+'\0'+base.sha256).slice(0,32),schema_version:base.schema_version,schema_path:schemaPath,schema_sha256:schemaSha,created_at:new Date(base.created_at).toISOString(),extraction_revision:base.extraction_revision,mapping_revision:base.mapping_revision,sources,coverage:[],changelog:[{type:'pinned_national_context',base_publication:base.id,description:'Contexto BR exato da publicação fixada, para recalcular vínculos das fontes alvo. Não é publicação nacional completa.'}],publication_kind:'ingestion_national_context',base_publication:base.id,base_publication_sha256:base.sha256,national_release_ready:false};
  const result=await writeShardedArtifact(header,{items:queryRecords<Learning>(client,'items',base.id,"AND uf='BR'"),relations:(async function*(){})()},{directory:input.directory});
  await client.query('COMMIT');return{artifact:relative(process.cwd(),result.filename),artifact_sha256:result.sha256,base_publication:base.id,base_publication_sha256:base.sha256,context_publication:result.manifest.id};
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
}
type SourceProof={source_id:string;items:number;source_sha256:string;items_sha256:string};
async function sourceProofs(client:pg.PoolClient,publication:string,excluded:string[]):Promise<SourceProof[]>{
 const sources=await client.query('SELECT id,payload::text AS content FROM sources WHERE publication_id=$1 AND NOT(id=ANY($2::text[])) ORDER BY id',[publication,excluded]);
 const summaries=new Map(sources.rows.map(source=>[source.id as string,{source_id:source.id as string,items:0,source_sha256:digest(semanticJson(source.content)),hash:createHash('sha256')}]));
 // One indexed scan per publication, rather than a fresh global item scan for each of hundreds of sources.
 let last='';for(;;){const rows=await client.query('SELECT id,source_id,payload::text AS content FROM items WHERE publication_id=$1 AND NOT(source_id=ANY($2::text[])) AND id>$3 ORDER BY id LIMIT 50',[publication,excluded,last]);if(!rows.rowCount)break;for(const row of rows.rows){const source=summaries.get(row.source_id);if(!source)throw new DomainError(409,'UPDATE_DANGLING_SOURCE','Item sem fonte no inventário da publicação verificada.');source.hash.update(row.id).update('\0').update(semanticJson(row.content)).update('\n');source.items++;last=row.id;}}
 return[...summaries.values()].map(source=>({source_id:source.source_id,items:source.items,source_sha256:source.source_sha256,items_sha256:source.hash.digest('hex')}));
}
async function relationProof(client:pg.PoolClient,publication:string,excluded:string[],comparePublication?:string){
 const hash=createHash('sha256');let count=0,last='';
 for(;;){
  // Apply LIMIT before inspecting membership. A correlated anti-join rebuilt the entire source/member join for every page.
  const rows=(await client.query('SELECT id,payload::text AS content FROM relations WHERE publication_id=$1 AND id>$2 ORDER BY id LIMIT 50',[publication,last])).rows;
  if(!rows.length)break;
  const records=rows.map(row=>{const record=JSON.parse(row.content) as Relation;return{id:row.id as string,record,content:JSON.stringify(record)};});
  const memberIds=[...new Set(records.flatMap(row=>row.record.members.map(member=>member.item_id)))],membership=new Map<string,boolean>();
  // Each lookup uses the publication/id primary key; neither a global item scan nor a full member join is repeated.
  for(let index=0;index<memberIds.length;index+=250){const ids=memberIds.slice(index,index+250);const found=await client.query('SELECT id,source_id=ANY($3::text[]) AS target FROM items WHERE publication_id=$1 AND id=ANY($2::text[])',[publication,ids,excluded]);for(const item of found.rows)membership.set(item.id,item.target);if(found.rows.length!==ids.length)throw new DomainError(409,'UPDATE_DANGLING_MEMBER','Vínculo contém membro inexistente na publicação verificada.');}
  const outside=records.filter(row=>!row.record.evidence.some(e=>excluded.includes(e.source_id))&&!row.record.members.some(member=>membership.get(member.item_id)));
  if(comparePublication&&outside.length){const changed=(await client.query('SELECT b.id FROM relations b LEFT JOIN relations a ON a.publication_id=$3 AND a.id=b.id WHERE b.publication_id=$1 AND b.id=ANY($2::text[]) AND b.payload IS DISTINCT FROM a.payload LIMIT 1',[publication,outside.map(row=>row.id),comparePublication])).rows[0];if(changed)throw new DomainError(409,'OUTSIDE_CANONICAL_VALUE_CHANGED','Valor canônico de relação fora do alvo mudou.');}
  for(const row of outside){hash.update(row.id).update('\0').update(row.content).update('\n');count++;}
  last=rows.at(-1)!.id;
 }
 return{count,sha256:hash.digest('hex')};
}
function rowTargets(row:Record<string,unknown>,ids:string[]){return Array.isArray(row.source_ids)&&row.source_ids.some(s=>ids.includes(String(s)));}
const coverageKey=(row:Record<string,unknown>)=>JSON.stringify([row.uf??null,row.stage??null,row.component??null]);
async function coverageProof(client:pg.PoolClient,publication:string,excluded:string[],affectedKeys:string[]=[]){
 const rows=(await client.query('SELECT payload,payload::text AS content FROM publication_coverage WHERE publication_id=$1 ORDER BY row_index',[publication])).rows;
 const hash=createHash('sha256');let count=0;for(const row of rows)if(!rowTargets(row.payload,excluded)&&!affectedKeys.includes(coverageKey(row.payload))){hash.update(semanticJson(row.content)).update('\n');count++;}return{count,sha256:hash.digest('hex')};
}
/** Full canonical payloads are hashed one bounded page at a time; no text/evidence/position fields are omitted. */
export async function verifyGlobalIngestionPreservation(basePublication:string,candidatePublication:string,targetSourceIds:string[],actorId='curriculos-abertos:global-update-verifier'){
 const target=targets(targetSourceIds),client=await pool.connect();try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
  const candidate=(await client.query("SELECT payload->'update_scope' AS scope FROM publications WHERE id=$1",[candidatePublication])).rows[0];if(!candidate||candidate.scope?.mode!=='base-plus-source-update'||candidate.scope.base_publication!==basePublication||JSON.stringify(candidate.scope.target_source_ids)!==JSON.stringify(target))throw new DomainError(409,'UPDATE_LINEAGE_MISMATCH','Linhagem do candidato não corresponde à base e fontes declaradas.');
  const before=await diagnosticStep('base source preservation hashes',()=>sourceProofs(client,basePublication,target)),after=await diagnosticStep('candidate source preservation hashes',()=>sourceProofs(client,candidatePublication,target));
  if(JSON.stringify(before)!==JSON.stringify(after))throw new DomainError(409,'OUTSIDE_SOURCE_CHANGED','Fonte ou item fora do escopo foi removido ou alterado.');
  const affectedKeys=Array.isArray(candidate.scope.affected_coverage_keys)?candidate.scope.affected_coverage_keys as string[]:[];
  const actualCoverage=(await client.query('SELECT payload FROM publication_coverage WHERE publication_id=ANY($1::text[])',[ [basePublication,candidatePublication] ])).rows.map(x=>x.payload as Record<string,unknown>);
  const actualAffected=[...new Set(actualCoverage.filter(row=>rowTargets(row,target)).map(coverageKey))].sort();
  if(JSON.stringify([...affectedKeys].sort())!==JSON.stringify(actualAffected))throw new DomainError(409,'UPDATE_COVERAGE_SCOPE_MISMATCH','Escopo declarado de cobertura não coincide com as fontes alvo; a prova não pode excluir outros recortes.');
  const beforeRelations=await diagnosticStep('base unaffected relation hashes',()=>relationProof(client,basePublication,target,candidatePublication)),afterRelations=await diagnosticStep('candidate unaffected relation hashes',()=>relationProof(client,candidatePublication,target)),beforeCoverage=await coverageProof(client,basePublication,target,affectedKeys),afterCoverage=await coverageProof(client,candidatePublication,target,affectedKeys);
  if(JSON.stringify(beforeRelations)!==JSON.stringify(afterRelations))throw new DomainError(409,'OUTSIDE_RELATIONS_CHANGED','Relações fora do escopo foram removidas ou alteradas.');
  if(JSON.stringify(beforeCoverage)!==JSON.stringify(afterCoverage))throw new DomainError(409,'OUTSIDE_COVERAGE_CHANGED','Cobertura fora do escopo foi removida ou alterada.');
  // This database-side check also catches unsafe JS numeric rounding, which a serialization hash alone cannot prove absent.
  for(const table of ['sources','items'] as const){const filter=table==='sources'?'b.id':'b.source_id';const changed=(await diagnosticStep('canonical equality '+table,()=>client.query(`SELECT b.id FROM ${table} b LEFT JOIN ${table} a ON a.publication_id=$3 AND a.id=b.id WHERE b.publication_id=$1 AND NOT(${filter}=ANY($2::text[])) AND b.payload IS DISTINCT FROM a.payload LIMIT 1`,[basePublication,target,candidatePublication]))).rows[0];if(changed)throw new DomainError(409,'OUTSIDE_CANONICAL_VALUE_CHANGED','Valor canônico fora do alvo mudou; a atualização foi recusada, inclusive para números que perderiam precisão.');}
  const coverageFilter=`NOT EXISTS(SELECT 1 FROM jsonb_array_elements_text(coalesce(payload->'source_ids','[]'::jsonb)) sid WHERE sid=ANY($2::text[])) AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements($4::jsonb) k WHERE k=jsonb_build_array(payload->'uf',payload->'stage',payload->'component'))`;
  const changedCoverage=(await client.query(`WITH b AS(SELECT row_number() OVER(ORDER BY row_index) n,payload FROM publication_coverage WHERE publication_id=$1 AND ${coverageFilter}),a AS(SELECT row_number() OVER(ORDER BY row_index) n,payload FROM publication_coverage WHERE publication_id=$3 AND ${coverageFilter}) SELECT b.n FROM b FULL JOIN a USING(n) WHERE b.payload IS DISTINCT FROM a.payload LIMIT 1`,[basePublication,target,candidatePublication,JSON.stringify(affectedKeys.map(key=>JSON.parse(key)))])).rows[0];if(changedCoverage)throw new DomainError(409,'OUTSIDE_CANONICAL_VALUE_CHANGED','Valor canônico de cobertura fora do alvo mudou.');
  const baseSources=(await client.query('SELECT id FROM sources WHERE publication_id=$1 ORDER BY id',[basePublication])).rows.map(x=>x.id as string).sort();
  const sourceIds=(await client.query('SELECT id FROM sources WHERE publication_id=$1 ORDER BY id',[candidatePublication])).rows.map(x=>x.id as string).sort();
  const expected=[...new Set([...baseSources,...target])].sort();if(JSON.stringify(expected)!==JSON.stringify(sourceIds))throw new DomainError(409,'UPDATE_INVENTORY_MISMATCH','Inventário global difere da união da base com as fontes alvo.');
  await client.query('COMMIT');
  return{mode:'base-plus-source-update' as const,base_publication:basePublication,candidate_publication:candidatePublication,base_source_ids:baseSources,target_source_ids:target,affected_coverage_keys:affectedKeys,unaffected_sources:before.map((b,index)=>({source_id:b.source_id,before:{items:b.items,source_sha256:b.source_sha256,items_sha256:b.items_sha256},after:{items:after[index].items,source_sha256:after[index].source_sha256,items_sha256:after[index].items_sha256}})),relations_excluding_target:{before_count:beforeRelations.count,after_count:afterRelations.count,before_sha256:beforeRelations.sha256,after_sha256:afterRelations.sha256},coverage_excluding_target:{before_count:beforeCoverage.count,after_count:afterCoverage.count,before_sha256:beforeCoverage.sha256,after_sha256:afterCoverage.sha256},actor_id:actorId,actor_type:'automated' as const,method:VERSION+': ordered complete payload SHA-256 with normalized JSON number spelling AND independent PostgreSQL JSONB value equality (including exact numeric precision), complete inventory/counts, immutable base and outside-target preservation'};
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
}

export interface GlobalIngestionInput {base_publication:string;target_source_ids:string[];raw_artifact:string;raw_artifact_sha256:string;base_artifact_sha256:string;output_directory:string;actor_id:string;provenance?:IngestionProvenanceInput;signal?:AbortSignal;}
/** Builds a real global artifact, imports it privately, then independently proves outside-target preservation. */
export async function prepareGlobalIngestionUpdate(input:GlobalIngestionInput){
 input.signal?.throwIfAborted();
 const target=targets(input.target_source_ids);if(!input.actor_id||!hashValid(input.raw_artifact_sha256)||!hashValid(input.base_artifact_sha256))throw new DomainError(422,'INVALID_UPDATE_RECEIPT','Ator e checksums fixados são obrigatórios.');
 const artifact=await loadBundleFile(input.raw_artifact,{expected:{sha256:input.raw_artifact_sha256}}),raw=artifact.bundle as unknown as ShardedManifest;
 await verifyShardedManifest(raw);input.signal?.throwIfAborted();
 const technicalRequired=raw.sources.some(source=>input.target_source_ids.includes(source.id)&&(['am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em'].includes(source.id)||Object.hasOwn(source,'technical_supersessions')||Object.hasOwn(source,'technical_extraction_corrections')));
 if(technicalRequired&&!input.provenance)throw new DomainError(422,'INGESTION_PROVENANCE_REQUIRED','Esta fonte exige etapa raster/técnica e recibos de orquestração verificáveis.');
 if(raw.publication_kind!=='source_update_receipt'||raw.base_publication!==input.base_publication||raw.base_artifact_sha256!==input.base_artifact_sha256||JSON.stringify(targets(raw.target_source_ids as string[]))!==JSON.stringify(target))throw new DomainError(409,'RAW_UPDATE_SCOPE_MISMATCH','Recibo parcial não demonstra a mesma base, contexto SHA e fontes alvo fixadas no job.');
 const client=await pool.connect();let global:Awaited<ReturnType<typeof writeShardedArtifact>>,provenance:PreparedIngestionProvenance|undefined;
 try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ');const base=await baseRecord(client,input.base_publication);
  if(raw.base_publication_sha256!==base.sha256)throw new DomainError(409,'RAW_BASE_CHECKSUM_MISMATCH','Checksum da base no recibo não corresponde à publicação fixada.');
  const baseSources=(await client.query('SELECT payload FROM sources WHERE publication_id=$1 ORDER BY id',[base.id])).rows.map(x=>x.payload as Source);
  const nationalSources=baseSources.filter(s=>s.uf==='BR'),contextIds=nationalSources.map(s=>s.id).sort();
  if(target.some(id=>nationalSources.some(s=>s.id===id))||raw.sources.some(s=>target.includes(s.id)&&s.uf==='BR'))throw new DomainError(422,'NATIONAL_UPDATE_REQUIRES_GLOBAL_REBUILD','Atualização do referencial nacional exige reconstrução explícita de todos os vínculos dependentes.');
  if(JSON.stringify([...(raw.context_source_ids as string[]??[])].sort())!==JSON.stringify(contextIds))throw new DomainError(409,'NATIONAL_CONTEXT_MISMATCH','O contexto BR não corresponde ao inventário da base fixada.');
  if(raw.sources.some(s=>!target.includes(s.id)&&!contextIds.includes(s.id))||target.some(id=>!raw.sources.some(s=>s.id===id)))throw new DomainError(409,'RAW_SOURCE_SCOPE_MISMATCH','O recibo deve conter exatamente fontes alvo e o contexto BR fixado.');
  for(const source of nationalSources){const supplied=raw.sources.find(s=>s.id===source.id);if(!supplied||(await client.query('SELECT $1::jsonb=$2::jsonb AS equal',[JSON.stringify(source),JSON.stringify(supplied)])).rows[0].equal!==true)throw new DomainError(409,'NATIONAL_CONTEXT_CHANGED','Metadados BR diferem da base imutável.');}
  for(const source of baseSources.filter(s=>target.includes(s.id))){const replacement=raw.sources.find(s=>s.id===source.id)!;const unchanged=(await client.query('SELECT $1::jsonb=$2::jsonb AS equal',[JSON.stringify(source),JSON.stringify(replacement)])).rows[0].equal;if(!unchanged){const dependency=(await client.query("SELECT i.id FROM items i CROSS JOIN LATERAL jsonb_array_elements(i.evidence)e WHERE i.publication_id=$1 AND NOT(i.source_id=ANY($2::text[])) AND e->>'source_id'=$3 LIMIT 1",[base.id,target,source.id])).rows[0];if(dependency)throw new DomainError(409,'CROSS_SOURCE_EVIDENCE_DEPENDENCY','Itens fora do alvo citam a edição desta fonte. A alteração exige escopo editorial explícito dessas dependências.');}}
  const sourceUnion=[...baseSources.filter(s=>!target.includes(s.id)),...raw.sources.filter(s=>target.includes(s.id))].sort((a,b)=>a.id.localeCompare(b.id));
  if(input.provenance)provenance=await prepareIngestionProvenance(client,{base:{id:base.id,sha256:base.sha256},target_source_ids:target,raw,effective_raw_receipt:{publication:raw.id,artifact:relative(process.cwd(),resolve(input.raw_artifact)),artifact_sha256:input.raw_artifact_sha256},provenance:input.provenance,signal:input.signal});
  await client.query('CREATE TEMP TABLE ingestion_scope(base_id text,target_ids text[]) ON COMMIT DROP');await client.query('INSERT INTO ingestion_scope VALUES($1,$2)',[base.id,target]);
  await client.query('CREATE TEMP TABLE ingestion_raw_items(id text PRIMARY KEY,source_id text NOT NULL,kind text NOT NULL,positions jsonb NOT NULL,evidence jsonb NOT NULL,payload jsonb NOT NULL) ON COMMIT DROP');
  await client.query('CREATE INDEX ON ingestion_raw_items(source_id)');
  await client.query('CREATE TEMP TABLE ingestion_raw_relations(id text PRIMARY KEY,payload jsonb NOT NULL) ON COMMIT DROP');
  for(const part of raw.parts.filter(p=>p.kind==='items')){input.signal?.throwIfAborted();let batch:Learning[]=[];const flush=async()=>{input.signal?.throwIfAborted();if(!batch.length)return;await client.query(`INSERT INTO ingestion_raw_items SELECT x.id,x.source_id,x.kind,x.positions,x.evidence,x.payload FROM jsonb_to_recordset($1::jsonb)x(id text,source_id text,kind text,positions jsonb,evidence jsonb,payload jsonb)`,[JSON.stringify(batch.map(i=>({...i,payload:i})))]);batch=[];};for await(const row of shardRecords(part)){const item=row as Learning;if(!target.includes(item.source_id)&&!contextIds.includes(item.source_id))throw new DomainError(409,'RAW_ITEM_OUTSIDE_SCOPE','Item fora do alvo ou contexto BR.');batch.push(item);if(batch.length>=50)await flush();}await flush();}
  const context=(await client.query(`SELECT (SELECT count(*)::int FROM items WHERE publication_id=$1 AND uf='BR') AS expected,(SELECT count(*)::int FROM ingestion_raw_items WHERE source_id=ANY($2::text[])) AS supplied,(SELECT count(*)::int FROM ingestion_raw_items r JOIN items b ON b.publication_id=$1 AND b.id=r.id AND b.payload=r.payload WHERE r.source_id=ANY($2::text[])) AS equal`,[base.id,contextIds])).rows[0];
  if(!context.expected||context.expected!==context.supplied||context.expected!==context.equal)throw new DomainError(409,'NATIONAL_CONTEXT_CHANGED','IDs, textos ou metadados BR do recibo não coincidem integralmente com a base fixada.');
  const collision=(await client.query('SELECT r.id FROM ingestion_raw_items r JOIN items b ON b.publication_id=$1 AND b.id=r.id WHERE r.source_id=ANY($2::text[]) AND NOT(b.source_id=ANY($2::text[])) LIMIT 1',[base.id,target])).rows[0];if(collision)throw new DomainError(409,'OUTSIDE_ITEM_ID_COLLISION','ID do alvo colide com um item fora do recorte.');
  for(const id of target){const count=(await client.query('SELECT count(*)::int count FROM ingestion_raw_items WHERE source_id=$1',[id])).rows[0].count;if(!count)throw new DomainError(422,'EMPTY_TARGET_EXTRACTION','Extração alvo vazia; exclusão total exige uma operação editorial explícita.');}
  for(const part of raw.parts.filter(p=>p.kind==='relations')){input.signal?.throwIfAborted();let batch:Relation[]=[];const flush=async()=>{input.signal?.throwIfAborted();if(!batch.length)return;await client.query('INSERT INTO ingestion_raw_relations SELECT x.id,x.payload FROM jsonb_to_recordset($1::jsonb)x(id text,payload jsonb)',[JSON.stringify(batch.map(r=>({id:r.id,payload:r})))]);batch=[];};for await(const row of shardRecords(part)){const relation=row as Relation;batch.push(relation);if(batch.length>=50)await flush();}await flush();}
  const irrelevant=(await client.query(`SELECT r.id FROM ingestion_raw_relations r WHERE NOT EXISTS(SELECT 1 FROM jsonb_array_elements(r.payload->'members')m JOIN ingestion_raw_items i ON i.id=m->>'item_id' WHERE i.source_id=ANY($1::text[])) LIMIT 1`,[target])).rows[0];if(irrelevant)throw new DomainError(409,'RAW_RELATION_OUTSIDE_SCOPE','Relação do recibo não toca nenhuma fonte alvo.');
  const crossSource=(await client.query(`SELECT r.id FROM relations r JOIN relation_members m ON m.publication_id=r.publication_id AND m.relation_id=r.id JOIN items i ON i.publication_id=m.publication_id AND i.id=m.item_id WHERE r.publication_id=$1 AND m.role='source' AND i.uf<>'BR' AND NOT(i.source_id=ANY($2::text[])) AND EXISTS(SELECT 1 FROM relation_members t JOIN items ti ON ti.publication_id=t.publication_id AND ti.id=t.item_id WHERE t.publication_id=r.publication_id AND t.relation_id=r.id AND ti.source_id=ANY($2::text[])) AND NOT EXISTS(SELECT 1 FROM ingestion_raw_relations rr CROSS JOIN LATERAL jsonb_array_elements(rr.payload->'members')rm WHERE rr.id=r.id AND rm->>'item_id'=m.item_id AND rm->>'role'=m.role AND rm->>'scope'=m.scope) LIMIT 1`,[base.id,target])).rows[0];
  if(crossSource)throw new DomainError(409,'CROSS_SOURCE_RELATION_DEPENDENCY','Uma relação muitos-para-muitos também contém fontes locais fora do alvo. A atualização parcial não pode perder esses membros; inclua explicitamente as dependências.');
  await client.query(`CREATE TEMP VIEW ingestion_items AS SELECT i.id,i.source_id,i.kind,i.positions,i.evidence,i.payload FROM items i CROSS JOIN ingestion_scope s WHERE i.publication_id=s.base_id AND NOT(i.source_id=ANY(s.target_ids)) UNION ALL SELECT r.id,r.source_id,r.kind,r.positions,r.evidence,r.payload FROM ingestion_raw_items r CROSS JOIN ingestion_scope s WHERE r.source_id=ANY(s.target_ids)`);
  await client.query(`CREATE TEMP TABLE ingestion_retained_relations ON COMMIT DROP AS SELECT r.id,r.payload FROM relations r CROSS JOIN ingestion_scope s WHERE r.publication_id=s.base_id AND NOT EXISTS(SELECT 1 FROM relation_members m JOIN items i ON i.publication_id=m.publication_id AND i.id=m.item_id WHERE m.publication_id=r.publication_id AND m.relation_id=r.id AND i.source_id=ANY(s.target_ids)) AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(r.payload->'evidence')e WHERE e->>'source_id'=ANY(s.target_ids))`);
  await client.query('CREATE UNIQUE INDEX ON ingestion_retained_relations(id)');
  const relCollision=(await client.query('SELECT r.id FROM ingestion_raw_relations r JOIN ingestion_retained_relations b ON b.id=r.id LIMIT 1')).rows[0];if(relCollision)throw new DomainError(409,'OUTSIDE_RELATION_ID_COLLISION','Relação do alvo colide com vínculo fora do escopo.');
  await client.query('CREATE TEMP VIEW ingestion_relations AS SELECT id,payload FROM ingestion_retained_relations UNION ALL SELECT id,payload FROM ingestion_raw_relations');
  await client.query(`CREATE TEMP TABLE ingestion_members ON COMMIT DROP AS SELECT r.id AS relation_id,m->>'item_id' AS item_id,m->>'role' AS role,m->>'scope' AS scope FROM ingestion_relations r CROSS JOIN LATERAL jsonb_array_elements(r.payload->'members')m`);await client.query('CREATE INDEX ON ingestion_members(item_id)');
  const dangling=(await client.query('SELECT m.item_id FROM ingestion_members m LEFT JOIN ingestion_items i ON i.id=m.item_id WHERE i.id IS NULL LIMIT 1')).rows[0];if(dangling)throw new DomainError(409,'UPDATE_DANGLING_MEMBER','Um vínculo recalculado ou preservado aponta para item ausente.');
  const baseCoverage=(await client.query('SELECT payload FROM publication_coverage WHERE publication_id=$1 ORDER BY row_index',[base.id])).rows.map(x=>x.payload);
  const coverage=await mergeIngestionCoverage(client,baseCoverage,raw.coverage as Record<string,unknown>[],target,sourceUnion);
  const affectedKeys=[...new Set([...baseCoverage,...raw.coverage as Record<string,unknown>[]].filter(row=>rowTargets(row,target)).map(coverageKey))].sort();
  const preservation={unaffected_sources:await sourceProofs(client,base.id,target),relations_excluding_target:await relationProof(client,base.id,target),coverage_excluding_target:await coverageProof(client,base.id,target,affectedKeys)};
  const updateScope={mode:'base-plus-source-update',version:VERSION,base_publication:base.id,base_publication_sha256:base.sha256,base_artifact_sha256:input.base_artifact_sha256,base_source_ids:baseSources.map(s=>s.id).sort(),target_source_ids:target,affected_coverage_keys:affectedKeys,preservation_expected:preservation,raw_publication:raw.id,raw_artifact_sha256:input.raw_artifact_sha256,actor_id:input.actor_id,actor_type:'automated',method:'Pinned immutable base + exact scoped replacement; target relations recalculated by producer against exact base BR context; no correspondence/review flags coerced. Expected preservation is independently verified after import in the job receipt.'};
  const id='ca-update-'+digest(JSON.stringify({version:VERSION,base:base.id,base_sha256:base.sha256,raw_sha256:input.raw_artifact_sha256,target,actor_id:input.actor_id,...(provenance?{orchestration_sha256:provenance.orchestration_sha256,technical_events_sha256:provenance.technical_events_sha256}:{} )})).slice(0,32);
  const metadata={...base.metadata};for(const key of ['format','storage_format','content_identity','item_count','source_count','relation_count','update_scope','verification','export_manifest','orchestration_provenance','orchestration_sha256','technical_identity_payload','technical_events_sha256'])delete metadata[key];
  const header={...metadata,id,schema_version:raw.schema_version,schema_path:raw.schema_path??base.metadata.schema_path??null,schema_sha256:raw.schema_sha256??base.metadata.schema_sha256??null,created_at:raw.created_at,extraction_revision:raw.extraction_revision,mapping_revision:raw.mapping_revision,sources:sourceUnion,coverage,...(provenance?{orchestration_provenance:provenance.orchestration_provenance,orchestration_sha256:provenance.orchestration_sha256,technical_identity_payload:provenance.technical_identity_payload,technical_events_sha256:provenance.technical_events_sha256}:{}),changelog:[...(Array.isArray(base.metadata.changelog)?base.metadata.changelog:[]),...(provenance?.technical_events??[]),{type:'source_update',base_publication:base.id,target_source_ids:target,raw_publication:raw.id,raw_artifact_sha256:input.raw_artifact_sha256,description:'Substituição delimitada de fontes sobre base publicada imutável. Demais fontes, itens, relações e cobertura preservados; não representa mudança oficial dos currículos.'}],parent_publication:base.id,parent_content_identity:base.metadata.content_identity??null,publication_kind:'global_source_update_candidate',national_release_ready:false,coverage_statement:'Atualização global por fontes delimitadas; recortes afetados requerem reconciliação. Não constitui aprovação pedagógica humana nem lançamento nacional.',update_scope:updateScope,verification:{actor_type:'automated',actor_id:input.actor_id,method:VERSION,raw_verification:raw.verification??null,base_verification:base.metadata.verification??null,human_pedagogical_review:false}};
  global=await writeShardedArtifact(header,{items:queryRecords<Learning>(client,'ingestion_items',undefined,'',input.signal),relations:queryRecords<Relation>(client,'ingestion_relations',undefined,'',input.signal)},{directory:input.output_directory});
  input.signal?.throwIfAborted();if(provenance)await assertIngestionProvenanceUnchanged(provenance);input.signal?.throwIfAborted();
  await client.query('COMMIT');
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
 input.signal?.throwIfAborted();
 const receipt=await importShardedManifest(global.manifest,global.sha256,{root:global.root,makeDefault:false});
 input.signal?.throwIfAborted();
 const proof=await verifyGlobalIngestionPreservation(input.base_publication,receipt.id,target,input.actor_id);
 return{publication:receipt.id,artifact:relative(process.cwd(),global.filename),artifact_sha256:global.sha256,import_receipt:receipt,raw_receipt:{publication:raw.id,artifact:relative(process.cwd(),resolve(input.raw_artifact)),artifact_sha256:input.raw_artifact_sha256},update_scope:proof,...(provenance?{provenance_receipt:{orchestration_provenance:provenance.orchestration_provenance,orchestration_sha256:provenance.orchestration_sha256,technical_events_sha256:provenance.technical_events_sha256}}:{})};
}

/** Explicit candidate publication: CAS, visibility and the audit event share one locked transaction. */
export async function publishGlobalIngestionUpdate(publication:string,expectedBase:string,actor:PublicationActor){
 const pinned=(await pool.query("SELECT payload->'update_scope' AS scope FROM publications WHERE id=$1",[publication])).rows[0]?.scope;
 if(!pinned||pinned.mode!=='base-plus-source-update'||pinned.base_publication!==expectedBase)throw new DomainError(409,'UPDATE_LINEAGE_MISMATCH','Candidato global não deriva da base declarada.');
 await verifyGlobalIngestionPreservation(expectedBase,publication,pinned.target_source_ids,actor.id);
 const client=await pool.connect();try{
  await client.query('BEGIN');await client.query('SELECT pg_advisory_xact_lock(81726354)');
  const row=(await client.query("SELECT p.payload->'update_scope' AS scope,v.status FROM publications p JOIN publication_visibility v ON v.publication_id=p.id WHERE p.id=$1",[publication])).rows[0];
  if(!row||row.scope?.mode!=='base-plus-source-update'||row.scope.base_publication!==expectedBase)throw new DomainError(409,'UPDATE_LINEAGE_MISMATCH','Candidato global não deriva da base declarada.');
  const current=(await client.query('SELECT publication_id FROM current_publication WHERE singleton=true FOR UPDATE')).rows[0]?.publication_id;
  if(current!==expectedBase)throw new DomainError(409,'STALE_INGESTION_BASE','A publicação padrão mudou após o início do job. Reprocesse sobre a nova base; nenhum dado foi publicado.');
  await publishVisibility(client,publication,actor);await client.query('UPDATE current_publication SET publication_id=$1 WHERE singleton=true',[publication]);
  const event=(await client.query('INSERT INTO publication_events(publication_id,previous_id,actor_id,actor_type,reason) VALUES($1,$2,$3,$4,$5) RETURNING id,publication_id,previous_id,actor_id,actor_type,created_at',[publication,expectedBase,actor.id,actor.actor_type,actor.reason])).rows[0];
  await client.query('COMMIT');return{id:publication,previous_id:expectedBase,publication_event:{...event,id:String(event.id)}};
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
}

/** Verify a persisted private candidate against current pinned inputs without recomposing the global graph. */
export async function revalidatePreparedIngestionProvenance(input:GlobalIngestionInput,candidatePublication:string){
 if(!input.provenance)throw new DomainError(422,'INGESTION_PROVENANCE_REQUIRED','Retomada orquestrada exige os recibos originais do job.');
 const loaded=await loadBundleFile(input.raw_artifact,{expected:{sha256:input.raw_artifact_sha256}}),raw=loaded.bundle as unknown as ShardedManifest;await verifyShardedManifest(raw);
 const client=await pool.connect();try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');const base=await baseRecord(client,input.base_publication),target=targets(input.target_source_ids);
  const stored=(await client.query("SELECT payload->'orchestration_provenance' AS orchestration,payload->>'orchestration_sha256' AS digest,payload->>'technical_events_sha256' AS technical,payload->'update_scope' AS scope FROM publications WHERE id=$1",[candidatePublication])).rows[0];
  if(!stored||stored.scope?.base_publication!==base.id||stored.scope?.actor_id!==input.actor_id||JSON.stringify(stored.scope?.target_source_ids)!==JSON.stringify(target)||stored.scope?.raw_publication!==raw.id||stored.scope?.raw_artifact_sha256!==input.raw_artifact_sha256)throw new DomainError(409,'INGESTION_PROVENANCE_MISMATCH','Candidato salvo não pertence à mesma atualização fixada.');
  const proof=await prepareIngestionProvenance(client,{base:{id:base.id,sha256:base.sha256},target_source_ids:target,raw,effective_raw_receipt:{publication:raw.id,artifact:relative(process.cwd(),resolve(input.raw_artifact)),artifact_sha256:input.raw_artifact_sha256},provenance:input.provenance,signal:input.signal});
  if(stored.digest!==proof.orchestration_sha256||stored.technical!==proof.technical_events_sha256||provenanceDigest(stored.orchestration)!==proof.orchestration_sha256)throw new DomainError(409,'INGESTION_PROVENANCE_MISMATCH','Provas/código/recibos da retomada diferem da composição original.');
  await assertIngestionProvenanceUnchanged(proof);await client.query('COMMIT');return{orchestration_provenance:proof.orchestration_provenance,orchestration_sha256:proof.orchestration_sha256,technical_events_sha256:proof.technical_events_sha256};
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
}
