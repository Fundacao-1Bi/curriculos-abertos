import {readFile} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve,sep,basename} from 'node:path';
import {z} from 'zod';
import {pool} from '../db/client';
import {importArtifactFile} from '../domain/shards';
import {audit} from '../admin/auth';
import type {Job} from './jobs';
const completed=z.object({id:z.string(),state:z.literal('completed'),publication:z.string().min(1).max(160),artifact:z.string().min(1).max(500),artifact_sha256:z.string().regex(/^[a-f0-9]{64}$/)});
export async function completedIngestionCheckpoint(jobId:string){
 try{const value=JSON.parse(await readFile(resolve('var/jobs',jobId+'.json'),'utf8'));const parsed=completed.safeParse(value);return parsed.success&&parsed.data.id===jobId?parsed.data:null;}catch(error){if((error as NodeJS.ErrnoException).code==='ENOENT')return null;throw error;}
}
export async function importPreparedIngestion(job:Job,owner:string){
 const checkpoint=await completedIngestionCheckpoint(job.id);if(!checkpoint)throw new Error('Checkpoint concluído do mesmo job com artefato verificável não encontrado.');
 const root=resolve('data/bundles'),path=resolve(checkpoint.artifact);
 if(!path.startsWith(root+sep)||!basename(path).startsWith(checkpoint.publication+'.'))throw new Error('Artefato do job fora do armazenamento de publicações.');
 const lease=await pool.query("SELECT id FROM jobs WHERE id=$1 AND lease_owner=$2 AND attempts=$3 AND status='running' AND pause_requested=false AND lease_until>now()",[job.id,owner,job.attempts]);
 if(!lease.rowCount)throw new Error('Lease não permite preparar esta ingestão.');
 const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);const digest=hash.digest('hex');if(digest!==checkpoint.artifact_sha256)throw new Error('Checksum do artefato específico do job diverge do checkpoint.');
 await pool.query("UPDATE jobs SET progress=$2::jsonb,updated_at=now() WHERE id=$1 AND lease_owner=$3 AND attempts=$4 AND status='running'",[job.id,JSON.stringify({stage:'importing_prepared_candidate',publication:checkpoint.publication,artifact:checkpoint.artifact}),owner,job.attempts]);
 const receipt=await importArtifactFile(path,{root,expected:{sha256:digest},makeDefault:false});
 if(receipt.id!==checkpoint.publication)throw new Error('Publicação importada diverge do checkpoint específico do job.');
 const visibility=(await pool.query('SELECT status FROM publication_visibility WHERE publication_id=$1',[receipt.id])).rows[0]?.status;
 const result={checkpoint:`var/jobs/${job.id}.json`,stage:visibility==='published'?'already_published':'prepared',publication:receipt.id,artifact:checkpoint.artifact,artifact_sha256:digest,import_receipt:receipt,visibility,actor_id:owner,actor_type:'automated',technical_review:'artifact checksums, schema and references verified by importer; no human pedagogical approval'};
 await audit({id:owner,actor_type:'automated'},'prepare_ingested_candidate','publication',receipt.id,'Ingestão concluída e importada em preparação sem alterar a publicação padrão.',null,{job_id:job.id,...result});
 return result;
}
