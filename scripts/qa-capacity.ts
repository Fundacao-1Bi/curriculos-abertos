/** Explicit incremental disk budgets. The build's independent 15-GiB guard is unchanged. */
import assert from 'node:assert/strict';
import {statfsSync} from 'node:fs';
import type {Learning} from '../src/shared/contracts';
import type {ArtifactHandle} from './audit-artifact';

export const GiB=1024**3;
export interface ArtifactFootprint {publication:string;compressed_bytes:number;decoded_bytes:number;metadata_bytes:number;items:number;largest_uf:string;largest_uf_primary_bytes:number;largest_uf_items:number;national_json_upper_bytes:number;}
export interface DatabaseFootprint {database_bytes:number;item_payload_bytes:number;relation_payload_bytes:number;source_payload_bytes:number;metadata_bytes:number;coverage_bytes:number;id_bytes:number;items:number;largest_uf:string;largest_uf_primary_bytes:number;largest_uf_items:number;national_json_upper_bytes:number;}
export interface CapacityBudget {stage:'production'|'reimport'|'recovery';components:{name:string;bytes:number;basis:string}[];subtotal_bytes:number;reserve_bytes:number;required_free_bytes:number;notes:string[];}
function bytes(value:number,name:string){assert.ok(Number.isSafeInteger(value)&&value>=0,`${name}: tamanho inválido`);return value;}
function budget(stage:CapacityBudget['stage'],components:CapacityBudget['components'],notes:string[]):CapacityBudget {
 for(const component of components)bytes(component.bytes,component.name);
 const subtotal=bytes(components.reduce((n,c)=>n+c.bytes,0),'subtotal');
 const reserve=Math.max(2*GiB,Math.ceil(subtotal*.2));
 return{stage,components,subtotal_bytes:subtotal,reserve_bytes:reserve,required_free_bytes:bytes(subtotal+reserve,'total'),notes};
}
export async function artifactFootprint(artifact:ArtifactHandle):Promise<ArtifactFootprint>{
 const metadata=Object.fromEntries(Object.entries(artifact.header).filter(([key])=>!['items','relations','parts'].includes(key)));
 const metadata_bytes=Buffer.byteLength(JSON.stringify(metadata)),ufs=new Map<string,{bytes:number;items:number}>();
 let decoded=artifact.parts.reduce((n,p)=>n+bytes(p.decoded_bytes,'decoded part'),0),idBytes=0,legacyItems=0;
 for await(const record of artifact.records('items')){
  const item=record as Learning,length=Buffer.byteLength(JSON.stringify(item))+1;
  const row=ufs.get(item.uf)||{bytes:0,items:0};row.bytes+=length;row.items++;ufs.set(item.uf,row);
  idBytes+=Buffer.byteLength(item.id)+4;legacyItems+=length;
 }
 if(!artifact.parts.length){decoded=legacyItems;for await(const row of artifact.records('relations'))decoded+=Buffer.byteLength(JSON.stringify(row))+1;}
 const largest=[...ufs].filter(([uf])=>uf!=='BR').sort((a,b)=>b[1].bytes-a[1].bytes)[0];
 assert.ok(largest,'Capacidade exige uma UF real com registros');
 return{publication:artifact.header.id,compressed_bytes:artifact.parts.reduce((n,p)=>n+bytes(p.bytes,'compressed part'),0),decoded_bytes:decoded,metadata_bytes,items:artifact.item_count,largest_uf:largest[0],largest_uf_primary_bytes:largest[1].bytes,largest_uf_items:largest[1].items,national_json_upper_bytes:bytes(2*(decoded+metadata_bytes)+idBytes+1024**2,'JSON upper bound')};
}
export function measureDatabaseFootprint(publication:string,query:(statement:string)=>string):DatabaseFootprint {
 assert.ok(publication.length>0&&publication.length<=200&&!publication.includes('\0'));
 const id="'"+publication.replaceAll("'","''")+"'";
 const row=JSON.parse(query(`SELECT json_build_object('database_bytes',pg_database_size(current_database()),'item_payload_bytes',(SELECT coalesce(sum(octet_length(payload::text)),0) FROM items WHERE publication_id=${id}),'relation_payload_bytes',(SELECT coalesce(sum(octet_length(payload::text)),0) FROM relations WHERE publication_id=${id}),'source_payload_bytes',(SELECT coalesce(sum(octet_length(payload::text)),0) FROM sources WHERE publication_id=${id}),'metadata_bytes',(SELECT octet_length(payload::text) FROM publications WHERE id=${id}),'coverage_bytes',(SELECT coalesce(sum(octet_length(payload::text)),0) FROM publication_coverage WHERE publication_id=${id}),'id_bytes',(SELECT coalesce(sum(octet_length(id)+4),0) FROM items WHERE publication_id=${id}),'items',(SELECT count(*) FROM items WHERE publication_id=${id}));`)) as DatabaseFootprint;
 for(const [name,value]of Object.entries(row))bytes(value as number,name);
 const largest=JSON.parse(query(`SELECT row_to_json(x) FROM (SELECT uf,count(*) AS items,sum(octet_length(payload::text)) AS bytes FROM items WHERE publication_id=${id} AND uf<>'BR' GROUP BY uf ORDER BY bytes DESC,uf LIMIT 1)x;`)) as {uf:string;items:number;bytes:number};
 assert.match(largest.uf,/^[A-Z]{2}$/);bytes(largest.bytes,'UF bytes');bytes(largest.items,'UF items');
 // A filtered export may include direct relation members from every UF. Budget the entire
 // national graph for that support, rather than assuming its size scales with matched items.
 return{...row,largest_uf:largest.uf,largest_uf_primary_bytes:largest.bytes,largest_uf_items:largest.items,national_json_upper_bytes:bytes(row.item_payload_bytes+row.relation_payload_bytes+row.source_payload_bytes+4*(row.metadata_bytes+row.coverage_bytes+row.id_bytes)+8*row.items+1024**2,'measured JSON upper bound')};
}
export function productionBudget(artifact:ArtifactFootprint){
 const database=Math.max(512*1024**2,2*bytes(artifact.national_json_upper_bytes,'artifact bound'));
 return budget('production',[{name:'new database including indexes',bytes:database,basis:'estimate: 2 × verified artifact JSON upper bound; replaced by measured PG size after import'},{name:'WAL during import',bytes:Math.max(GiB,database),basis:'one estimated database or 1GiB'},{name:'index build workspace',bytes:Math.ceil(database*.25),basis:'25% of estimated database'}],['Estimated before the first database exists; no claim of measured FULL runtime size.','Existing main/rollback databases and the production image are already allocated and are not reclaimable budget inputs.']);
}
export function reimportBudget(database:DatabaseFootprint,artifact:ArtifactFootprint){
 const json=bytes(database.national_json_upper_bytes,'national JSON'),db=bytes(database.database_bytes,'measured PG database');
 return budget('reimport',[{name:'server exports national + largest-UF closure',bytes:2*json,basis:'measured SQL payload upper bound; UF support bounded by entire national graph'},{name:'client HTTP downloads national + largest-UF closure',bytes:2*json,basis:'second complete copy, both checked before cleanup'},{name:'stream-converted shards and manifests',bytes:2*json+2*artifact.metadata_bytes+64*1024**2,basis:'allow gzip output as large as decoded JSON plus two metadata headers and bounded chunk workspace'},{name:'disposable reimport database: national + UF',bytes:2*db,basis:'twice measured clean database, including its indexes'},{name:'WAL and sort workspace',bytes:Math.max(GiB,db)+Math.ceil(db*.25),basis:'one database of WAL and 25% index workspace'}],[`Largest primary UF ${database.largest_uf}: ${database.largest_uf_items} items/${database.largest_uf_primary_bytes} SQL bytes.`,`Delivered artifact: ${artifact.decoded_bytes} decoded/${artifact.compressed_bytes} compressed bytes.`,`The national and UF copies coexist until complete byte/record verification. Cleanup occurs only after evidence, not as an assumption that reduces peak.`,`No fixed 3-GiB allowance; measured PostgreSQL and full payload sizes drive this budget.`]);
}
export function recoveryBudget(databaseBytes:number,dataBytes:number,storageBytes:number){
 const db=bytes(databaseBytes,'database'),data=bytes(dataBytes,'data tree'),storage=bytes(storageBytes,'storage');
 return budget('recovery',[{name:'pg_dump archive and restored database',bytes:2*db,basis:'measured clean PostgreSQL size, two copies'},{name:'WAL and restore index workspace',bytes:Math.max(GiB,db)+Math.ceil(db*.25),basis:'one database of WAL and 25% workspace'},{name:'data archive + extracted data',bytes:2*data,basis:'measured logical bytes in manifests/bundles/schema/coverage'},{name:'storage archive + restored storage',bytes:2*storage,basis:'measured files in the isolated QA storage volume'}],['Private backup archives remain preserved.','Only the uniquely named restored database and extracted QA copies may be removed after complete restore verification.']);
}
export function assertCapacityAvailable(plan:CapacityBudget,available?:{host:number;docker?:number}){
 const stats=available?undefined:statfsSync('.');const host=available?.host??stats!.bavail*stats!.bsize;
 bytes(host,'host free');if(available?.docker!==undefined)bytes(available.docker,'Docker free');
 const limiting=Math.min(host,available?.docker??host);
 assert.ok(limiting>=plan.required_free_bytes,`${plan.stage}: requer ${Math.ceil(plan.required_free_bytes/GiB*100)/100}GiB livres pelo orçamento; disponível ${Math.floor(limiting/GiB*100)/100}GiB. Nenhum recurso QA novo deve ser criado.`);
 return{host_free_bytes:host,...(available?.docker===undefined?{}:{docker_free_bytes:available.docker}),required_free_bytes:plan.required_free_bytes};
}
