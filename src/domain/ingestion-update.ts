import {createHash} from 'node:crypto';
import {relative,resolve} from 'node:path';
import {existsSync} from 'node:fs';
import {mkdir,readFile,stat} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import type pg from 'pg';
import {pool} from '../db/client';
import type {Learning,Relation,Source} from '../shared/contracts';
import {DomainError} from './errors';
import {loadBundleFile} from './bundle-file';
import {importShardedManifest,shardRecords,verifyShardedManifest,type ShardedManifest} from './shards';
import {hashShardedRecords,rewritePrivateShardedManifest,writeShardedArtifact} from './shard-writer';
import {publishVisibility,type PublicationActor} from './visibility';
import {mergeIngestionCoverage} from './ingestion-coverage';
import {prepareIngestionProvenance,assertIngestionProvenanceUnchanged,provenanceDigest,type IngestionProvenanceInput,type PreparedIngestionProvenance} from './ingestion-provenance';

const VERSION='base-plus-source-update-v4';
const RELEASE_CHECK='pipeline/release_check.py';
const RECONCILIATION_PENDING='Atualização de fonte exige nova reconciliação documental deste recorte.';
const digest=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
// JSON numeric spelling (1.0/1) is not a changed value; exact JSONB equality is checked separately below.
const semanticJson=(text:string)=>JSON.stringify(JSON.parse(text));
async function diagnosticStep<T>(label:string,action:()=>Promise<T>):Promise<T>{try{return await action();}catch(error){if(error instanceof Error)error.message=label+': '+error.message;throw error;}}
const hashValid=(value:string)=>/^[a-f0-9]{64}$/.test(value);
const stableJson=(value:unknown):string=>Array.isArray(value)?'['+value.map(stableJson).join(',')+']':value&&typeof value==='object'?'{'+Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([key,item])=>JSON.stringify(key)+':'+stableJson(item)).join(',')+'}':JSON.stringify(value)??'null';
function comparableCandidateHeader(value:Record<string,unknown>){
 const output={...value};for(const key of ['format','storage_format','content_identity','source_content_identity','export_source_content_identity','transcode_provenance','item_count','source_count','relation_count','parts'])delete output[key];
 if(Array.isArray(output.coverage))output.coverage=output.coverage.map(value=>{if(!value||typeof value!=='object'||Array.isArray(value))return value;const row={...(value as Record<string,unknown>)};for(const key of ['ready','reconciled','national_release_ready','editorial_completeness','mapping_coverage','pending','coverage_revalidation'])delete row[key];return row;});
 return stableJson(output);
}
async function revalidateCoverage(result:Awaited<ReturnType<typeof writeShardedArtifact>>,affectedKeys:string[],signal?:AbortSignal,mode:'prepare'|'replay'='prepare'){
 signal?.throwIfAborted();const reportRoot=resolve('var/ingestion-revalidation'),reportPath=resolve(reportRoot,mode==='prepare'?`${result.manifest.id}.json`:`${result.manifest.id}-current-${result.sha256}.json`);await mkdir(reportRoot,{recursive:true});
 const python=process.env.PIPELINE_PYTHON||process.env.PYTHON_BIN||(existsSync('var/venv-pipeline/bin/python')?resolve('var/venv-pipeline/bin/python'):'python3');let stderr='';
 const exitCode=await new Promise<number>((accept,reject)=>{const child=spawn(python,[RELEASE_CHECK,'--bundle',result.filename,'--output',relative(process.cwd(),reportPath),'--json'],{stdio:['ignore','ignore','pipe']});let aborted=false,timedOut=false,killer:NodeJS.Timeout|undefined;const terminate=()=>{if(child.exitCode!==null)return;child.kill('SIGTERM');if(!killer){killer=setTimeout(()=>child.kill('SIGKILL'),5000);killer.unref();}};const onAbort=()=>{aborted=true;terminate();};signal?.addEventListener('abort',onAbort,{once:true});if(signal?.aborted)onAbort();const timeout=setTimeout(()=>{timedOut=true;terminate();},Math.max(1000,Number(process.env.JOB_TIMEOUT_SECONDS||7200)*1000));timeout.unref();const cleanup=()=>{clearTimeout(timeout);if(killer)clearTimeout(killer);signal?.removeEventListener('abort',onAbort);};child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-16000);});child.once('error',error=>{cleanup();reject(error);});child.once('close',code=>{cleanup();if(aborted)reject(signal?.reason??new Error('Ingestion aborted'));else if(timedOut)reject(new DomainError(409,'COVERAGE_REVALIDATION_TIMEOUT','Revalidação da cobertura excedeu o prazo do job.'));else if(code===0||code===1)accept(code??1);else reject(new DomainError(409,'COVERAGE_REVALIDATION_FAILED','Checker documental recusou candidato: '+stderr.slice(-1200)));});});
 signal?.throwIfAborted();const reportBytes=await readFile(reportPath);const report=JSON.parse(reportBytes.toString('utf8')) as Record<string,unknown>;
 if(report.publication!==result.manifest.id||report.bundle_sha256!==result.sha256||!Array.isArray(report.scope_readiness))throw new DomainError(409,'COVERAGE_REVALIDATION_BINDING_FAILED','Relatório do checker não se vincula ao manifesto candidato atual.');
 const evaluated=new Map<string,Record<string,unknown>>();for(const value of report.scope_readiness){if(!value||typeof value!=='object'||Array.isArray(value))continue;const row=value as Record<string,unknown>;if(typeof row.uf==='string'&&typeof row.stage==='string'&&(typeof row.component==='string'||row.component===null))evaluated.set(coverageKey(row),row);}
 const reportSha256=digest(reportBytes);const scopes=result.manifest.coverage.map(value=>value as unknown as Record<string,unknown>);let checked=0;let persistedReportPath:string|undefined,persistedReportSha:string|undefined,persistedCandidateSha:string|undefined;
 for(const row of scopes){const key=coverageKey(row);if(!affectedKeys.includes(key))continue;const proof=evaluated.get(key);if(!proof||!Array.isArray(proof.issues)||typeof proof.ready!=='boolean')throw new DomainError(409,'COVERAGE_REVALIDATION_SCOPE_MISSING','Checker não produziu veredito para um recorte afetado.');const ready=proof.ready===true;
  if(mode==='prepare'){row.ready=ready;row.reconciled=ready;row.national_release_ready=false;row.editorial_completeness=ready?'reconciled':'pending_revalidation';row.mapping_coverage=ready?'verified_against_current_bundle':'pending_revalidation_after_source_update';const previous=Array.isArray(row.pending)?row.pending.filter(item=>item!==RECONCILIATION_PENDING):[];row.pending=ready?previous:[...new Set([...previous,RECONCILIATION_PENDING])];row.coverage_revalidation={version:'scope-readiness/1',method:'pipeline/release_check.py',candidate_manifest_sha256:result.sha256,candidate_content_identity:result.manifest.content_identity,report_path:relative(process.cwd(),reportPath),report_sha256:reportSha256,ready,issues:proof.issues,source_ids:proof.source_ids,checker_exit_code:exitCode};}
  else{
   const saved=row.coverage_revalidation as Record<string,unknown>|undefined;
   if(!saved||saved.version!=='scope-readiness/1'||saved.candidate_content_identity===undefined||JSON.stringify(saved.candidate_content_identity)!==JSON.stringify(result.manifest.content_identity)||saved.ready!==ready||row.ready!==ready||row.reconciled!==ready||JSON.stringify(saved.issues)!==JSON.stringify(proof.issues)||JSON.stringify(saved.source_ids)!==JSON.stringify(proof.source_ids))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_MISMATCH','Prontidão ou os motivos persistidos divergem das evidências atuais.');
   if(typeof saved.report_path!=='string'||typeof saved.report_sha256!=='string'||typeof saved.candidate_manifest_sha256!=='string'||!saved.report_path.startsWith('var/ingestion-revalidation/'))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISSING','Prova original da revalidação não está no armazenamento permitido.');
   if(persistedReportPath&&persistedReportPath!==saved.report_path||persistedReportSha&&persistedReportSha!==saved.report_sha256||persistedCandidateSha&&persistedCandidateSha!==saved.candidate_manifest_sha256)throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISMATCH','Recortes afetados apontam para relatórios de revalidação diferentes.');persistedReportPath=saved.report_path;persistedReportSha=saved.report_sha256;persistedCandidateSha=saved.candidate_manifest_sha256;
  }
  checked++;
 }
 if(mode==='replay'){
  if(!persistedReportPath||!persistedReportSha)throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISSING','Manifesto não contém a prova original da revalidação.');
  if(!persistedCandidateSha)throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISSING','Hash do manifesto preliminar está ausente.');
  const originalPath=resolve(persistedReportPath),originalRelative=relative(reportRoot,originalPath);if(originalRelative.startsWith('..'))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISSING','Relatório original escapou do diretório de provas permitido.');
  const originalBytes=await readFile(originalPath);if(digest(originalBytes)!==persistedReportSha)throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISMATCH','Checksum do relatório original de revalidação diverge.');
  const original=JSON.parse(originalBytes.toString('utf8')) as Record<string,unknown>;if(original.publication!==result.manifest.id||original.bundle_sha256!==persistedCandidateSha||!Array.isArray(original.scope_readiness))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISMATCH','Relatório original não pertence à publicação ou ao manifesto candidato declarado.');
  const originalScopes=new Map<string,Record<string,unknown>>();for(const value of original.scope_readiness){if(value&&typeof value==='object'&&!Array.isArray(value)){const row=value as Record<string,unknown>;originalScopes.set(coverageKey(row),row);}}
  for(const row of scopes){if(!affectedKeys.includes(coverageKey(row)))continue;const saved=row.coverage_revalidation as Record<string,unknown>;const proof=originalScopes.get(coverageKey(row));if(!proof||proof.ready!==saved.ready||JSON.stringify(proof.issues)!==JSON.stringify(saved.issues))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_PROOF_MISMATCH','Escopo persistido diverge do relatório original.');}
  return{result,report_path:relative(process.cwd(),reportPath),report_sha256:reportSha256,scopes_checked:checked,scopes_ready:scopes.filter(row=>affectedKeys.includes(coverageKey(row))&&row.ready===true).length};
 }
 if(checked!==affectedKeys.length)throw new DomainError(409,'COVERAGE_REVALIDATION_SCOPE_COUNT_MISMATCH','Quantidade de recortes afetados diverge do relatório do checker.');
 const updated=await rewritePrivateShardedManifest(result,{...result.manifest,coverage:scopes as unknown as typeof result.manifest.coverage});return{result:updated,report_path:relative(process.cwd(),reportPath),report_sha256:reportSha256,scopes_checked:checked,scopes_ready:scopes.filter(row=>affectedKeys.includes(coverageKey(row))&&row.ready===true).length};
}
export async function revalidatePersistedGlobalIngestionCoverage(input:{manifest:ShardedManifest;filename:string;sha256:string;signal?:AbortSignal}){
 const scope=input.manifest.update_scope as Record<string,unknown>|undefined,keys=scope?.affected_coverage_keys;
 if(scope?.mode!=='base-plus-source-update'||!Array.isArray(keys)||keys.some(key=>typeof key!=='string'))throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_SCOPE_INVALID','Manifesto salvo não contém o escopo original da revalidação.');
 const filename=resolve(input.filename),info=await stat(filename);if(!info.isFile())throw new DomainError(409,'COVERAGE_REVALIDATION_REPLAY_ARTIFACT_INVALID','Manifesto salvo não é um arquivo regular.');
 const result=await revalidateCoverage({manifest:input.manifest,filename,sha256:input.sha256,bytes:info.size,root:resolve('data/bundles')},keys as string[],input.signal,'replay');
 return{report_path:result.report_path,report_sha256:result.report_sha256,scopes_checked:result.scopes_checked,scopes_ready:result.scopes_ready};
}
function targets(input:string[]){if(!Array.isArray(input)||!input.length||input.length>500||input.some(x=>typeof x!=='string'||!x||x.length>500)||new Set(input).size!==input.length)throw new DomainError(422,'INVALID_UPDATE_TARGETS','Declare fontes alvo únicas e explícitas.');return[...input].sort();}
function scopedVerificationSamples(verification:unknown,inventorySourceIds:Set<string>,targetSourceIds:Set<string>,scope:'base'|'raw'){
 if(verification===undefined||verification===null)return[] as Record<string,unknown>[];
 if(typeof verification!=='object'||Array.isArray(verification))throw new DomainError(409,'UPDATE_SAMPLE_INVALID','Verificação de amostras da publicação é inválida.');
 const samples=(verification as Record<string,unknown>).samples;if(samples===undefined)return[] as Record<string,unknown>[];
 if(!Array.isArray(samples))throw new DomainError(409,'UPDATE_SAMPLE_INVALID','Lista de amostras da publicação é inválida.');
 const seen=new Set<string>();
 return samples.flatMap(sample=>{
  if(!sample||typeof sample!=='object'||Array.isArray(sample))throw new DomainError(409,'UPDATE_SAMPLE_INVALID','Amostra não é um objeto válido.');
  const row=sample as Record<string,unknown>;
  if(typeof row.source_id!=='string'||typeof row.item_id!=='string'||typeof row.uf!=='string'||typeof row.stage!=='string'||!(typeof row.component==='string'||row.component===null)||!Number.isInteger(row.page)||Number(row.page)<1||typeof row.artifact_sha256!=='string'||!hashValid(row.artifact_sha256)||typeof row.literal_text_in_page!=='boolean')throw new DomainError(409,'UPDATE_SAMPLE_INVALID','Amostra não tem âncora, escopo, página ou hash válidos.');
  if(!inventorySourceIds.has(row.source_id))throw new DomainError(409,'UPDATE_SAMPLE_OUTSIDE_SCOPE','Amostra não pertence ao inventário pinado da atualização.');
  const isTarget=targetSourceIds.has(row.source_id);
  if(scope==='raw'&&!isTarget)throw new DomainError(409,'UPDATE_SAMPLE_OUTSIDE_SCOPE','Amostra RAW fora do escopo de fontes alvo.');
  const key=JSON.stringify([row.uf,row.stage,row.component,row.item_id]);
  if(seen.has(key))throw new DomainError(409,'UPDATE_SAMPLE_DUPLICATE','Amostras duplicadas para o mesmo item e estrato.');
  seen.add(key);
  return scope==='base'&&!isTarget? [row] : scope==='raw'? [row] : [];
 });
}
function mergeSourceReconciliationReports(baseValue:unknown,rawValue:unknown,targetSourceIds:string[],baseSourceIds:string[],rawSourceIds:string[]){
 if(!Array.isArray(baseValue)||!Array.isArray(rawValue))throw new DomainError(409,'UPDATE_RECONCILIATION_REPORT_INVALID','Relatórios de reconciliação da base ou do recibo RAW estão ausentes.');
 const target=new Set(targetSourceIds);
 const validate=(rows:unknown[],name:string)=>{
  const seen=new Set<string>();
  for(const row of rows){
   if(!row||typeof row!=='object'||Array.isArray(row)||typeof (row as Record<string,unknown>).source_id!=='string')throw new DomainError(409,'UPDATE_RECONCILIATION_REPORT_INVALID',`Relatório de reconciliação inválido em ${name}.`);
   const sourceId=(row as Record<string,unknown>).source_id as string;
   if(seen.has(sourceId))throw new DomainError(409,'UPDATE_RECONCILIATION_REPORT_DUPLICATE',`Relatório de reconciliação duplicado para ${sourceId} em ${name}.`);
   seen.add(sourceId);
  }
  return seen;
 };
 const baseIds=validate(baseValue,'base');
 const rawIds=validate(rawValue,'RAW');
 const exactInventory=(actual:Set<string>,expected:string[],name:string)=>{
  const expectedIds=new Set(expected);
  if(actual.size!==expectedIds.size||expectedIds.size!==expected.length||[...expectedIds].some(sourceId=>!actual.has(sourceId)))throw new DomainError(409,'UPDATE_RECONCILIATION_INVENTORY_MISMATCH',`Relatórios de reconciliação não correspondem ao inventário de fontes ${name}.`);
 };
 exactInventory(baseIds,baseSourceIds,'da base');
 exactInventory(rawIds,rawSourceIds,'do RAW');
 if(targetSourceIds.some(sourceId=>!baseIds.has(sourceId)||!rawIds.has(sourceId)))throw new DomainError(409,'UPDATE_RECONCILIATION_REPORT_MISSING_TARGET','Fonte alvo sem relatório na base e no RAW.');
 const replacements=rawValue.filter(row=>target.has((row as Record<string,unknown>).source_id as string));
 if(replacements.length!==target.size)throw new DomainError(409,'UPDATE_RECONCILIATION_REPORT_MISSING_TARGET','O recibo RAW não tem um relatório único para cada fonte alvo.');
 return [...baseValue.filter(row=>!target.has((row as Record<string,unknown>).source_id as string)),...replacements]
  .sort((left,right)=>((left as Record<string,unknown>).source_id as string).localeCompare((right as Record<string,unknown>).source_id as string));
}
async function baseRecord(client:pg.PoolClient,id:string){
 const row=(await client.query(`SELECT p.id,p.sha256,p.schema_version,p.created_at,p.extraction_revision,p.mapping_revision,(p.payload-'items'-'relations'-'sources'-'coverage'-'parts') AS metadata FROM publications p JOIN publication_visibility v ON v.publication_id=p.id AND v.status='published' WHERE p.id=$1`,[id])).rows[0];
 if(!row)throw new DomainError(404,'PUBLICATION_NOT_FOUND','Base publicada inexistente.');return row;
}
async function* queryRecords<T>(client:pg.PoolClient,table:'items'|'relations'|'ingestion_items'|'ingestion_relations',publication?:string,where='',signal?:AbortSignal):AsyncGenerator<T>{
 let last='';for(;;){signal?.throwIfAborted();const values=publication?[publication,last]:[last];const rows=await client.query(`SELECT id,payload FROM ${table} WHERE ${publication?'publication_id=$1 AND id>$2':'id>$1'} ${where} ORDER BY id LIMIT 1000`,values);if(!rows.rowCount)break;for(const row of rows.rows){signal?.throwIfAborted();last=row.id;yield row.payload as T;}}
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
 let last='';for(;;){const rows=await client.query('SELECT id,source_id,payload::text AS content FROM items WHERE publication_id=$1 AND NOT(source_id=ANY($2::text[])) AND id>$3 ORDER BY id LIMIT 1000',[publication,excluded,last]);if(!rows.rowCount)break;for(const row of rows.rows){const source=summaries.get(row.source_id);if(!source)throw new DomainError(409,'UPDATE_DANGLING_SOURCE','Item sem fonte no inventário da publicação verificada.');source.hash.update(row.id).update('\0').update(semanticJson(row.content)).update('\n');source.items++;last=row.id;}}
 return[...summaries.values()].map(source=>({source_id:source.source_id,items:source.items,source_sha256:source.source_sha256,items_sha256:source.hash.digest('hex')}));
}
async function relationProof(client:pg.PoolClient,publication:string,excluded:string[],comparePublication?:string){
 const hash=createHash('sha256');let count=0,last='';
 for(;;){
  // Apply LIMIT before inspecting membership. A correlated anti-join rebuilt the entire source/member join for every page.
  const rows=(await client.query('SELECT id,payload::text AS content FROM relations WHERE publication_id=$1 AND id>$2 ORDER BY id LIMIT 1000',[publication,last])).rows;
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
  await client.query("SET LOCAL statement_timeout='0'");
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
  // A new candidate publication has no useful MCV statistics yet. With nested loops enabled PostgreSQL can estimate
  // its side as one row and compare every base row against the entire candidate. Force a merge/hash-capable plan for
  // this full-payload equality check; the composite publication/id index supplies the merge order when chosen.
  const nestedLoopSetting=(await client.query('SHOW enable_nestloop')).rows[0].enable_nestloop==='on'?'on':'off';
  await client.query('SET LOCAL enable_nestloop=off');
  try{for(const table of ['sources','items'] as const){const filter=table==='sources'?'b.id':'b.source_id';const changed=(await diagnosticStep('canonical equality '+table,()=>client.query(`SELECT b.id FROM ${table} b LEFT JOIN ${table} a ON a.publication_id=$3 AND a.id=b.id WHERE b.publication_id=$1 AND NOT(${filter}=ANY($2::text[])) AND b.payload IS DISTINCT FROM a.payload LIMIT 1`,[basePublication,target,candidatePublication]))).rows[0];if(changed)throw new DomainError(409,'OUTSIDE_CANONICAL_VALUE_CHANGED','Valor canônico fora do alvo mudou; a atualização foi recusada, inclusive para números que perderiam precisão.');}}finally{await client.query(`SET LOCAL enable_nestloop=${nestedLoopSetting}`);}
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
 const client=await pool.connect();let global:Awaited<ReturnType<typeof writeShardedArtifact>>,provenance:PreparedIngestionProvenance|undefined,affectedKeys:string[]=[],revalidationMode:'prepare'|'replay'='prepare';
 try{
  await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ');await client.query("SET LOCAL statement_timeout='0'");const base=await baseRecord(client,input.base_publication);
  if(raw.base_publication_sha256!==base.sha256)throw new DomainError(409,'RAW_BASE_CHECKSUM_MISMATCH','Checksum da base no recibo não corresponde à publicação fixada.');
  const baseSources=(await client.query('SELECT payload FROM sources WHERE publication_id=$1 ORDER BY id',[base.id])).rows.map(x=>x.payload as Source);
  const nationalSources=baseSources.filter(s=>s.uf==='BR'),contextIds=nationalSources.map(s=>s.id).sort();
  if(target.some(id=>nationalSources.some(s=>s.id===id))||raw.sources.some(s=>target.includes(s.id)&&s.uf==='BR'))throw new DomainError(422,'NATIONAL_UPDATE_REQUIRES_GLOBAL_REBUILD','Atualização do referencial nacional exige reconstrução explícita de todos os vínculos dependentes.');
  if(JSON.stringify([...(raw.context_source_ids as string[]??[])].sort())!==JSON.stringify(contextIds))throw new DomainError(409,'NATIONAL_CONTEXT_MISMATCH','O contexto BR não corresponde ao inventário da base fixada.');
  if(raw.sources.some(s=>!target.includes(s.id)&&!contextIds.includes(s.id))||target.some(id=>!raw.sources.some(s=>s.id===id)))throw new DomainError(409,'RAW_SOURCE_SCOPE_MISMATCH','O recibo deve conter exatamente fontes alvo e o contexto BR fixado.');
  for(const source of nationalSources){const supplied=raw.sources.find(s=>s.id===source.id);if(!supplied||(await client.query('SELECT $1::jsonb=$2::jsonb AS equal',[JSON.stringify(source),JSON.stringify(supplied)])).rows[0].equal!==true)throw new DomainError(409,'NATIONAL_CONTEXT_CHANGED','Metadados BR diferem da base imutável.');}
  for(const source of baseSources.filter(s=>target.includes(s.id))){const replacement=raw.sources.find(s=>s.id===source.id)!;const unchanged=(await client.query('SELECT $1::jsonb=$2::jsonb AS equal',[JSON.stringify(source),JSON.stringify(replacement)])).rows[0].equal;if(!unchanged){const dependency=(await client.query("SELECT i.id FROM items i CROSS JOIN LATERAL jsonb_array_elements(i.evidence)e WHERE i.publication_id=$1 AND NOT(i.source_id=ANY($2::text[])) AND e->>'source_id'=$3 LIMIT 1",[base.id,target,source.id])).rows[0];if(dependency)throw new DomainError(409,'CROSS_SOURCE_EVIDENCE_DEPENDENCY','Itens fora do alvo citam a edição desta fonte. A alteração exige escopo editorial explícito dessas dependências.');}}
  const sourceUnion=[...baseSources.filter(s=>!target.includes(s.id)),...raw.sources.filter(s=>target.includes(s.id))].sort((a,b)=>a.id.localeCompare(b.id));
  const targetSet=new Set(target),baseSampleSources=new Set(baseSources.map(source=>source.id)),rawSampleSources=new Set(raw.sources.map(source=>source.id));
  const verificationSamples=[...scopedVerificationSamples(base.metadata.verification,baseSampleSources,targetSet,'base'),...scopedVerificationSamples(raw.verification,rawSampleSources,targetSet,'raw')];
  const sampleKeys=new Set<string>();for(const sample of verificationSamples){const key=JSON.stringify([sample.uf,sample.stage,sample.component,sample.item_id]);if(sampleKeys.has(key))throw new DomainError(409,'UPDATE_SAMPLE_CONFLICT','Amostras da base e do recibo conflitam no mesmo item e estrato.');sampleKeys.add(key);}
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
  affectedKeys=[...new Set([...baseCoverage,...raw.coverage as Record<string,unknown>[]].filter(row=>rowTargets(row,target)).map(coverageKey))].sort();
  const preservation={unaffected_sources:await sourceProofs(client,base.id,target),relations_excluding_target:await relationProof(client,base.id,target),coverage_excluding_target:await coverageProof(client,base.id,target,affectedKeys)};
  const updateScope={mode:'base-plus-source-update',version:VERSION,base_publication:base.id,base_publication_sha256:base.sha256,base_artifact_sha256:input.base_artifact_sha256,base_source_ids:baseSources.map(s=>s.id).sort(),target_source_ids:target,affected_coverage_keys:affectedKeys,preservation_expected:preservation,raw_publication:raw.id,raw_artifact_sha256:input.raw_artifact_sha256,actor_id:input.actor_id,actor_type:'automated',method:'Pinned immutable base + exact scoped replacement; target relations recalculated by producer against exact base BR context; no correspondence/review flags coerced. Expected preservation is independently verified after import in the job receipt.'};
  const id='ca-update-'+digest(JSON.stringify({version:VERSION,base:base.id,base_sha256:base.sha256,raw_sha256:input.raw_artifact_sha256,target,actor_id:input.actor_id,...(provenance?{orchestration_sha256:provenance.orchestration_sha256,technical_events_sha256:provenance.technical_events_sha256}:{} )})).slice(0,32);
  const sourceReconciliation=mergeSourceReconciliationReports(base.metadata.source_reconciliation,raw.source_reconciliation,target,baseSources.map(source=>source.id),raw.sources.map(source=>source.id));
  const metadata={...base.metadata};for(const key of ['format','storage_format','content_identity','item_count','source_count','relation_count','update_scope','verification','export_manifest','orchestration_provenance','orchestration_sha256','technical_identity_payload','technical_events_sha256'])delete metadata[key];
  const header={...metadata,id,schema_version:raw.schema_version,schema_path:raw.schema_path??base.metadata.schema_path??null,schema_sha256:raw.schema_sha256??base.metadata.schema_sha256??null,created_at:raw.created_at,extraction_revision:raw.extraction_revision,mapping_revision:raw.mapping_revision,sources:sourceUnion,coverage,source_reconciliation:sourceReconciliation,...(provenance?{orchestration_provenance:provenance.orchestration_provenance,orchestration_sha256:provenance.orchestration_sha256,technical_identity_payload:provenance.technical_identity_payload,technical_events_sha256:provenance.technical_events_sha256}:{}),changelog:[...(Array.isArray(base.metadata.changelog)?base.metadata.changelog:[]),...(provenance?.technical_events??[]),{type:'source_update',base_publication:base.id,target_source_ids:target,raw_publication:raw.id,raw_artifact_sha256:input.raw_artifact_sha256,description:'Substituição delimitada de fontes sobre base publicada imutável. Demais fontes, itens, relações e cobertura preservados; não representa mudança oficial dos currículos.'}],parent_publication:base.id,parent_content_identity:base.metadata.content_identity??null,publication_kind:'global_source_update_candidate',national_release_ready:false,coverage_statement:'Atualização global por fontes delimitadas; recortes afetados requerem reconciliação. Não constitui aprovação pedagógica humana nem lançamento nacional.',update_scope:updateScope,verification:{actor_type:'automated',actor_id:input.actor_id,method:VERSION,samples:verificationSamples,raw_verification:raw.verification??null,base_verification:base.metadata.verification??null,human_pedagogical_review:false}};
  const outputRecords={items:queryRecords<Learning>(client,'ingestion_items',undefined,'',input.signal),relations:queryRecords<Relation>(client,'ingestion_relations',undefined,'',input.signal)};
  const existingFilename=resolve(input.output_directory,'snapshot.manifest.json');
  if(existsSync(existingFilename)){
   const loaded=await loadBundleFile(existingFilename);const existing=loaded.bundle as unknown as ShardedManifest;
   if(existing.format!=='curriculos-abertos/sharded-v1'||existing.id!==id||comparableCandidateHeader(existing as unknown as Record<string,unknown>)!==comparableCandidateHeader(header))throw new DomainError(409,'UPDATE_CANDIDATE_COLLISION','Artefato existente não corresponde à atualização global fixada.');
   const actualIdentity=await hashShardedRecords(outputRecords),savedIdentity=existing.content_identity as {items_jsonl_sha256?:string;relations_jsonl_sha256?:string};
   if(stableJson(actualIdentity)!==stableJson({items_jsonl_sha256:savedIdentity?.items_jsonl_sha256,relations_jsonl_sha256:savedIdentity?.relations_jsonl_sha256}))throw new DomainError(409,'UPDATE_CANDIDATE_CONTENT_MISMATCH','Conteúdo persistido do candidato diverge da composição atual.');
   await verifyShardedManifest(existing,resolve('data/bundles'));
   const proofs=existing.coverage.filter(value=>affectedKeys.includes(coverageKey(value as unknown as Record<string,unknown>))).map(value=>(value as unknown as Record<string,unknown>).coverage_revalidation);
   if(proofs.some(Boolean)&&proofs.some(value=>!value))throw new DomainError(409,'UPDATE_CANDIDATE_REVALIDATION_PARTIAL','Manifesto existente contém provas de revalidação incompletas.');
   if(proofs.length!==affectedKeys.length)throw new DomainError(409,'UPDATE_CANDIDATE_SCOPE_MISMATCH','Recortes afetados do artefato existente divergem da atualização.');
   revalidationMode=proofs.length&&proofs.every(Boolean)?'replay':'prepare';
   global={manifest:existing,filename:loaded.path,sha256:loaded.file_sha256,bytes:loaded.bytes,root:resolve('data/bundles')};
  }else global=await writeShardedArtifact(header,outputRecords,{directory:input.output_directory});
  input.signal?.throwIfAborted();if(provenance)await assertIngestionProvenanceUnchanged(provenance);input.signal?.throwIfAborted();
  await client.query('COMMIT');
 }catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();}
 input.signal?.throwIfAborted();
 const coverageRevalidation=await revalidateCoverage(global,affectedKeys,input.signal,revalidationMode);global=coverageRevalidation.result;
 const coverageRevalidationReceipt={report_path:coverageRevalidation.report_path,report_sha256:coverageRevalidation.report_sha256,scopes_checked:coverageRevalidation.scopes_checked,scopes_ready:coverageRevalidation.scopes_ready};
 input.signal?.throwIfAborted();
 const receipt=await importShardedManifest(global.manifest,global.sha256,{root:global.root,makeDefault:false});
 input.signal?.throwIfAborted();
 const proof=await verifyGlobalIngestionPreservation(input.base_publication,receipt.id,target,input.actor_id);
 return{publication:receipt.id,artifact:relative(process.cwd(),global.filename),artifact_sha256:global.sha256,import_receipt:receipt,raw_receipt:{publication:raw.id,artifact:relative(process.cwd(),resolve(input.raw_artifact)),artifact_sha256:input.raw_artifact_sha256},update_scope:proof,coverage_revalidation:coverageRevalidationReceipt,...(provenance?{provenance_receipt:{orchestration_provenance:provenance.orchestration_provenance,orchestration_sha256:provenance.orchestration_sha256,technical_events_sha256:provenance.technical_events_sha256}}:{})};
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
