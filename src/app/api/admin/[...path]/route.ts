import { z } from 'zod';
import { randomUUID } from 'node:crypto';
import { DomainError } from '../../../../domain/errors';
import { pool } from '../../../../db/client';
import { requireActor,requireSameOrigin,audit,AdminError } from '../../../../admin/auth';
import { createDraft,addChange,validateDraft,prepareDraft,publishDraft,rollbackPublication } from '../../../../admin/curation';
import { enqueueJob,controlJob } from '../../../../worker/jobs';
export const dynamic='force-dynamic';
export const runtime='nodejs';
const limits=new Map<string,{at:number;count:number}>();
function limit(id:string){const now=Date.now();const old=limits.get(id);if(!old||now-old.at>60000){limits.set(id,{at:now,count:1});return;}if(++old.count>60)throw new AdminError(429,'rate_limited','Aguarde antes de repetir operações.');}
async function parseBody(request:Request){const text=await request.text();if(text.length>120000)throw new AdminError(413,'body_too_large','Corpo excede o limite.');return JSON.parse(text);}
function respondError(error:unknown,requestId:string) {
  const status=error instanceof AdminError || error instanceof DomainError?error.status:error instanceof z.ZodError || error instanceof SyntaxError?422:500;
  if(status===500)console.error(JSON.stringify({event:'admin_request_failed',request_id:requestId,error:error instanceof Error?error.message:'Erro'}));
  return Response.json({error:{code:error instanceof AdminError || error instanceof DomainError?error.code:status===422?'validation_error':'internal_error',message:status===500?'Não foi possível concluir a operação.':error instanceof Error?error.message:'Erro'},request_id:requestId},{status,headers:{'Cache-Control':'no-store'}});
}
export async function GET(request:Request,context:{params:Promise<{path:string[]}>}) {
  const requestId=randomUUID();
  try {
    const actor=await requireActor(request.headers);limit(actor.id);
    const {path}=await context.params;
    const section=path.join('/');
    let data:unknown;
    if(section==='overview') {
      const [jobs,contributions,drafts,checks,publications,events,workers]=await Promise.all([
        pool.query('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100'),
        pool.query('SELECT * FROM contributions ORDER BY created_at DESC LIMIT 100'),
        pool.query('SELECT id,base_publication,title,status,validation,prepared_publication,created_by,created_at,updated_at,jsonb_array_length(changes) AS change_count FROM drafts ORDER BY created_at DESC LIMIT 100'),
        pool.query('SELECT * FROM source_checks ORDER BY checked_at DESC LIMIT 100'),
        pool.query('SELECT id,item_count,source_count,created_at FROM publications ORDER BY created_at DESC'),
        pool.query('SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100'),
        pool.query('SELECT * FROM worker_heartbeats')
      ]);
      data={actor,jobs:jobs.rows,contributions:contributions.rows,drafts:drafts.rows,source_checks:checks.rows,publications:publications.rows,audit:events.rows,workers:workers.rows};
    }else if(path[0]==='jobs'&&path[1]) {
      z.uuid().parse(path[1]);
      const [job,events]=await Promise.all([pool.query('SELECT * FROM jobs WHERE id=$1',[path[1]]),pool.query('SELECT event,created_at FROM job_events WHERE job_id=$1 ORDER BY id DESC LIMIT 200',[path[1]])]);
      if(!job.rowCount)throw new AdminError(404,'not_found','Job não encontrado.');data={job:job.rows[0],events:events.rows};
    }else if(path[0]==='drafts'&&path[1]) {
      z.uuid().parse(path[1]);const result=await pool.query('SELECT * FROM drafts WHERE id=$1',[path[1]]);
      if(!result.rowCount)throw new AdminError(404,'not_found','Rascunho não encontrado.');data=result.rows[0];
    }else throw new AdminError(404,'not_found','Operação não encontrada.');
    return Response.json({data,request_id:requestId},{headers:{'Cache-Control':'no-store'}});
  }catch(error){return respondError(error,requestId);}
}
export async function POST(request:Request,context:{params:Promise<{path:string[]}>}) {
  const requestId=randomUUID();
  try {
    requireSameOrigin(request);
    const actor=await requireActor(request.headers);limit(actor.id);
    const {path}=await context.params;const body=await parseBody(request);
    let data:unknown;
    if(path.join('/')==='jobs') {
      const input=z.object({type:z.enum(['ingest','source-check','validate']),source:z.string().regex(/^[a-zA-Z0-9_.:-]{1,200}$/).optional(),draft_id:z.uuid().optional()}).parse(body);
      if(input.type==='ingest'&&actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador inicia ingestão.');
      data=await enqueueJob(input.type,{source:input.source,draft_id:input.draft_id});
      await audit(actor,'enqueue_job','job',(data as {id:string}).id,'Processamento solicitado pela administração.',null,{type:input.type,source:input.source});
    }else if(path[0]==='jobs'&&path[1]&&path[2]) {
      const action=z.enum(['pause','resume','retry']).parse(path[2]);
      const job=await pool.query('SELECT type FROM jobs WHERE id=$1',[z.uuid().parse(path[1])]);
      if(job.rows[0]?.type==='ingest'&&actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador controla jobs de ingestão.');
      data=await controlJob(path[1],action);await audit(actor,action,'job',path[1],`Operação de job: ${action}.`);
    }else if(path.join('/')==='drafts')data=await createDraft(actor,body);
    else if(path[0]==='drafts'&&path[1]&&path[2]) {
      z.uuid().parse(path[1]);
      if(path[2]==='changes')data=await addChange(actor,path[1],body);
      else if(path[2]==='validate'){data=await validateDraft(path[1]);await audit(actor,'validate_draft','draft',path[1],'Validação técnica de schema e referências; não é homologação pedagógica.');}
      else if(path[2]==='prepare')data=await prepareDraft(actor,path[1],z.object({reason:z.string().min(8).max(4000)}).parse(body).reason);
      else if(path[2]==='publish')data=await publishDraft(actor,path[1],z.object({reason:z.string().min(8).max(4000)}).parse(body).reason);
      else throw new AdminError(404,'not_found','Operação não encontrada.');
    }else if(path.join('/')==='publications/rollback') {
      const input=z.object({publication:z.string().min(1).max(160),reason:z.string().min(8).max(4000)}).parse(body);
      data=await rollbackPublication(actor,input.publication,input.reason);
    }else if(path[0]==='contributions'&&path[1]&&path[2]==='decide') {
      const id=z.uuid().parse(path[1]);
      const input=z.object({status:z.enum(['accepted','rejected','needs_information']),reason:z.string().min(8).max(4000)}).parse(body);
      const before=await pool.query('SELECT * FROM contributions WHERE id=$1',[id]);
      if(!before.rowCount)throw new AdminError(404,'not_found','Contribuição não encontrada.');
      const result=await pool.query('UPDATE contributions SET status=$2,decision_reason=$3,decided_by=$4,updated_at=now() WHERE id=$1 RETURNING *',[id,input.status,input.reason,actor.id]);
      data=result.rows[0];await audit(actor,'decide_contribution','contribution',id,input.reason,before.rows[0],data);
    }else throw new AdminError(404,'not_found','Operação não encontrada.');
    return Response.json({data,request_id:requestId},{headers:{'Cache-Control':'no-store'}});
  }catch(error){return respondError(error,requestId);}
}
