import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { csvRows, downloadAndHash, validatePublishedCsvFile, validatePublishedJsonFile } from '../scripts/api-export-stream';
import { csvCell } from '../src/domain/normalize';

function fixture(){
 const source={id:'isolated-source',uf:'BR',title:'Fixture isolada, nunca corpus',issuer:'Teste',official_url:'https://example.invalid',artifact_url:'https://example.invalid/document.pdf',stages:['EF'],components:[],edition:null,document_date:null,homologation_date:null,application_period:null,document_type:'test',normative_parts:[],redistribution:'test',collected_at:null,sha256:null,local_path:null,status:'test'};
 const item={id:'isolated-item',curriculum_id:'isolated-source',source_id:'isolated-source',uf:'BR',code:null,text:'Texto íntegro, com "aspas" e\nlinhas adicionais.',normalized_text:'texto',editorial_note:null,kind:'test',parent_id:null,positions:[],evidence:[{source_id:'isolated-source',page:1,printed_page:null,section:null,excerpt:'Texto íntegro'}],extraction_revision:'test'};
 return{id:'isolated-publication',schema_version:'1.0.0',sources:[source],items:[item],relations:[],coverage:[{uf:'BR',ready:false}]};
}
test('JSON nacional é validado registro a registro e reconcilia contagens/IDs/texto/evidência',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'curriculos-stream-test-'));try{const b=fixture(),path=join(directory,'bundle.json');await writeFile(path,JSON.stringify(b));const result=await validatePublishedJsonFile(path,{publication:b.id,record_count:1,source_count:1,relation_count:0,sample:b.items[0]});assert.equal(result.items,1);assert.equal(result.sample_matches,1);assert.equal(result.json_valid,true);assert.equal(result.references_valid,true);assert.ok(result.max_record_bytes<2000);
 await writeFile(path,JSON.stringify(b).slice(0,-2));await assert.rejects(validatePublishedJsonFile(path,{publication:b.id}),'JSON truncado não pode passar');
 }finally{await rm(directory,{recursive:true,force:true});}
});
test('CSV incremental preserva JSON relacionado com vírgulas/aspas/quebras de linha e rejeita perda de referência',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'curriculos-csv-test-'));try{const b=fixture(),path=join(directory,'bundle.csv');const lines=[['record_type','id','payload_json'],['manifest',b.id,{publication:b.id,schema_version:b.schema_version}],['source',b.sources[0].id,b.sources[0]],['item',b.items[0].id,b.items[0]],['coverage','0',b.coverage[0]]];await writeFile(path,lines.map(row=>row.map(csvCell).join(',')).join('\r\n'));const result=await validatePublishedCsvFile(path,{publication:b.id,record_count:1,sample:b.items[0]});assert.equal(result.items,1);assert.equal(result.sources,1);const rows=[];for await(const row of csvRows(path))rows.push(row);assert.equal(JSON.parse(rows[3][2]).text,b.items[0].text);
 const invalid={...b,items:[{...b.items[0],source_id:'source-missing'}]};const json=join(directory,'invalid.json');await writeFile(json,JSON.stringify(invalid));await assert.rejects(validatePublishedJsonFile(json,{publication:b.id}),/Referência a fonte ausente/);
 }finally{await rm(directory,{recursive:true,force:true});}
});
test('download usa bytes em fluxo e confere SHA256 sem Response.text/JSON.parse nacional',async()=>{
 const directory=await mkdtemp(join(tmpdir(),'curriculos-download-test-'));try{const text='UTF-8 com acentos: educação\n';const response=new Response(text);const saved=await downloadAndHash(response,join(directory,'download.json'));assert.equal(saved.bytes,Buffer.byteLength(text));assert.equal(saved.sha256,createHash('sha256').update(text).digest('hex'));}finally{await rm(directory,{recursive:true,force:true});}
});
