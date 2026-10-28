import { createHash } from 'node:crypto';
import { mkdir,open,unlink } from 'node:fs/promises';
import { dirname } from 'node:path';
import type pg from 'pg';
import { pool } from '../db/client';
import type { Query } from '../shared/contracts';
import { boundedQuery,itemFilter,resolvePublication,panorama,compare,analyses,listSources } from './service';
import { DomainError } from './errors';
import { csvCell } from './normalize';
const FILTERS=['uf','stage','component','area','q','curriculum','kind','year','edition','age_group','period','source_id','parent_id','national_id','relation_type','origin','technical_validation_status','pedagogical_review_status','publication_status'];
async function* encoded(value:unknown):AsyncGenerator<string> {if(value instanceof Date){yield JSON.stringify(value.toISOString());}else if(Array.isArray(value)){yield'[';let first=true;for(const item of value){if(!first)yield',';first=false;yield*encoded(item);}yield']';}else if(value&&typeof value==='object'){yield'{';let first=true;for(const[key,item]of Object.entries(value)){if(item===undefined)continue;if(!first)yield',';first=false;yield JSON.stringify(key)+':';yield*encoded(item);}yield'}';}else yield JSON.stringify(value??null);}
async function* records(client:pg.PoolClient,table:'items'|'relations'|'sources',publication:string,selection:string):AsyncGenerator<{id:string;content:string}> {let last='';for(;;){const rows=await client.query(`SELECT x.id,x.payload::text AS content FROM ${table} x WHERE x.publication_id=$1 AND x.id>$2 ${selection} ORDER BY x.id LIMIT 50`,[publication,last]);if(!rows.rowCount)break;for(const row of rows.rows){yield row;last=row.id;}}}
async function* jsonArray(client:pg.PoolClient,table:'items'|'relations'|'sources',publication:string,selection:string) {yield'[';let first=true;for await(const row of records(client,table,publication,selection)){if(!first)yield',';first=false;yield row.content;}yield']';}
async function prepareSelection(client:pg.PoolClient,q:Query,publication:string,unfiltered:boolean) {
 await client.query('CREATE TEMP TABLE export_items(id text PRIMARY KEY,matched boolean NOT NULL) ON COMMIT DROP');
 const f=itemFilter(q,publication);await client.query(`INSERT INTO export_items(id,matched) SELECT i.id,true FROM items i WHERE ${f.where}`,f.values);
 const matched=(await client.query('SELECT count(*)::int count FROM export_items')).rows[0].count as number;if(matched>1_000_000)throw new DomainError(413,'EXPORT_TOO_LARGE','Recorte excede limite operacional.');
 await client.query('CREATE TEMP TABLE export_relations(id text PRIMARY KEY) ON COMMIT DROP');
 await client.query('INSERT INTO export_relations(id) SELECT DISTINCT m.relation_id FROM relation_members m JOIN export_items e ON e.id=m.item_id WHERE m.publication_id=$1',[publication]);
 await client.query('INSERT INTO export_items(id,matched) SELECT DISTINCT m.item_id,false FROM relation_members m JOIN export_relations r ON r.id=m.relation_id WHERE m.publication_id=$1 ON CONFLICT DO NOTHING',[publication]);
 await client.query(`WITH RECURSIVE ancestors(id,parent_id) AS (SELECT i.id,i.payload->>'parent_id' FROM items i JOIN export_items e ON e.id=i.id WHERE i.publication_id=$1 UNION SELECT p.id,p.payload->>'parent_id' FROM items p JOIN ancestors a ON p.id=a.parent_id WHERE p.publication_id=$1) INSERT INTO export_items(id,matched) SELECT id,false FROM ancestors ON CONFLICT DO NOTHING`,[publication]);
 await client.query('CREATE TEMP TABLE export_sources(id text PRIMARY KEY) ON COMMIT DROP');
 if(unfiltered)await client.query('INSERT INTO export_sources(id) SELECT id FROM sources WHERE publication_id=$1',[publication]);
 else await client.query(`INSERT INTO export_sources(id) SELECT DISTINCT id FROM (SELECT i.source_id AS id FROM items i JOIN export_items e ON e.id=i.id WHERE i.publication_id=$1 UNION SELECT v->>'source_id' FROM items i JOIN export_items e ON e.id=i.id CROSS JOIN LATERAL jsonb_array_elements(i.evidence) v WHERE i.publication_id=$1 UNION SELECT v->>'source_id' FROM relations r JOIN export_relations e ON e.id=r.id CROSS JOIN LATERAL jsonb_array_elements(r.payload->'evidence') v WHERE r.publication_id=$1) s WHERE id IS NOT NULL`,[publication]);
 const counts=(await client.query('SELECT (SELECT count(*)::int FROM export_items) AS item_count,(SELECT count(*)::int FROM export_relations) AS relation_count,(SELECT count(*)::int FROM export_sources) AS source_count')).rows[0];
 const support=(await client.query('SELECT id FROM export_items WHERE matched=false ORDER BY id')).rows.map(x=>x.id as string);return{matched,...counts,support};
}
export async function streamExportToFile(input:Query={},format:'json'|'csv'='json',filename:string) {
 if(!['json','csv'].includes(format))throw new DomainError(400,'INVALID_EXPORT_FORMAT','Formato deve ser json ou csv.');
 const q=boundedQuery(input),publication=await resolvePublication(q.publication);await mkdir(dirname(filename),{recursive:true});
 const file=await open(filename,'wx',0o600);const hash=createHash('sha256');let size=0;let pending='';
 const append=async(text:string)=>{pending+=text;if(Buffer.byteLength(pending)>=65536){hash.update(pending);size+=Buffer.byteLength(pending);await file.writeFile(pending);pending='';}};
 let client:pg.PoolClient|undefined;let recordCount=0;let manifest:Record<string,unknown>={};
 try{client=await pool.connect();await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ');
 const row=(await client.query("SELECT schema_version,created_at,extraction_revision,mapping_revision,item_count,source_count,relation_count,storage_format,(payload - 'items' - 'relations') AS metadata FROM publications WHERE id=$1",[publication])).rows[0];
 const baseManifest={publication,schema_version:row.schema_version,filters:input,generated_at:row.created_at,extraction_revision:row.extraction_revision,mapping_revision:row.mapping_revision,rights:'Código MIT; textos oficiais preservam direitos dos órgãos emissores. Consulte cada fonte. CSV é uma tabela tipada de payloads JSON com neutralização de fórmulas.'};
 if(['panorama','comparison','analyses'].includes(String(q.view))){let report:unknown;
 if(q.view==='panorama'){if(typeof q.item_id!=='string')throw new DomainError(400,'MISSING_ITEM_ID','Panorama exige item_id.');report=await panorama(q.item_id,{...q,publication},{unpaginated:true});}
 else if(q.view==='comparison'){const ufs=Array.isArray(q.ufs)?q.ufs:String(q.ufs??'').split(',');report=await compare({...q,publication,ufs:ufs as string[]},{unpaginated:true});}
 else report=await analyses({...q,publication},{unpaginated:true});
 recordCount=Number((report as {total?:number}).total??0);manifest={...baseManifest,view:q.view,unpaginated:true,csv_structure:'json_report contém o relatório integral serializado.'};
 const payload={...report as object,sources:(await listSources({publication})).data,export_manifest:manifest};
 if(format==='csv')await append('json_report\r\n"');for await(const token of encoded(payload))await append(format==='csv'?token.replace(/"/g,'""'):token);if(format==='csv')await append('"\r\n');
 }else{
 const unfiltered=!FILTERS.some(key=>q[key]!==undefined&&q[key]!==null&&q[key]!=='');const selected=await prepareSelection(client,q,publication,unfiltered);recordCount=selected.matched;
 const meta=row.metadata as Record<string,unknown>;for(const key of ['sources','coverage','items','relations','parts','format','storage_format'])delete meta[key];
 const coverage=(await client.query('SELECT payload FROM publication_coverage WHERE publication_id=$1 ORDER BY row_index',[publication])).rows.map(x=>x.payload).filter(c=>!q.uf||c.uf===q.uf).map(c=>unfiltered?c:{...c,ready:false,reconciled:false,export_scope:'Recorte; cobertura nacional de origem não certifica este subconjunto.'});
 manifest={...baseManifest,item_count:selected.item_count,matched_item_count:selected.matched,source_count:selected.source_count,relation_count:selected.relation_count,support_item_ids:selected.support,relation_policy:'Membros diretos e ancestrais são suporte explícito; vínculos e IDs permanecem intactos.',csv_structure:'record_type,id,payload_json: manifest,source,item,relation,coverage.'};
 if(!unfiltered){const filterEntries=Object.entries(input).filter(([k,v])=>!['page','limit','publication'].includes(k)&&v!==undefined).sort(([a],[b])=>a.localeCompare(b));meta.id=publication.slice(0,120)+'-slice-'+createHash('sha256').update(JSON.stringify({publication,filters:filterEntries})).digest('hex').slice(0,16);meta.parent_publication=publication;meta.publication_kind='filtered_export';meta.national_release_ready=false;meta.coverage_statement='Recorte autocontido; não representa a base nacional completa.';meta.verification={type:'filtered_export',parent_publication:publication};meta.export_manifest=manifest;}
 if(row.storage_format==='relational-v1'||!unfiltered){meta.item_count=selected.item_count;meta.relation_count=selected.relation_count;}
 if(format==='json'){await append('{');let first=true;for(const[key,value]of Object.entries(meta)){if(!first)await append(',');first=false;await append(JSON.stringify(key)+':');for await(const token of encoded(value))await append(token);}for(const[table,key,selection]of [['sources','sources','AND x.id IN (SELECT id FROM export_sources)'],['items','items','AND x.id IN (SELECT id FROM export_items)'],['relations','relations','AND x.id IN (SELECT id FROM export_relations)']] as const){await append((first?'':',')+JSON.stringify(key)+':');first=false;for await(const token of jsonArray(client,table,publication,selection))await append(token);}await append(',"coverage":');for await(const token of encoded(coverage))await append(token);await append('}');}
 else {await append('record_type,id,payload_json\r\n');await append(['manifest',publication,manifest].map(csvCell).join(',')+'\r\n');for(const[table,type,selection]of [['sources','source','AND x.id IN (SELECT id FROM export_sources)'],['items','item','AND x.id IN (SELECT id FROM export_items)'],['relations','relation','AND x.id IN (SELECT id FROM export_relations)']] as const)for await(const record of records(client,table,publication,selection))await append([type,record.id,record.content].map(csvCell).join(',')+'\r\n');for(let index=0;index<coverage.length;index++)await append(['coverage',String(index),coverage[index]].map(csvCell).join(',')+'\r\n');}
 }
 if(pending){hash.update(pending);size+=Buffer.byteLength(pending);await file.writeFile(pending);pending='';}await file.sync();await client.query('COMMIT');await file.close();
 return{publication,filename:`curriculos-abertos-${publication}${q.view?'-'+String(q.view):''}.${format}`,mime_type:format==='json'?'application/json; charset=utf-8':'text/csv; charset=utf-8',record_count:recordCount,sha256:hash.digest('hex'),size,manifest};
 }catch(error){if(client)await client.query('ROLLBACK');await file.close().catch(()=>{});await unlink(filename).catch(()=>{});throw error;}finally{client?.release();}
}
