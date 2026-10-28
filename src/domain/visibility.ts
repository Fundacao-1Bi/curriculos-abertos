import type pg from 'pg';
import { DomainError } from './errors';
export interface PublicationActor {id:string;actor_type:'human'|'automated';reason:string;}
/** Trusted administrative/import path only; called inside the same transaction as the default pointer/audit event. */
export async function publishVisibility(client:pg.PoolClient,publication:string,actor:PublicationActor) {
 if(!actor.id||!actor.reason||!['human','automated'].includes(actor.actor_type))throw new DomainError(422,'ACTOR_REQUIRED','Ator real e justificativa obrigatórios.');
 const updated=await client.query(`UPDATE publication_visibility SET status='published',published_at=coalesce(published_at,now()),actor_id=coalesce(actor_id,$2),actor_type=coalesce(actor_type,$3),evidence=CASE WHEN status='prepared' THEN $4 ELSE evidence END WHERE publication_id=$1 RETURNING publication_id`,[publication,actor.id,actor.actor_type,actor.reason]);
 if(!updated.rowCount)throw new DomainError(404,'PUBLICATION_NOT_FOUND','Publicação inexistente.');
}
