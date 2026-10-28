import {pool} from '../db/client';
import {getPublicationInternal,searchLearningsInternal} from '../domain/service';
import {setDefaultPublication} from '../domain/publication';
import {audit,AdminError,type Actor} from './auth';
export async function listIngestCandidates(){
 const rows=await pool.query(`WITH latest AS (SELECT DISTINCT ON (result->>'publication') id,result,updated_at FROM jobs WHERE type='ingest' AND status='succeeded' AND result->>'publication' IS NOT NULL AND result->'import_receipt' IS NOT NULL ORDER BY result->>'publication',updated_at DESC)
 SELECT p.id,p.created_at,p.item_count,p.source_count,p.relation_count,v.status AS visibility,j.id AS job_id,j.result->>'artifact' AS artifact,j.result->>'artifact_sha256' AS artifact_sha256,a.after_data AS validation
 FROM latest j JOIN publications p ON p.id=j.result->>'publication' JOIN publication_visibility v ON v.publication_id=p.id
 LEFT JOIN LATERAL(SELECT after_data FROM audit_events WHERE action='validate_ingested_candidate' AND entity_id=p.id AND after_data->>'sha256'=p.sha256 ORDER BY created_at DESC LIMIT 1)a ON true
 ORDER BY p.created_at DESC,p.id DESC LIMIT 100`);return rows.rows;
}
async function validationFor(id:string,sha:string){return(await pool.query("SELECT after_data FROM audit_events WHERE action='validate_ingested_candidate' AND entity_type='publication' AND entity_id=$1 AND after_data->>'sha256'=$2 ORDER BY created_at DESC LIMIT 1",[id,sha])).rows[0]?.after_data || null;}
export async function getIngestCandidate(id:string){
 const response=await getPublicationInternal(id);const row=response.data;
 const [sample,jobs,validation]=await Promise.all([searchLearningsInternal({publication:id,limit:10}),pool.query("SELECT id,type,status,progress,result,created_at,updated_at FROM jobs WHERE type='ingest' AND status='succeeded' AND result->>'publication'=$1 ORDER BY updated_at DESC LIMIT 20",[id]),validationFor(id,row.sha256)]);
 return{publication:id,visibility:row.visibility_status,metadata:{id:row.id,schema_version:row.schema_version,created_at:row.created_at,extraction_revision:row.extraction_revision,mapping_revision:row.mapping_revision,storage_format:row.storage_format,sha256:row.sha256,artifact_manifest_sha256:row.artifact_manifest_sha256,coverage_statement:row.metadata?.coverage_statement,publication_kind:row.metadata?.publication_kind},counts:{items:row.item_count,sources:row.source_count,relations:row.relation_count},sources:row.sources,sample_items:sample.data,validation,ingestion_jobs:jobs.rows};
}
async function assertImportedCandidate(id:string){
 const row=(await pool.query("SELECT p.id,p.sha256,p.item_count,p.source_count,p.relation_count,v.status AS visibility,j.id AS job_id,j.result->'import_receipt' AS receipt FROM publications p JOIN publication_visibility v ON v.publication_id=p.id JOIN LATERAL(SELECT id,result FROM jobs WHERE type='ingest' AND status='succeeded' AND result->>'publication'=p.id AND result->'import_receipt'->>'id'=p.id ORDER BY updated_at DESC LIMIT 1)j ON true WHERE p.id=$1",[id])).rows[0];
 if(!row)throw new AdminError(404,'candidate_not_found','Candidato de ingestão com recibo verificado não encontrado.');
 if(row.receipt?.sha256!==row.sha256)throw new AdminError(409,'candidate_receipt_mismatch','Recibo da ingestão não corresponde ao snapshot imutável.');return row;
}
export async function validateIngestCandidate(actor:Actor,id:string,reason:string){
 if(actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador valida candidatos de ingestão.');
 if(reason.length<8)throw new AdminError(422,'reason_required','Informe uma justificativa para a validação.');
 const candidate=await assertImportedCandidate(id);const client=await pool.connect();
 try{await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');await client.query("SET LOCAL statement_timeout='120s'");
 const counts=(await client.query('SELECT (SELECT count(*)::int FROM items WHERE publication_id=$1) AS items,(SELECT count(*)::int FROM sources WHERE publication_id=$1) AS sources,(SELECT count(*)::int FROM relations WHERE publication_id=$1) AS relations',[id])).rows[0];
 const integrity=(await client.query(`SELECT
 (SELECT count(*)::int FROM items i LEFT JOIN sources s ON s.publication_id=i.publication_id AND s.id=i.source_id WHERE i.publication_id=$1 AND s.id IS NULL) AS source_orphans,
 (SELECT count(*)::int FROM items i LEFT JOIN items p ON p.publication_id=i.publication_id AND p.id=i.payload->>'parent_id' WHERE i.publication_id=$1 AND i.payload->>'parent_id' IS NOT NULL AND p.id IS NULL) AS parent_orphans,
 (SELECT count(*)::int FROM relation_members m LEFT JOIN items i ON i.publication_id=m.publication_id AND i.id=m.item_id LEFT JOIN relations r ON r.publication_id=m.publication_id AND r.id=m.relation_id WHERE m.publication_id=$1 AND (i.id IS NULL OR r.id IS NULL)) AS member_orphans,
 (SELECT count(*)::int FROM items i WHERE i.publication_id=$1 AND (jsonb_array_length(i.evidence)=0 OR NOT EXISTS(SELECT 1 FROM jsonb_array_elements(i.evidence)e WHERE e->>'source_id'=i.source_id))) AS missing_evidence`,[id])).rows[0];
 await client.query('COMMIT');
 const valid=counts.items===candidate.item_count&&counts.sources===candidate.source_count&&counts.relations===candidate.relation_count&&Object.values(integrity).every(value=>value===0);
 const validation={valid,publication:id,sha256:candidate.sha256,counts,integrity,import_job_id:candidate.job_id,technical_validation_status:valid?'validated':'failed',method:'verified importer receipt + relational counts/references/evidence',actor_id:'curriculos-abertos:candidate-validator',actor_type:'automated',requested_by:{id:actor.id,actor_type:actor.actor_type},reason,checked_at:new Date().toISOString(),pedagogical_review_status:'not_asserted',human_pedagogical_approval:false,national_release_ready:false,national_launch_gate:'make release-check; technical validation does not assert documentary/national completeness'};
 await audit({id:validation.actor_id,actor_type:'automated'},'validate_ingested_candidate','publication',id,reason,null,validation);
 if(!valid)throw new AdminError(422,'candidate_integrity_failed','Candidato não passou nas verificações técnicas. Consulte o resultado administrativo.');return validation;
 }catch(error){await client.query('ROLLBACK').catch(()=>{});throw error;}finally{client.release();}
}
export async function publishIngestCandidate(actor:Actor,id:string,reason:string){
 if(actor.role!=='administrator')throw new AdminError(403,'forbidden','Somente administrador publica candidatos de ingestão.');if(reason.length<8)throw new AdminError(422,'reason_required','Informe justificativa de publicação.');
 const candidate=await assertImportedCandidate(id),validation=await validationFor(id,candidate.sha256);
 if(!validation?.valid)throw new AdminError(409,'candidate_not_validated','Valide tecnicamente o candidato antes de publicar.');
 const result=await setDefaultPublication(id,{...actor,reason});
 await audit(actor,'publish_ingested_candidate','publication',id,reason,{publication:result.previous_id},{publication:result.id,validation_sha256:validation.sha256,validation_actor_type:validation.actor_type});
 return{...result,visibility:'published',pedagogical_review_status:'not_asserted'};
}
