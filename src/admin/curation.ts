import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { pool } from '../db/client';
import { setDefaultPublication } from '../domain/publication';
import { validateRelationalRevision,prepareRelationalRevision,type RevisionMeta } from '../domain/revisions';
import { audit, AdminError, type Actor } from './auth';
const changeSchema=z.discriminatedUnion('entity',[
  z.object({entity:z.literal('item'),record_id:z.string().min(1).max(400),text:z.string().min(1).max(100000),reason:z.string().min(8).max(4000)}),
  z.object({entity:z.literal('relation'),record_id:z.string().min(1).max(400),decision:z.enum(['accept','reject','contest']),review_type:z.enum(['publication','technical','pedagogical']).default('publication'),method:z.string().min(8).max(2000).optional(),review_evidence:z.string().min(8).max(6000).optional(),reason:z.string().min(8).max(4000)})
]);
type Change=z.infer<typeof changeSchema> & {actor_id:string;actor_type:Actor['actor_type'];at:string};
type Draft={revision:number;id:string;base_publication:string;title:string;status:string;changes:Change[];validation:Record<string,unknown>|null;prepared_publication:string|null;created_by:string;created_at:string;updated_at:string};
export async function createDraft(actor:Actor,input:{base_publication:string;title:string}) {
  const value=z.object({base_publication:z.string().min(1).max(160),title:z.string().min(3).max(200)}).parse(input);
  const exists=await pool.query('SELECT id FROM publications WHERE id=$1',[value.base_publication]);
  if(!exists.rowCount)throw new AdminError(404,'not_found','Publicação base não encontrada.');
  const id=randomUUID();
  const result=await pool.query('INSERT INTO drafts(id,base_publication,title,created_by) VALUES($1,$2,$3,$4) RETURNING *',[id,value.base_publication,value.title,actor.id]);
  await audit(actor,'create_draft','draft',id,'Rascunho criado a partir de publicação imutável.',null,value);
  return result.rows[0] as Draft;
}
async function getDraft(id:string):Promise<Draft> {
  z.uuid().parse(id);
  const result=await pool.query<Draft>('SELECT * FROM drafts WHERE id=$1',[id]);
  if(!result.rows[0])throw new AdminError(404,'not_found','Rascunho não encontrado.');
  return result.rows[0];
}
export async function addChange(actor:Actor,id:string,input:unknown) {
  const parsed=changeSchema.parse(input);
  if(parsed.entity==='relation'&&parsed.review_type==='pedagogical'&&(!parsed.method||!parsed.review_evidence))throw new AdminError(422,'review_evidence_required','Revisão pedagógica explícita exige método e evidência.');
  const change={...parsed,actor_id:actor.id,actor_type:actor.actor_type,at:new Date().toISOString()};
  const draft=await getDraft(id);
  if(draft.status!=='editing'&&draft.status!=='validated')throw new AdminError(409,'draft_locked','Crie outro rascunho para revisar uma publicação já preparada.');
  const result=await pool.query("UPDATE drafts SET changes=changes || $2::jsonb,status='editing',validation=NULL,updated_at=now(),revision=revision+1 WHERE id=$1 AND revision=$3 AND status IN ('editing','validated') RETURNING *",[id,JSON.stringify([change]),draft.revision]);
  if(!result.rowCount)throw new AdminError(409,'draft_changed','O rascunho mudou durante a operação. Atualize e tente novamente.');
  await audit(actor,'stage_change',change.entity,change.record_id,change.reason,null,change);
  return result.rows[0];
}
async function materializeDraft(id:string) {
  const draft=await getDraft(id);
  const found=await pool.query<{extraction_revision:string;mapping_revision:string}>('SELECT extraction_revision,mapping_revision FROM publications WHERE id=$1',[draft.base_publication]);
  const base=found.rows[0];
  if(!base)throw new AdminError(404,'not_found','Base não encontrada.');
  const meta:RevisionMeta={
    id:`${draft.base_publication.slice(0,120)}.r-${draft.id}`,
    created_at:new Date(draft.updated_at).toISOString(),
    extraction_revision:`${base.extraction_revision}.curation-${draft.id.slice(0,8)}`,
    mapping_revision:`${base.mapping_revision}.curation-${draft.id.slice(0,8)}`
  };
  return {draft,meta};
}
export async function validateDraft(id:string) {
  const {draft,meta}=await materializeDraft(id);
  const validation=await validateRelationalRevision(draft.base_publication,draft.changes,meta);
  const result={...validation,validation_type:'technical',human_pedagogical_approval:false,draft_revision:draft.revision,national_release:'requires_release_check'};
  // Do not update updated_at here: candidate timestamps must remain reproducible.
  const validated=await pool.query("UPDATE drafts SET status=CASE WHEN status='editing' THEN 'validated' ELSE status END,validation=$2::jsonb WHERE id=$1 AND revision=$3 RETURNING id",[id,JSON.stringify(result),draft.revision]);
  if(!validated.rowCount)throw new AdminError(409,'draft_changed','O rascunho mudou durante a validação.');
  return result;
}
export async function prepareDraft(actor:Actor,id:string,reason:string) {
  if(reason.length<8)throw new AdminError(422,'reason_required','Justificativa precisa ter pelo menos oito caracteres.');
  const initial=await getDraft(id);
  if(!['editing','validated'].includes(initial.status))throw new AdminError(409,'draft_locked','A preparação exige rascunho em edição ou validado.');
  const validation=await validateDraft(id);
  const {draft,meta}=await materializeDraft(id);
  if(!draft.changes.length)throw new AdminError(422,'empty_draft','Não há alterações para preparar.');
  const result=await prepareRelationalRevision(draft.base_publication,draft.changes,meta,{sha256:validation.sha256});
  const prepared=await pool.query("UPDATE drafts SET status='prepared',prepared_publication=$2 WHERE id=$1 AND revision=$3 AND status='validated' RETURNING id",[id,result.id,validation.draft_revision]);
  if(!prepared.rowCount)throw new AdminError(409,'draft_changed','O rascunho mudou durante a preparação. Nenhuma publicação foi promovida.');
  await audit(actor,'prepare_publication','draft',id,reason,null,{publication:result.id,validation});
  return result;
}
export async function publishDraft(actor:Actor,id:string,reason:string) {
  if(actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador pode publicar.');
  if(reason.length<8)throw new AdminError(422,'reason_required','Justificativa precisa ter pelo menos oito caracteres.');
  const draft=await getDraft(id);
  if(draft.status!=='prepared'||!draft.prepared_publication)throw new AdminError(409,'not_prepared','Prepare e valide o rascunho primeiro.');
  const result=await setDefaultPublication(draft.prepared_publication,{...actor,reason});
  await pool.query("UPDATE drafts SET status='published' WHERE id=$1",[id]);
  await audit(actor,'publish_default','publication',draft.prepared_publication,reason,{publication:result.previous_id},{publication:result.id});
  return result;
}
export async function rollbackPublication(actor:Actor,id:string,reason:string) {
  if(actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador pode reverter publicação.');
  if(reason.length<8)throw new AdminError(422,'reason_required','Informe justificativa.');
  const visibility=(await pool.query('SELECT status FROM publication_visibility WHERE publication_id=$1',[id])).rows[0]?.status;
  if(visibility!=='published')throw new AdminError(409,'not_published','A reversão exige uma publicação anteriormente publicada. Use a ação explícita de publicação para um candidato preparado.');
  const result=await setDefaultPublication(id,{...actor,reason});
  await audit(actor,'rollback_default','publication',id,reason,{publication:result.previous_id},{publication:result.id});
  return result;
}
