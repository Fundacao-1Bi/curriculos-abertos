import {mkdir,readFile,writeFile,rename,realpath,stat} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,sep,basename} from 'node:path';
import {z} from 'zod';
import {pool} from '../db/client';
import {exportIngestionBase,prepareGlobalIngestionUpdate,verifyGlobalIngestionPreservation} from '../domain/ingestion-update';
import {loadBundleFile} from '../domain/bundle-file';
import {importShardedManifest,verifyShardedManifest,type ShardedManifest} from '../domain/shards';
import {audit} from '../admin/auth';
import type {Job} from './jobs';
const identifier=z.string().regex(/^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$/),hash=z.string().regex(/^[a-f0-9]{64}$/);
const sourceIds=z.array(z.string().min(1).max(500)).min(1).max(500);
const pinSchema=z.object({base_publication:identifier,base_publication_sha256:hash,target_sources:sourceIds});
const baseSchema=z.object({job_id:z.uuid(),artifact:z.string().min(1).max(1000),artifact_sha256:hash,base_publication:identifier,base_publication_sha256:hash,context_publication:identifier});
const completed=z.object({id:z.string(),state:z.literal('completed'),publication:identifier,artifact:z.string().min(1).max(1000),artifact_sha256:hash,base_publication:identifier,base_publication_sha256:hash,base_artifact_sha256:hash,target_source_ids:sourceIds});
const replaySchema=z.object({checkpoint:z.string(),publication:identifier,artifact:z.string().min(1).max(1000),artifact_sha256:hash,actor_id:z.string(),base_publication:identifier,base_receipt:baseSchema,raw_receipt:z.object({publication:identifier,artifact:z.string(),artifact_sha256:hash}),import_receipt:z.object({id:identifier,sha256:hash}),update_scope:z.object({mode:z.literal('base-plus-source-update'),base_publication:identifier,candidate_publication:identifier,target_source_ids:sourceIds})});
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
export async function ensureIngestionBase(job:Job,owner:string){
 const pin=ingestionPin(job);await lease(job,owner);let receipt:z.infer<typeof baseSchema>;
 try{receipt=baseSchema.parse(JSON.parse(await readFile(resolve('var/jobs',job.id+'.base.json'),'utf8')));}
 catch(error){if((error as NodeJS.ErrnoException).code!=='ENOENT')throw error;const exported=await exportIngestionBase({base_publication:pin.base_publication,directory:resolve('data/bundles','ingestion-base-'+job.id)});receipt={job_id:job.id,...exported};await saveJobReceipt(job,'.base.json',receipt,owner);}
 if(receipt.job_id!==job.id||receipt.base_publication!==pin.base_publication||receipt.base_publication_sha256!==pin.base_publication_sha256)throw new Error('Recibo de contexto não corresponde à base imutável fixada no job.');
 const path=await artifactPath(receipt.artifact,receipt.context_publication,resolve('data/bundles','ingestion-base-'+job.id));if(await artifactHash(path)!==receipt.artifact_sha256)throw new Error('SHA do contexto BR fixado diverge do recibo do job.');return receipt;
}
export async function completedIngestionCheckpoint(jobId:string){
 try{const value=JSON.parse(await readFile(resolve('var/jobs',jobId+'.json'),'utf8'));const parsed=completed.safeParse(value);return parsed.success&&parsed.data.id===jobId?parsed.data:null;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
}
export async function importPreparedIngestion(job:Job,owner:string){
 const pin=ingestionPin(job),base=await ensureIngestionBase(job,owner),checkpoint=await completedIngestionCheckpoint(job.id);
 if(!checkpoint)throw new Error('Checkpoint concluído do mesmo job com artefato e contexto verificáveis não encontrado.');
 if(checkpoint.base_publication!==pin.base_publication||checkpoint.base_publication_sha256!==pin.base_publication_sha256||checkpoint.base_artifact_sha256!==base.artifact_sha256||JSON.stringify([...checkpoint.target_source_ids].sort())!==JSON.stringify(pin.target_sources))throw new Error('Recibo parcial não demonstra a base e o escopo fixados no job.');
 const rawPath=await artifactPath(checkpoint.artifact,checkpoint.publication);await lease(job,owner);const digest=await artifactHash(rawPath);if(digest!==checkpoint.artifact_sha256)throw new Error('Checksum do artefato parcial específico do job diverge do checkpoint.');
 const starting=await pool.query("UPDATE jobs SET progress=$2::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,JSON.stringify({stage:job.result?'revalidating_prepared_global_candidate':'composing_global_candidate',base_publication:pin.base_publication,raw_publication:checkpoint.publication,target_source_ids:pin.target_sources}),owner,job.attempts]);if(!starting.rowCount)throw new Error('Lease perdida antes da composição global.');
 const actorId='ingestion-job:'+job.id;
 let prepared:Awaited<ReturnType<typeof prepareGlobalIngestionUpdate>>;const replay=job.result?replaySchema.parse(job.result):null;
 if(replay){
  if(replay.checkpoint!==`var/jobs/${job.id}.json`||replay.actor_id!==actorId||replay.base_publication!==pin.base_publication||replay.base_receipt.job_id!==job.id||replay.base_receipt.base_publication!==base.base_publication||replay.base_receipt.base_publication_sha256!==base.base_publication_sha256||replay.base_receipt.context_publication!==base.context_publication||replay.base_receipt.artifact_sha256!==base.artifact_sha256||replay.raw_receipt.publication!==checkpoint.publication||resolve(replay.raw_receipt.artifact)!==rawPath||replay.raw_receipt.artifact_sha256!==digest||replay.import_receipt.id!==replay.publication||replay.update_scope.base_publication!==pin.base_publication||replay.update_scope.candidate_publication!==replay.publication||JSON.stringify(replay.update_scope.target_source_ids)!==JSON.stringify(pin.target_sources))throw new Error('Recibo persistido da retomada não corresponde aos inputs fixados.');
  const raw=await loadBundleFile(rawPath,{expected:{sha256:digest}});await verifyShardedManifest(raw.bundle as unknown as ShardedManifest);
  const savedPath=await artifactPath(replay.artifact,replay.publication,resolve('data/bundles','ingestion-update-'+job.id));
  const saved=await loadBundleFile(savedPath,{expected:{sha256:replay.artifact_sha256}});
  const receipt=await importShardedManifest(saved.bundle as unknown as ShardedManifest,replay.artifact_sha256,{root:resolve('data/bundles'),makeDefault:false});
  if(receipt.id!==replay.publication||receipt.sha256!==replay.import_receipt.sha256)throw new Error('Snapshot global persistido diverge do recibo da tentativa anterior.');
  prepared={publication:receipt.id,artifact:replay.artifact,artifact_sha256:replay.artifact_sha256,import_receipt:receipt,raw_receipt:replay.raw_receipt,update_scope:await verifyGlobalIngestionPreservation(pin.base_publication,receipt.id,pin.target_sources,actorId)};
 }else prepared=await prepareGlobalIngestionUpdate({base_publication:pin.base_publication,target_source_ids:pin.target_sources,raw_artifact:rawPath,raw_artifact_sha256:digest,base_artifact_sha256:base.artifact_sha256,output_directory:resolve('data/bundles','ingestion-update-'+job.id),actor_id:actorId});
 if(prepared.raw_receipt.publication!==checkpoint.publication||prepared.import_receipt.id!==prepared.publication||prepared.update_scope.mode!=='base-plus-source-update'||prepared.update_scope.base_publication!==pin.base_publication)throw new Error('Recibo global não corresponde à linhagem da atualização.');
 const globalPath=await artifactPath(prepared.artifact,prepared.publication,resolve('data/bundles','ingestion-update-'+job.id));if(await artifactHash(globalPath)!==prepared.artifact_sha256)throw new Error('Checksum do artefato global diverge do recibo preparado.');
 const visibility=(await pool.query('SELECT status FROM publication_visibility WHERE publication_id=$1',[prepared.publication])).rows[0]?.status;
 const result={checkpoint:`var/jobs/${job.id}.json`,stage:visibility==='published'?'already_published':'prepared',...prepared,base_receipt:base,base_publication:pin.base_publication,resume_method:replay?'verified_global_receipt_replay':'global_composition',visibility,actor_id:actorId,worker_instance:owner,actor_type:'automated',technical_review:'checksums, schema, pinned BR context, exact outside-target preservation and references verified; no human pedagogical approval'};
 await saveJobReceipt(job,'.prepared.json',result,owner);
 const stored=await pool.query("UPDATE jobs SET result=$2::jsonb,progress=$3::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$4 AND attempts=$5 AND status='running'",[job.id,JSON.stringify(result),JSON.stringify({stage:'prepared_global_candidate',publication:prepared.publication,base_publication:pin.base_publication,raw_publication:checkpoint.publication,artifact:prepared.artifact}),owner,job.attempts]);if(!stored.rowCount)throw new Error('Lease perdida; candidato privado não será finalizado por esta tentativa.');
 await audit({id:actorId,actor_type:'automated'},'prepare_ingested_candidate','publication',prepared.publication,'Atualização global preparada sobre base fixada com preservação comprovada; padrão não alterado.',null,{job_id:job.id,...result});return result;
}
