import {mkdir,readFile,writeFile,rename,realpath,stat,link,unlink,open} from 'node:fs/promises';
import {createReadStream,readFileSync,existsSync} from 'node:fs';
import {spawn} from 'node:child_process';
import {createHash,randomUUID} from 'node:crypto';
import {resolve,sep,basename,relative,isAbsolute,dirname} from 'node:path';
import {z} from 'zod';
import {pool} from '../db/client';
import {exportIngestionBase,prepareGlobalIngestionUpdate,verifyGlobalIngestionPreservation,revalidatePreparedIngestionProvenance,type GlobalIngestionInput} from '../domain/ingestion-update';
import {evaluateIngestionProvenance,canonicalProvenance,type IngestionArtifactReceipt,type IngestionProvenanceInput} from '../domain/ingestion-provenance';
import {loadBundleFile} from '../domain/bundle-file';
import {importShardedManifest,verifyShardedManifest,type ShardedManifest} from '../domain/shards';
import {audit} from '../admin/auth';
import type {Job} from './jobs';
const identifier=z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$/),hash=z.string().regex(/^[a-f0-9]{64}$/);
const sourceIds=z.array(z.string().min(1).max(500)).min(1).max(500);
const pinSchema=z.object({base_publication:identifier,base_publication_sha256:hash,target_sources:sourceIds});
const baseSchema=z.object({job_id:z.uuid(),artifact:z.string().min(1).max(1000),artifact_sha256:hash,base_publication:identifier,base_publication_sha256:hash,context_publication:identifier});
const completed=z.object({id:z.string(),state:z.literal('completed'),publication:identifier,artifact:z.string().min(1).max(1000),artifact_sha256:hash,base_publication:identifier,base_publication_sha256:hash,base_artifact_sha256:hash,target_source_ids:sourceIds});
const artifactReceipt=z.object({publication:identifier,artifact:z.string().min(1).max(1500),artifact_sha256:hash}).strict();
const filePin=z.object({path:z.string().min(1).max(1500),sha256:hash}).strict();
const provenanceSchema=z.object({original_raw_receipt:artifactReceipt,raster_stage_receipt:filePin.nullable(),technical_evaluation_receipt:filePin,receipt_directory:z.string()}).strict();
const replaySchema=z.object({checkpoint:z.string(),publication:identifier,artifact:z.string().min(1).max(1000),artifact_sha256:hash,actor_id:z.string(),base_publication:identifier,base_receipt:baseSchema,raw_receipt:artifactReceipt,original_raw_receipt:artifactReceipt,effective_raw_receipt:artifactReceipt,provenance:provenanceSchema,provenance_receipt:z.object({orchestration_sha256:hash,technical_events_sha256:hash}).passthrough(),import_receipt:z.object({id:identifier,sha256:hash}),update_scope:z.object({mode:z.literal('base-plus-source-update'),base_publication:identifier,candidate_publication:identifier,target_source_ids:sourceIds})});
const RASTER_CLI='scripts/augment-ingestion-raw.py';
const STAGE_RUNTIME=[RASTER_CLI,'pipeline/raster_augmentation.py','pipeline/raster_review_scoped.py','pipeline/raster_review.py','pipeline/distribution.py','pipeline/validate_artifact.py'];
const LOADED_STAGE_PINS=Object.fromEntries(STAGE_RUNTIME.map(path=>[path,createHash('sha256').update(readFileSync(path)).digest('hex')]));
const AM_SOURCES=new Set(['am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em']);
type JobScope={base_publication:string;base_publication_sha256:string;base_artifact_sha256:string;target_source_ids:string[];context_source_ids:string[]};
function same(a:unknown,b:unknown,label:string){if(canonicalProvenance(a)!==canonicalProvenance(b))throw new Error(label);}
/** Pure admission check; the domain independently revalidates stage/proofs against SQL. */
export function validateIngestionRasterTransition(value:unknown,original:IngestionArtifactReceipt,scope:JobScope){
 const parsed=z.object({original_raw_receipt:artifactReceipt,effective_raw_receipt:artifactReceipt,augmentation_receipt:z.object({format:z.literal('primary-raster-reference-augmentation-receipt-v1'),original_raw_receipt:artifactReceipt,effective_raw_receipt:artifactReceipt,target_source_ids:sourceIds,context_source_ids:sourceIds,base_publication:identifier,base_publication_sha256:hash,base_artifact_sha256:hash,bypass_exact:z.boolean(),source_body_verified:z.literal(false),ready_promoted:z.literal(false),promotion_performed:z.literal(false),receipt_sha256:hash}).passthrough()}).strict().parse(value);
 same(parsed.original_raw_receipt,original,'Etapa raster perdeu o RAW original.');
 same(parsed.augmentation_receipt.original_raw_receipt,original,'Recibo interno raster perdeu o RAW original.');
 same(parsed.augmentation_receipt.effective_raw_receipt,parsed.effective_raw_receipt,'Recibos efetivos raster divergem.');
 for(const key of ['base_publication','base_publication_sha256','base_artifact_sha256','target_source_ids','context_source_ids'] as const)same(parsed.augmentation_receipt[key],scope[key],'Escopo da etapa raster diverge: '+key);
 const {receipt_sha256,...internal}=parsed.augmentation_receipt;
 if(createHash('sha256').update(canonicalProvenance(internal)).digest('hex')!==receipt_sha256)throw new Error('Digest interno raster diverge.');
 if(!scope.target_source_ids.some(id=>AM_SOURCES.has(id))&&!parsed.augmentation_receipt.bypass_exact)throw new Error('Alvo não AM exige bypass raster exato.');
 if(parsed.augmentation_receipt.bypass_exact)same(original,parsed.effective_raw_receipt,'Bypass raster alterou caminho, ID ou SHA do RAW original.');
 return parsed.effective_raw_receipt;
}
/** Bounded argv subprocess; abort/timeout wait for close, including SIGKILL escalation. */
export async function runIngestionCommand(command:string,args:string[],options:{signal?:AbortSignal;timeoutMs?:number;maxOutputBytes?:number}={}){
 options.signal?.throwIfAborted();
 return new Promise<string>((accept,reject)=>{
  const child=spawn(command,args,{stdio:['ignore','pipe','pipe'],env:process.env});let output='',stderr='',bytes=0,failure:unknown,killer:NodeJS.Timeout|undefined;
  const terminate=(reason:unknown)=>{failure??=reason;if(child.exitCode!==null)return;child.kill('SIGTERM');if(!killer){killer=setTimeout(()=>child.kill('SIGKILL'),5000);killer.unref();}};
  const onAbort=()=>terminate(options.signal?.reason??new Error('Ingestão cancelada.'));
  options.signal?.addEventListener('abort',onAbort,{once:true});if(options.signal?.aborted)onAbort();
  const timeout=setTimeout(()=>terminate(new Error('Tempo máximo da etapa de ingestão excedido.')),options.timeoutMs??Math.max(1000,Number(process.env.JOB_TIMEOUT_SECONDS||7200)*1000));timeout.unref();
  child.stdout.on('data',(chunk:Buffer)=>{bytes+=chunk.length;if(bytes>(options.maxOutputBytes??1024*1024)){terminate(new Error('Saída da etapa de ingestão excedeu o limite.'));return;}output+=chunk.toString();});
  child.stderr.on('data',(chunk:Buffer)=>{stderr=(stderr+chunk.toString()).slice(-4000);});
  const cleanup=()=>{clearTimeout(timeout);if(killer)clearTimeout(killer);options.signal?.removeEventListener('abort',onAbort);};
  child.once('error',error=>{failure??=error;});
  child.once('close',code=>{cleanup();if(failure)reject(failure);else if(code!==0)reject(new Error(`Etapa de ingestão terminou com código ${code}: ${stderr.slice(-1200)}`));else accept(output);});
 });
}
async function immutableJson(filename:string,value:unknown){
 await mkdir(dirname(filename),{recursive:true});const parent=await realpath(dirname(filename)),root=await realpath('var');if(!parent.startsWith(root+sep))throw new Error('Recibo de ingestão fora de var/.');
 const bytes=canonicalProvenance(value),sha256=createHash('sha256').update(bytes).digest('hex'),temporary=filename+'.tmp-'+randomUUID(),file=await open(temporary,'wx',0o600);
 try{await file.writeFile(bytes);await file.sync();}finally{await file.close();}
 try{await link(temporary,filename);}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;if(await artifactHash(filename)!==sha256)throw new Error('Recibo imutável de ingestão já existe com bytes diferentes.');}finally{await unlink(temporary).catch(()=>{});}
 return{path:relative(process.cwd(),filename),sha256};
}
async function stageRuntimeUnchanged(){for(const [path,sha] of Object.entries(LOADED_STAGE_PINS))if(await artifactHash(path)!==sha)throw new Error('Código raster mudou após carregamento; reinicie o worker com o runtime correto.');}
async function readRasterStage(pin:z.infer<typeof filePin>,directory:string,original:IngestionArtifactReceipt,scope:JobScope){
 if(isAbsolute(pin.path)||pin.path.split(/[\\/]/).includes('..'))throw new Error('Caminho raster deve ser relativo.');
 const path=await realpath(pin.path),root=await realpath(directory),info=await stat(path);if(!path.startsWith(root+sep)||!info.isFile()||info.size>64*1024*1024||await artifactHash(path)!==pin.sha256)throw new Error('Pin externo raster diverge do recibo específico do job.');
 const value=JSON.parse(await readFile(path,'utf8'));return validateIngestionRasterTransition(value,original,scope);
}
async function runRasterStage(original:IngestionArtifactReceipt,scope:JobScope,directory:string,signal?:AbortSignal){
 signal?.throwIfAborted();await stageRuntimeUnchanged();
 const key=createHash('sha256').update(canonicalProvenance({original,scope,runtime:LOADED_STAGE_PINS})).digest('hex');
 const receipt=await immutableJson(resolve(directory,'original-'+key+'.json'),original),scopePin=await immutableJson(resolve(directory,'scope-'+key+'.json'),scope),output=relative(process.cwd(),resolve(directory,'raster-'+key+'.json'));
 const python=process.env.PIPELINE_PYTHON||process.env.PYTHON_BIN||(existsSync('var/venv-pipeline/bin/python')?resolve('var/venv-pipeline/bin/python'):'python3');
 await runIngestionCommand(python,[RASTER_CLI,'--source-root',process.cwd(),'--storage-root',process.cwd(),'--original-receipt',receipt.path,'--original-receipt-sha256',receipt.sha256,'--job-scope',scopePin.path,'--job-scope-sha256',scopePin.sha256,'--output-receipt',output],{signal});
 await stageRuntimeUnchanged();signal?.throwIfAborted();const raster={path:output,sha256:await artifactHash(output)},effective=await readRasterStage(raster,directory,original,scope);return{raster,effective};
}
export function ingestionPin(job:Job){const value=pinSchema.safeParse(job.payload);if(!value.success)throw new Error('Job de atualização exige base publicada, SHA e fontes alvo fixados no enqueue; jobs antigos sem pin não são promovidos.');return{...value.data,target_sources:[...new Set(value.data.target_sources)].sort()};}
async function lease(job:Job,owner:string){const result=await pool.query("SELECT id FROM jobs WHERE id=$1 AND lease_owner=$2 AND attempts=$3 AND status='running' AND pause_requested=false AND lease_until>now()",[job.id,owner,job.attempts]);if(!result.rowCount)throw new Error('Lease ou pausa não permite iniciar esta etapa de ingestão.');}
async function artifactPath(filename:string,publication:string,directory?:string){
 const root=await realpath(resolve('data/bundles')),path=await realpath(resolve(filename));
 if(!path.startsWith(root+sep))throw new Error('Artefato fora do armazenamento de publicações.');
 if(directory){const expected=await realpath(directory);if(!expected.startsWith(root+sep)||!path.startsWith(expected+sep)||basename(path)!=='snapshot.manifest.json')throw new Error('Artefato não pertence ao diretório específico do job.');}
 else if(!basename(path).startsWith(publication+'.'))throw new Error('Nome do artefato parcial diverge do checkpoint.');
 const info=await stat(path);if(!info.isFile()||info.size>64*1024*1024)throw new Error('Manifesto excede o limite de metadados.');
 const metadata=JSON.parse(await readFile(path,'utf8'));if(metadata.id!==publication||metadata.format!=='curriculos-abertos/sharded-v1')throw new Error('Identidade ou formato do manifesto diverge do recibo.');return path;
}
async function artifactHash(filename:string){const digest=createHash('sha256');for await(const chunk of createReadStream(filename))digest.update(chunk);return digest.digest('hex');}
async function saveJobReceipt(job:Job,suffix:string,value:unknown,owner:string){await mkdir('var/jobs',{recursive:true});const destination=resolve('var/jobs',job.id+suffix),temporary=destination+'.tmp-'+owner;await writeFile(temporary,JSON.stringify(value)+'\n',{mode:0o600});await rename(temporary,destination);}
export async function ensureIngestionBase(job:Job,owner:string,signal?:AbortSignal){
 signal?.throwIfAborted();
 const pin=ingestionPin(job);await lease(job,owner);let receipt:z.infer<typeof baseSchema>;
 try{receipt=baseSchema.parse(JSON.parse(await readFile(resolve('var/jobs',job.id+'.base.json'),'utf8')));}
 catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;const exported=await exportIngestionBase({base_publication:pin.base_publication,directory:resolve('data/bundles','ingestion-base-'+job.id)});receipt={job_id:job.id,...exported};await saveJobReceipt(job,'.base.json',receipt,owner);}
 if(receipt.job_id!==job.id||receipt.base_publication!==pin.base_publication||receipt.base_publication_sha256!==pin.base_publication_sha256)throw new Error('Recibo de contexto não corresponde à base imutável fixada no job.');
 const path=await artifactPath(receipt.artifact,receipt.context_publication,resolve('data/bundles','ingestion-base-'+job.id));if(await artifactHash(path)!==receipt.artifact_sha256)throw new Error('SHA do contexto BR fixado diverge do recibo do job.');signal?.throwIfAborted();await lease(job,owner);return receipt;
}
export async function completedIngestionCheckpoint(jobId:string){
 try{const value=JSON.parse(await readFile(resolve('var/jobs',jobId+'.json'),'utf8'));const parsed=completed.safeParse(value);return parsed.success&&parsed.data.id===jobId?parsed.data:null;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
}
export async function importPreparedIngestion(job:Job,owner:string,signal?:AbortSignal){
 signal?.throwIfAborted();
 const pin=ingestionPin(job),base=await ensureIngestionBase(job,owner,signal),checkpoint=await completedIngestionCheckpoint(job.id);
 if(!checkpoint)throw new Error('Checkpoint concluído do mesmo job com artefato e contexto verificáveis não encontrado.');
 if(checkpoint.base_publication!==pin.base_publication||checkpoint.base_publication_sha256!==pin.base_publication_sha256||checkpoint.base_artifact_sha256!==base.artifact_sha256||JSON.stringify([...checkpoint.target_source_ids].sort())!==JSON.stringify(pin.target_sources))throw new Error('Recibo parcial não demonstra a base e o escopo fixados no job.');
 const rawPath=await artifactPath(checkpoint.artifact,checkpoint.publication);await lease(job,owner);const digest=await artifactHash(rawPath);if(digest!==checkpoint.artifact_sha256)throw new Error('Checksum do artefato parcial específico do job diverge do checkpoint.');
 const original:IngestionArtifactReceipt={publication:checkpoint.publication,artifact:relative(process.cwd(),rawPath),artifact_sha256:digest};
 const context=await loadBundleFile(base.artifact,{expected:{sha256:base.artifact_sha256}}),contextManifest=context.bundle as unknown as ShardedManifest;await verifyShardedManifest(contextManifest);
 const contextIds=contextManifest.sources.map(source=>source.id).sort();if(!contextIds.length||contextManifest.sources.some(source=>source.uf!=='BR')||new Set(contextIds).size!==contextIds.length)throw new Error('Contexto nacional pinado contém inventário inválido.');
 const scope:JobScope={base_publication:pin.base_publication,base_publication_sha256:pin.base_publication_sha256,base_artifact_sha256:base.artifact_sha256,target_source_ids:pin.target_sources,context_source_ids:contextIds};
 const directory=`var/jobs/${job.id}.provenance`,actorId='ingestion-job:'+job.id;
 const starting=await pool.query("UPDATE jobs SET progress=$2::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running' AND pause_requested=false AND lease_until>now()",[job.id,JSON.stringify({stage:job.result?'revalidating_prepared_global_candidate':'preparing_raw_provenance',base_publication:pin.base_publication,original_raw_publication:checkpoint.publication,target_source_ids:pin.target_sources}),owner,job.attempts]);if(!starting.rowCount)throw new Error('Lease perdida antes da composição global.');
 const replay=job.result?replaySchema.parse(job.result):null;
 let provenance:IngestionProvenanceInput,effective:IngestionArtifactReceipt;
 if(replay){
  if(replay.checkpoint!==`var/jobs/${job.id}.json`||replay.actor_id!==actorId||replay.base_publication!==pin.base_publication||replay.base_receipt.job_id!==job.id||replay.base_receipt.base_publication!==base.base_publication||replay.base_receipt.base_publication_sha256!==base.base_publication_sha256||replay.base_receipt.context_publication!==base.context_publication||replay.base_receipt.artifact_sha256!==base.artifact_sha256||replay.import_receipt.id!==replay.publication||replay.update_scope.base_publication!==pin.base_publication||replay.update_scope.candidate_publication!==replay.publication||JSON.stringify(replay.update_scope.target_source_ids)!==JSON.stringify(pin.target_sources)||replay.provenance.receipt_directory!==directory)throw new Error('Recibo persistido da retomada não corresponde aos inputs fixados.');
  same(replay.original_raw_receipt,original,'Retomada perdeu RAW original do checkpoint.');same(replay.provenance.original_raw_receipt,original,'Proveniência perdeu RAW original do checkpoint.');same(replay.raw_receipt,replay.effective_raw_receipt,'Retomada não identifica o RAW efetivo.');
  provenance=replay.provenance;effective=replay.effective_raw_receipt;
  if(!provenance.raster_stage_receipt)throw new Error('Retomada do worker exige recibo raster ou bypass explícito.');
  same(await readRasterStage(provenance.raster_stage_receipt,directory,original,scope),effective,'Etapa raster persistida diverge do efetivo.');
 }else{
  const stage=await runRasterStage(original,scope,directory,signal);effective=stage.effective;await lease(job,owner);signal?.throwIfAborted();
  const evaluation=await evaluateIngestionProvenance({effective_raw_receipt:effective,job_scope:scope,receipt_directory:directory,signal});
  provenance={original_raw_receipt:original,raster_stage_receipt:stage.raster,technical_evaluation_receipt:evaluation,receipt_directory:directory};
 }
 signal?.throwIfAborted();await lease(job,owner);
 const effectivePath=await artifactPath(effective.artifact,effective.publication);if(await artifactHash(effectivePath)!==effective.artifact_sha256)throw new Error('Checksum do RAW efetivo diverge da cadeia raster.');
 const input:GlobalIngestionInput={base_publication:pin.base_publication,target_source_ids:pin.target_sources,raw_artifact:effectivePath,raw_artifact_sha256:effective.artifact_sha256,base_artifact_sha256:base.artifact_sha256,output_directory:resolve('data/bundles','ingestion-update-'+job.id),actor_id:actorId,provenance,signal};
 let prepared:Awaited<ReturnType<typeof prepareGlobalIngestionUpdate>>;
 if(replay){
  const proof=await revalidatePreparedIngestionProvenance(input,replay.publication);same(proof,replay.provenance_receipt,'Proveniência revalidada difere do recibo global persistido.');signal?.throwIfAborted();await lease(job,owner);
  const savedPath=await artifactPath(replay.artifact,replay.publication,resolve('data/bundles','ingestion-update-'+job.id)),saved=await loadBundleFile(savedPath,{expected:{sha256:replay.artifact_sha256}});
  const receipt=await importShardedManifest(saved.bundle as unknown as ShardedManifest,replay.artifact_sha256,{root:resolve('data/bundles'),makeDefault:false});
  if(receipt.id!==replay.publication||receipt.sha256!==replay.import_receipt.sha256)throw new Error('Snapshot global persistido diverge do recibo da tentativa anterior.');
  signal?.throwIfAborted();prepared={publication:receipt.id,artifact:replay.artifact,artifact_sha256:replay.artifact_sha256,import_receipt:receipt,raw_receipt:effective,provenance_receipt:proof,update_scope:await verifyGlobalIngestionPreservation(pin.base_publication,receipt.id,pin.target_sources,actorId)};
 }else prepared=await prepareGlobalIngestionUpdate(input);
 signal?.throwIfAborted();await lease(job,owner);
 same(prepared.raw_receipt,effective,'Compositor não recebeu o RAW efetivo verificado.');
 if(!prepared.provenance_receipt||prepared.import_receipt.id!==prepared.publication||prepared.update_scope.mode!=='base-plus-source-update'||prepared.update_scope.base_publication!==pin.base_publication)throw new Error('Recibo global não corresponde à linhagem da atualização.');
 const globalPath=await artifactPath(prepared.artifact,prepared.publication,resolve('data/bundles','ingestion-update-'+job.id));if(await artifactHash(globalPath)!==prepared.artifact_sha256)throw new Error('Checksum do artefato global diverge do recibo preparado.');
 const visibility=(await pool.query('SELECT status FROM publication_visibility WHERE publication_id=$1',[prepared.publication])).rows[0]?.status;
 const result={checkpoint:`var/jobs/${job.id}.json`,stage:visibility==='published'?'already_published':'prepared',...prepared,original_raw_receipt:original,effective_raw_receipt:effective,provenance,base_receipt:base,base_publication:pin.base_publication,resume_method:replay?'verified_global_provenance_replay':'global_composition',visibility,actor_id:actorId,worker_instance:owner,actor_type:'automated',technical_review:'checksums, raster transition or exact bypass, pinned technical evaluation and SQL authority, schema, pinned BR context, outside-target preservation and references verified; no human pedagogical approval'};
 signal?.throwIfAborted();await lease(job,owner);await saveJobReceipt(job,'.prepared.json',result,owner);
 const stored=await pool.query("UPDATE jobs SET result=$2::jsonb,progress=$3::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$4 AND attempts=$5 AND status='running' AND pause_requested=false AND lease_until>now()",[job.id,JSON.stringify(result),JSON.stringify({stage:'prepared_global_candidate',publication:prepared.publication,base_publication:pin.base_publication,original_raw_publication:original.publication,effective_raw_publication:effective.publication,artifact:prepared.artifact}),owner,job.attempts]);if(!stored.rowCount)throw new Error('Lease perdida; candidato privado não será finalizado por esta tentativa.');
 signal?.throwIfAborted();await audit({id:actorId,actor_type:'automated'},'prepare_ingested_candidate','publication',prepared.publication,'Atualização global preparada sobre base fixada com proveniência técnica e preservação comprovadas; padrão não alterado.',null,{job_id:job.id,...result});return result;
}
