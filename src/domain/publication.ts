import { createHash } from 'node:crypto';
import { pool } from '../db/client';
import { UFS, type Bundle } from '../shared/contracts';
import { DomainError } from './errors';
import { normalize } from './normalize';

export function validateHierarchy(parents:Map<string,string>,ids:Set<string>) {
 for(const[id,parent]of parents)if(!ids.has(parent))throw new DomainError(422,'DANGLING_PARENT',id);
 const complete=new Set<string>();for(const id of parents.keys()){const active=new Set<string>();let current:string|undefined=id;while(current&&parents.has(current)&&!complete.has(current)){if(active.has(current))throw new DomainError(422,'CYCLIC_HIERARCHY','Hierarquia curricular cíclica.');active.add(current);current=parents.get(current);}for(const key of active)complete.add(key);}
}

export function validateBundle(value:unknown):asserts value is Bundle {
 if(!value || typeof value!=='object') throw new DomainError(422,'INVALID_BUNDLE','Publicação precisa ser um objeto JSON.');
 const b=value as Bundle;
 const checkReviews=(entity:Record<string,unknown>)=>{const events=entity.review_events;if(events!==undefined&&!Array.isArray(events))throw new DomainError(422,'INVALID_REVIEWS','Eventos de revisão devem ser uma lista.');if(Array.isArray(events))for(const event of events){if(!event||typeof event!=='object'||!['human','automated'].includes(event.actor_type)||typeof event.actor_id!=='string'||!event.actor_id)throw new DomainError(422,'INVALID_REVIEW_ACTOR','Revisão exige identidade e tipo real de ator.');}if(typeof entity.pedagogical_review_status==='string'&&/human|humana/.test(entity.pedagogical_review_status)&&(!Array.isArray(events)||!events.some(e=>e.actor_type==='human')))throw new DomainError(422,'UNSUPPORTED_HUMAN_REVIEW','Revisão humana alegada sem evento humano identificado.');};
 if(!/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,159}$/.test(b.id??'')) throw new DomainError(422,'INVALID_BUNDLE_ID','ID da publicação inválido.');
 for(const key of ['schema_version','created_at','extraction_revision','mapping_revision'] as const) if(typeof b[key]!=='string'||!b[key]) throw new DomainError(422,'INVALID_BUNDLE',`Campo obrigatório: ${key}`);
 if(!Number.isFinite(Date.parse(b.created_at))) throw new DomainError(422,'INVALID_BUNDLE','Data de criação inválida.');
 if(!Array.isArray(b.sources)||!Array.isArray(b.items)||!Array.isArray(b.relations)||!Array.isArray(b.coverage)||!Array.isArray(b.changelog)) throw new DomainError(422,'INVALID_BUNDLE','Coleções obrigatórias ausentes.');
 for(const [key,records]of [['item_count',b.items],['relation_count',b.relations],['source_count',b.sources]] as const)if(Object.hasOwn(b,key)&&b[key]!==records.length)throw new DomainError(422,'BUNDLE_COUNT_MISMATCH',`Contagem ${key} difere dos registros.`);
 for(const row of b.coverage)if(!row||typeof row!=='object'||Array.isArray(row))throw new DomainError(422,'INVALID_COVERAGE','Cobertura precisa de linhas estruturadas por recorte.');
 const sourceIds=new Set<string>(), sourcesById=new Map<string,Bundle['sources'][number]>(), itemIds=new Set<string>(), relationIds=new Set<string>();
 for(const s of b.sources) {
  if(typeof s.id!=='string'||!s.id||s.id.length>500||sourceIds.has(s.id)) throw new DomainError(422,'DUPLICATE_SOURCE',`Fonte duplicada ou inválida: ${s.id}`);
  if(s.uf!=='BR' && !(s.uf in UFS)) throw new DomainError(422,'INVALID_UF',`UF inválida: ${s.uf}`);
  for(const key of ['title','issuer','official_url','artifact_url','document_type','redistribution','status']) if(typeof s[key]!=='string') throw new DomainError(422,'INVALID_SOURCE',`Fonte ${s.id}: ${key} ausente.`);
  for(const key of ['official_url','artifact_url']) {try {const u=new URL(s[key] as string);if(!['https:','http:'].includes(u.protocol))throw Error();}catch{throw new DomainError(422,'INVALID_SOURCE_URL',`Fonte ${s.id}: URL inválida.`);}}
  if(!Array.isArray(s.stages)||s.stages.some(x=>!['EI','EF','EM'].includes(x))) throw new DomainError(422,'INVALID_SOURCE','Etapa inválida.');
  if(!Array.isArray(s.components)||s.components.some(c=>typeof c!=='string')||!Array.isArray(s.normative_parts)||s.normative_parts.some(p=>typeof p!=='string'))throw new DomainError(422,'INVALID_SOURCE','Componentes e partes esperadas devem ser listas.');
  if(s.sha256!==null&&!/^[a-f0-9]{64}$/.test(s.sha256??''))throw new DomainError(422,'INVALID_SOURCE_HASH',s.id);
  sourceIds.add(s.id);sourcesById.set(s.id,s);
 }
 for(const item of b.items) {
  if(typeof item.id!=='string'||!item.id||item.id.length>500||itemIds.has(item.id)) throw new DomainError(422,'DUPLICATE_ITEM',`Item duplicado ou inválido: ${item.id}`);
  if(!sourceIds.has(item.source_id)) throw new DomainError(422,'DANGLING_SOURCE',`Fonte não encontrada: ${item.source_id}`);
  if(item.uf!==sourcesById.get(item.source_id)?.uf)throw new DomainError(422,'ITEM_SOURCE_UF_MISMATCH',`UF divergente da fonte: ${item.id}`);
  if(item.uf!=='BR'&&!(item.uf in UFS))throw new DomainError(422,'INVALID_UF',`UF inválida: ${item.uf}`);
  if(typeof item.curriculum_id!=='string'||!item.curriculum_id||typeof item.text!=='string'||!item.text.trim()||typeof item.kind!=='string') throw new DomainError(422,'INVALID_ITEM',`Item sem contexto/texto/tipo: ${item.id}`);
  if(typeof item.normalized_text!=='string'||!Object.hasOwn(item,'parent_id')||!Object.hasOwn(item,'editorial_note')||typeof item.extraction_revision!=='string'||(item.parent_id!==null&&typeof item.parent_id!=='string')||(item.editorial_note!==null&&typeof item.editorial_note!=='string'))throw new DomainError(422,'INVALID_ITEM','Campos canônicos ausentes.');
  if(item.code_aliases!==undefined&&(!Array.isArray(item.code_aliases)||item.code_aliases.length>100||item.code_aliases.some(a=>typeof a!=='string'||!a||a.length>500)))throw new DomainError(422,'INVALID_CODE_ALIASES','Aliases devem ser códigos textuais documentados.');
  checkReviews(item);
  if(item.code!==null&&typeof item.code!=='string')throw new DomainError(422,'INVALID_ITEM','Código deve ser texto ou nulo.');
  if(!Array.isArray(item.positions)||!Array.isArray(item.evidence)||!item.evidence.length)throw new DomainError(422,'MISSING_EVIDENCE',`Item sem evidência: ${item.id}`);
  for(const p of item.positions) {if(!sourcesById.get(item.source_id)?.stages.includes(p.stage))throw new DomainError(422,'ITEM_SOURCE_STAGE_MISMATCH',`Etapa divergente da fonte: ${item.id}`);if(!['EI','EF','EM'].includes(p.stage))throw new DomainError(422,'INVALID_POSITION',item.id);if(p.years!==null&&(!Array.isArray(p.years)||p.years.some(y=>!Number.isInteger(y)||y<1||y>12)))throw new DomainError(422,'INVALID_POSITION',item.id);}
  if(!item.evidence.some(e=>e.source_id===item.source_id))throw new DomainError(422,'MISSING_PRIMARY_EVIDENCE',item.id);
  for(const e of item.evidence) if(!sourceIds.has(e.source_id)||typeof e.excerpt!=='string'||!e.excerpt.trim()||(e.page!==null&&(!Number.isInteger(e.page)||e.page<1))||(e.page===null&&!e.section))throw new DomainError(422,'INVALID_EVIDENCE',`Localizador ausente/inválido: ${item.id}`);
  itemIds.add(item.id);
 }
 validateHierarchy(new Map(b.items.filter(i=>i.parent_id).map(i=>[i.id,i.parent_id!])),itemIds);
 for(const r of b.relations) {
  if(typeof r.id!=='string'||!r.id||r.id.length>500||relationIds.has(r.id))throw new DomainError(422,'DUPLICATE_RELATION',r.id);
  for(const key of ['relation_type','origin','technical_validation_status','pedagogical_review_status','publication_status','method'])if(typeof r[key]!=='string'||!r[key])throw new DomainError(422,'INVALID_RELATION',`Dimensão obrigatória ausente: ${key}`);
  if(!Array.isArray(r.members)||!r.members.some(m=>m.role==='source')||!r.members.some(m=>m.role==='target'))throw new DomainError(422,'INVALID_RELATION',`Relação sem direção: ${r.id}`);
  const keys=new Set<string>();for(const m of r.members) {if(!itemIds.has(m.item_id)||!['source','target'].includes(m.role)||typeof m.scope!=='string')throw new DomainError(422,'DANGLING_MEMBER',r.id);const key=m.item_id+':'+m.role;if(keys.has(key))throw new DomainError(422,'DUPLICATE_MEMBER',r.id);keys.add(key);}
  checkReviews(r);
  if(!Array.isArray(r.evidence))throw new DomainError(422,'INVALID_RELATION',r.id);
  for(const e of r.evidence)if(!sourceIds.has(e.source_id))throw new DomainError(422,'DANGLING_RELATION_EVIDENCE',r.id);
  relationIds.add(r.id);
 }
}

export async function setDefaultPublication(id:string,actor:{id:string;actor_type:'human'|'automated';reason:string}) {
 if(!actor.id||!actor.reason||!['human','automated'].includes(actor.actor_type))throw new DomainError(422,'ACTOR_REQUIRED','Ator e justificativa obrigatórios.');
 const client=await pool.connect();
 try{await client.query('BEGIN');await client.query('SELECT pg_advisory_xact_lock(81726354)');
 const found=await client.query('SELECT id FROM publications WHERE id=$1',[id]);if(!found.rowCount)throw new DomainError(404,'PUBLICATION_NOT_FOUND','Publicação inexistente.');
 const previous=await client.query('SELECT publication_id FROM current_publication WHERE singleton=true');
 await client.query('INSERT INTO current_publication(singleton,publication_id) VALUES(true,$1) ON CONFLICT(singleton) DO UPDATE SET publication_id=excluded.publication_id',[id]);
 await client.query('INSERT INTO publication_events(publication_id,previous_id,actor_id,actor_type,reason) VALUES($1,$2,$3,$4,$5)',[id,previous.rows[0]?.publication_id??null,actor.id,actor.actor_type,actor.reason]);
 await client.query('COMMIT');return{id,previous_id:previous.rows[0]?.publication_id??null};
 }catch(e){await client.query('ROLLBACK');throw e;}finally{client.release();}
}

async function samePublishedBundle(client:import('pg').PoolClient,id:string,bundle:Bundle):Promise<boolean> {
 const existing=await client.query("SELECT item_count,source_count,relation_count,(payload - 'items' - 'relations' - 'sources' - 'parts' - 'format' - 'storage_format') = $2::jsonb AS same_metadata FROM publications WHERE id=$1",[id,JSON.stringify(Object.fromEntries(Object.entries(bundle).filter(([key])=>!['items','relations','sources','parts','format','storage_format'].includes(key))))]);
 const row=existing.rows[0];if(!row||row.item_count!==bundle.items.length||row.source_count!==bundle.sources.length||row.relation_count!==bundle.relations.length||!row.same_metadata)return false;
 for(const[table,records]of [['sources',bundle.sources],['items',bundle.items],['relations',bundle.relations]] as const)for(let offset=0;offset<records.length;offset+=100){const batch=records.slice(offset,offset+100);const match=await client.query(`SELECT count(*)::int AS count FROM jsonb_to_recordset($2::jsonb) AS x(id text,payload jsonb) JOIN ${table} t ON t.publication_id=$1 AND t.id=x.id AND t.payload=x.payload`,[id,JSON.stringify(batch.map(payload=>({id:payload.id,payload})))]);if(match.rows[0].count!==batch.length)return false;}
 return true;
}

export async function importBundle(bundle:Bundle,options:{sha256?:string;makeDefault?:boolean}={}) {
 validateBundle(bundle);
 const serialized=JSON.stringify(bundle);
 let digest=createHash('sha256').update(serialized).digest('hex');
 if(options.sha256&&options.sha256!==digest)throw new DomainError(422,'CHECKSUM_MISMATCH','Checksum do conteúdo canônico divergente.');
 const client=await pool.connect();let already_imported=false;
 try{await client.query('BEGIN');await client.query('SELECT pg_advisory_xact_lock(81726354)');
 const old=await client.query('SELECT sha256 FROM publications WHERE id=$1',[bundle.id]);
 if(old.rowCount) {if(old.rows[0].sha256!==digest){const same=await samePublishedBundle(client,bundle.id,bundle);if(!same)throw new DomainError(409,'IMMUTABLE_PUBLICATION','ID já existe com conteúdo diferente. Crie outra publicação.');}already_imported=true;digest=old.rows[0].sha256;}
 else {
 await client.query('INSERT INTO publications(id,schema_version,created_at,extraction_revision,mapping_revision,sha256,item_count,source_count,relation_count,payload) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)',[bundle.id,bundle.schema_version,bundle.created_at,bundle.extraction_revision,bundle.mapping_revision,digest,bundle.items.length,bundle.sources.length,bundle.relations.length,serialized]);
 await client.query('INSERT INTO publication_metadata(publication_id,changelog,payload) VALUES($1,$2::jsonb,$3::jsonb)',[bundle.id,JSON.stringify(bundle.changelog),JSON.stringify({publication_kind:bundle.publication_kind??null,coverage_statement:bundle.coverage_statement??null,national_release_ready:bundle.national_release_ready??false})]);
 await client.query(`INSERT INTO publication_coverage(publication_id,row_index,uf,stage,component,payload) SELECT $1,x.row_index,x.uf,x.stage,x.component,x.payload FROM jsonb_to_recordset($2::jsonb) AS x(row_index integer,uf text,stage text,component text,payload jsonb)`,[bundle.id,JSON.stringify(bundle.coverage.map((payload,index)=>{const row=payload as Record<string,unknown>;return{row_index:index+1,uf:row.uf??null,stage:row.stage??null,component:row.component??null,payload};}))]);
 for(const s of bundle.sources)await client.query('INSERT INTO sources(publication_id,id,uf,payload) VALUES($1,$2,$3,$4)',[bundle.id,s.id,s.uf,JSON.stringify(s)]);
 for(let offset=0;offset<bundle.items.length;offset+=500){const chunk=bundle.items.slice(offset,offset+500);
 await client.query(`INSERT INTO items(publication_id,id,uf,curriculum_id,source_id,code,text,normalized_text,kind,positions,evidence,payload)
 SELECT $1,x.id,x.uf,x.curriculum_id,x.source_id,x.code,x.text,x.normalized_text,x.kind,x.positions,x.evidence,x.payload FROM jsonb_to_recordset($2::jsonb) AS x(id text,uf text,curriculum_id text,source_id text,code text,text text,normalized_text text,kind text,positions jsonb,evidence jsonb,payload jsonb)`,[bundle.id,JSON.stringify(chunk.map(item=>({...item,normalized_text:normalize(item.text),payload:item})))]);}
 for(let offset=0;offset<bundle.relations.length;offset+=500){const chunk=bundle.relations.slice(offset,offset+500);await client.query(`INSERT INTO relations(publication_id,id,relation_type,origin,technical_validation_status,pedagogical_review_status,publication_status,payload) SELECT $1,x.id,x.relation_type,x.origin,x.technical_validation_status,x.pedagogical_review_status,x.publication_status,x.payload FROM jsonb_to_recordset($2::jsonb) AS x(id text,relation_type text,origin text,technical_validation_status text,pedagogical_review_status text,publication_status text,payload jsonb)`,[bundle.id,JSON.stringify(chunk.map(r=>({...r,payload:r})))]);const members=chunk.flatMap(r=>r.members.map(m=>({...m,relation_id:r.id})));await client.query(`INSERT INTO relation_members(publication_id,relation_id,item_id,role,scope) SELECT $1,x.relation_id,x.item_id,x.role,x.scope FROM jsonb_to_recordset($2::jsonb) AS x(relation_id text,item_id text,role text,scope text)`,[bundle.id,JSON.stringify(members)]);}
 }
 if(options.makeDefault){const previous=await client.query('SELECT publication_id FROM current_publication WHERE singleton=true');await client.query('INSERT INTO current_publication(singleton,publication_id) VALUES(true,$1) ON CONFLICT(singleton) DO UPDATE SET publication_id=excluded.publication_id',[bundle.id]);if(previous.rows[0]?.publication_id!==bundle.id)await client.query('INSERT INTO publication_events(publication_id,previous_id,actor_id,actor_type,reason) VALUES($1,$2,$3,$4,$5)',[bundle.id,previous.rows[0]?.publication_id??null,'data-import','automated','Importação validada por schema e integridade referencial. Não constitui revisão pedagógica.']);}
 await client.query('COMMIT');return{id:bundle.id,sha256:digest,already_imported,item_count:bundle.items.length};
 }catch(e){await client.query('ROLLBACK');throw e;}finally{client.release();}
}
