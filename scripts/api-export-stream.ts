import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createReadStream, createWriteStream } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';
import { Readable, Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import parserStream from 'stream-json';
import FlexAssembler, { arrayRule } from 'stream-json/utils/flex-assembler.js';
import type { Token } from 'stream-json/parser.js';
import { LearningSchema, RelationSchema, SourceSchema } from '../src/mcp/contracts';

type RecordType='sources'|'items'|'relations'|'coverage';
type Counter={type:RecordType;count:number};
export interface ExportSummary {id:string;schema_version:string;items:number;sources:number;relations:number;coverage:number;sample_matches:number;max_record_bytes:number;parser:string;json_valid:true;references_valid:true;}
export interface ExportExpectations {publication:string;record_count?:number;source_count?:number;relation_count?:number;sample?:{id:string;text:string;evidence?:unknown};}

/** Download bytes directly to disk. Never materializes a national response/string. */
export async function downloadAndHash(response:Response,path:string){
 assert.ok(response.body,'Corpo da exportação obrigatório.');await mkdir(dirname(path),{recursive:true});
 const hash=createHash('sha256');let bytes=0;
 const meter=new Transform({transform(chunk:Buffer,_encoding,callback){bytes+=chunk.length;hash.update(chunk);callback(null,chunk);}});
 await pipeline(Readable.fromWeb(response.body as import('node:stream/web').ReadableStream<Uint8Array>),meter,createWriteStream(path,{flags:'w',mode:0o600}));
 return{path,bytes,sha256:hash.digest('hex')};
}

class RecordVerifier {
 readonly ids=new Set<string>();readonly sourceIds=new Set<string>();readonly relationIds=new Set<string>();
 readonly requiredItems=new Set<string>();readonly requiredSources=new Set<string>();
 readonly counts={sources:0,items:0,relations:0,coverage:0};maxRecordBytes=0;sampleMatches=0;
 constructor(readonly expected:ExportExpectations){}
 accept(type:RecordType,value:unknown){
  this.counts[type]++;
  // Upper bound is one canonical record, not the complete publication.
  this.maxRecordBytes=Math.max(this.maxRecordBytes,Buffer.byteLength(JSON.stringify(value)));
  if(type==='sources'){
   const source=SourceSchema.parse(value);assert.ok(!this.sourceIds.has(source.id),`Fonte duplicada: ${source.id}`);this.sourceIds.add(source.id);
  }else if(type==='items'){
   const item=LearningSchema.parse(value);assert.ok(!this.ids.has(item.id),`Item duplicado: ${item.id}`);this.ids.add(item.id);assert.ok(item.text.trim().length,'Texto canônico vazio.');assert.ok(item.evidence.length,`Item sem evidência: ${item.id}`);
   this.requiredSources.add(item.source_id);for(const evidence of item.evidence)this.requiredSources.add(evidence.source_id);if(item.parent_id)this.requiredItems.add(item.parent_id);
   if(this.expected.sample?.id===item.id){assert.equal(item.text,this.expected.sample.text);if(this.expected.sample.evidence)assert.deepEqual(item.evidence,this.expected.sample.evidence);this.sampleMatches++;}
  }else if(type==='relations'){
   const relation=RelationSchema.parse(value);assert.ok(!this.relationIds.has(relation.id),`Relação duplicada: ${relation.id}`);this.relationIds.add(relation.id);
   for(const member of relation.members)this.requiredItems.add(member.item_id);for(const evidence of relation.evidence)this.requiredSources.add(evidence.source_id);
  }else{assert.ok(value&&typeof value==='object','Cobertura deve ser estruturada.');}
 }
 finish(id:string,schemaVersion:string):ExportSummary{
  assert.equal(id,this.expected.publication);assert.ok(this.counts.items>0,'Exportação sem itens reais.');assert.ok(this.counts.sources>0,'Exportação sem fontes.');assert.ok(schemaVersion,'Schema obrigatório.');
  if(this.expected.record_count!==undefined)assert.equal(this.counts.items,this.expected.record_count,'Contagem nacional da exportação difere do job.');
  if(this.expected.source_count!==undefined)assert.equal(this.counts.sources,this.expected.source_count);
  if(this.expected.relation_count!==undefined)assert.equal(this.counts.relations,this.expected.relation_count);
  for(const id of this.requiredItems)assert.ok(this.ids.has(id),`Referência a item ausente: ${id}`);
  for(const id of this.requiredSources)assert.ok(this.sourceIds.has(id),`Referência a fonte ausente: ${id}`);
  if(this.expected.sample)assert.equal(this.sampleMatches,1,'ID/texto/evidência da API ausente ou duplicado no download.');
  return{id,schema_version:schemaVersion,...this.counts,sample_matches:this.sampleMatches,max_record_bytes:this.maxRecordBytes,parser:'stream-json@3.7.0; record-by-record',json_valid:true,references_valid:true};
 }
}

/** Parse the full JSON grammar and validate every record while discarding array payloads. */
export async function validatePublishedJsonFile(path:string,expected:ExportExpectations):Promise<ExportSummary>{
 const verifier=new RecordVerifier(expected);let completed=false;
 const types=new Set<RecordType>(['sources','items','relations','coverage']);
 const assembler=new FlexAssembler<Record<string,unknown>>({maxDepth:100,arrayRules:[arrayRule<Counter>({filter:p=>p.length===1&&types.has(p[0] as RecordType),create:p=>({type:p[0] as RecordType,count:0}),add:(counter,value)=>{verifier.accept(counter.type,value);counter.count++;},finalize:counter=>({count:counter.count})})]});
 const parser=parserStream({packValues:true,streamValues:false});
 const consume=new Transform({objectMode:true,transform(token:Token,_encoding,callback){try{assembler.consume(token);if(assembler.done){assert.equal(completed,false,'Mais de um valor JSON no arquivo.');completed=true;}callback();}catch(error){callback(error as Error);}}});
 await pipeline(createReadStream(path),parser,consume);assert.ok(completed&&assembler.done,'JSON incompleto.');
 const metadata=assembler.current;assert.ok(metadata&&typeof metadata==='object'&&!Array.isArray(metadata),'Bundle JSON deve ser objeto.');
 for(const key of types)assert.ok(metadata[key]&&typeof metadata[key]==='object'&&'count'in(metadata[key] as object),`Array obrigatório ausente: ${key}`);
 assert.ok(!('users'in metadata)&&!('contributions'in metadata)&&!('admin'in metadata),'Dados administrativos no download público.');
 return verifier.finish(String(metadata.id??''),String(metadata.schema_version??''));
}

/** CSV state machine: commas/newlines/escaped quotes across arbitrary chunk boundaries. */
export async function* csvRows(path:string):AsyncGenerator<string[]>{
 let row:string[]=[],field='',quoted=false,afterQuote=false,pendingCr=false,atStart=true;
 for await(const chunk of createReadStream(path,{encoding:'utf8'})){
  for(const c of chunk as string){
   if(atStart){atStart=false;if(c==='\uFEFF')continue;}
   if(pendingCr){pendingCr=false;if(c==='\n')continue;}
   if(quoted){if(c==='"'){quoted=false;afterQuote=true;}else field+=c;continue;}
   if(afterQuote&&c==='"'){field+='"';quoted=true;afterQuote=false;continue;}
   if(c===','){row.push(field);field='';afterQuote=false;continue;}
   if(c==='\n'||c==='\r'){row.push(field);yield row;row=[];field='';afterQuote=false;if(c==='\r')pendingCr=true;continue;}
   if(afterQuote)throw new Error('CSV inválido: caractere após fechamento de aspas.');
   if(c==='"'){assert.equal(field,'','CSV inválido: aspas em campo não delimitado.');quoted=true;continue;}
   field+=c;
  }
 }
 assert.equal(quoted,false,'CSV truncado em campo com aspas.');if(field||row.length){row.push(field);yield row;}
}
export async function validatePublishedCsvFile(path:string,expected:ExportExpectations):Promise<ExportSummary>{
 const verifier=new RecordVerifier(expected);let header:string[]|undefined,manifest:Record<string,unknown>|undefined;
 const names:Record<string,RecordType>={source:'sources',item:'items',relation:'relations',coverage:'coverage'};
 for await(const row of csvRows(path)){
  if(!header){header=row;assert.deepEqual(header,['record_type','id','payload_json']);continue;}
  assert.equal(row.length,3,'Registro CSV deve preservar as três colunas.');assert.ok(!/^[=+\-@\t\r]/.test(row[2]),'Fórmula executável no CSV público.');
  const value=JSON.parse(row[2].startsWith("'")?row[2].slice(1):row[2]);
  if(row[0]==='manifest'){assert.ok(!manifest,'Manifesto CSV duplicado.');manifest=value;}
  else{const type=names[row[0]];assert.ok(type,`Tipo CSV não documentado: ${row[0]}`);verifier.accept(type,value);if(type!=='coverage')assert.equal((value as {id:string}).id,row[1]);}
 }
 assert.ok(manifest,'Manifesto CSV obrigatório.');return verifier.finish(String(manifest.publication??''),String(manifest.schema_version??''));
}
