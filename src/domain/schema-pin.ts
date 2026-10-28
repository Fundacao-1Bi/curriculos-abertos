/** Versioned, local JSON Schema verification. Never resolves a network schema or parses national arrays. */
import {constants} from 'node:fs';
import {lstat,open,realpath} from 'node:fs/promises';
import {basename,dirname,join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {z} from 'zod';
import {DomainError} from './errors';

// These bytes define immutable published contracts. A new contract requires a new version and reviewed digest.
export const PUBLICATION_SCHEMAS={
 '1.0.0':'23d783e8be1893a25f53abfb5d8d555b686b6dc6833c7506f0faa203c4abf416',
 '1.1.0':'cfe3c8cf165f34faa7aa29fda55245df4ce1bfa47d3b4c8bde15eec6f588d5df',
} as const;
type Version=keyof typeof PUBLICATION_SCHEMAS;
type Declaration={schema_version?:unknown;schema_path?:unknown;schema_sha256?:unknown};
type Kind='Source'|'Learning'|'Relation';
export interface SchemaPinOptions {schemaRoot?:string;}
export interface VerifiedPublicationSchema {version:Version;status:'pinned'|'legacy-unpinned-1.0.0';schema_path:string;schema_sha256:string;validate(kind:Kind,record:unknown):void;}
const MAX_SCHEMA_BYTES=64*1024;
const compiled=new Map<Version,Record<Kind,z.ZodType>>();
function fail(code:string,message:string):never{throw new DomainError(422,code,message);}
function zodDocument(document:Record<string,unknown>):Record<string,unknown>{
 const adapt=(node:unknown):unknown=>{if(Array.isArray(node))return node.map(adapt);if(!node||typeof node!=='object')return node;const value=Object.fromEntries(Object.entries(node).map(([key,child])=>[key,adapt(child)]));
  // The only implicitly typed branches in these fixed schemas constrain Evidence, already an object.
  // Zod's converter otherwise ignores their properties/required keywords.
  if(value.properties&&value.type===undefined)value.type='object';return value;};
 const result=adapt(document) as Record<string,unknown>,defs=result.$defs as Record<string,Record<string,unknown>>,properties=defs.Source.properties as Record<string,Record<string,unknown>>;
 // JSON Schema counts Unicode code points; Zod string.max counts UTF-16 units. Enforce this bound below.
 delete properties.id.maxLength;return result;
}
/** Synchronous shape/version check, also used by validateBundle before any file or database work. */
export function assertSchemaDeclaration(value:Declaration):Version{
 const version=value.schema_version;
 if(typeof version!=='string'||!Object.hasOwn(PUBLICATION_SCHEMAS,version))fail('UNSUPPORTED_DATA_SCHEMA','Versão de schema de dados não suportada; use 1.0.0 ou 1.1.0.');
 const pathPresent=Object.hasOwn(value,'schema_path'),hashPresent=Object.hasOwn(value,'schema_sha256');
 if(pathPresent!==hashPresent)fail('INCOMPLETE_SCHEMA_PIN','schema_path e schema_sha256 devem ser declarados juntos.');
 if(!pathPresent){if(version!=='1.0.0')fail('SCHEMA_PIN_REQUIRED','Publicações 1.1.0 exigem pin explícito de JSON Schema.');return version as Version;}
 if(value.schema_path!==`data/schema/${version}.json`)fail('SCHEMA_VERSION_PATH_MISMATCH','Caminho de JSON Schema deve corresponder exatamente à versão declarada em data/schema.');
 if(value.schema_sha256!==PUBLICATION_SCHEMAS[version as Version])fail('SCHEMA_PIN_MISMATCH','Checksum declarado não corresponde ao contrato imutável desta versão.');
 return version as Version;
}
/** Original/restore bundle roots share data/schema; transcode caches explicitly retain their original schema root. */
export function schemaRootForBundleRoot(bundleRoot?:string):string{
 const root=resolve(bundleRoot??'data/bundles');return basename(root)==='bundles'&&basename(dirname(root))==='data'?resolve(root,'../schema'):resolve('data/schema');
}
export async function verifyPublicationSchema(value:Declaration,options:SchemaPinOptions={}):Promise<VerifiedPublicationSchema>{
 const version=assertSchemaDeclaration(value),root=resolve(options.schemaRoot??'data/schema'),path=join(root,version+'.json');
 try{
  if((await lstat(root)).isSymbolicLink()||(await lstat(path)).isSymbolicLink())fail('SCHEMA_PATH_ESCAPE','JSON Schema não pode redirecionar por link simbólico.');
  const base=await realpath(root),located=await realpath(path);if(located!==join(base,version+'.json'))fail('SCHEMA_PATH_ESCAPE','JSON Schema fora do diretório permitido.');
  const file=await open(located,constants.O_RDONLY|constants.O_NOFOLLOW);let bytes:Buffer;
  try{const info=await file.stat();if(!info.isFile()||info.size<1||info.size>MAX_SCHEMA_BYTES)fail('SCHEMA_SIZE_LIMIT','JSON Schema excede o limite local de 64 KiB.');const buffer=Buffer.alloc(MAX_SCHEMA_BYTES+1),read=await file.read(buffer,0,buffer.length,0);if(read.bytesRead!==info.size)fail('SCHEMA_CHANGED','JSON Schema mudou durante a leitura limitada.');bytes=buffer.subarray(0,read.bytesRead);}finally{await file.close();}
  const hash=createHash('sha256').update(bytes).digest('hex');if(hash!==PUBLICATION_SCHEMAS[version])fail('SCHEMA_FILE_MISMATCH','Arquivo local de JSON Schema diverge do contrato imutável desta versão.');
  let validators=compiled.get(version);
  if(!validators){const document=JSON.parse(bytes.toString('utf8')) as Record<string,unknown>;if(document.$id!==`urn:curriculos-abertos:schema:${version}`||document.$schema!=='https://json-schema.org/draft/2020-12/schema')fail('SCHEMA_ID_MISMATCH','Identidade interna do JSON Schema diverge da versão suportada.');const normalized=zodDocument(document);
   const compile=(kind:Kind)=>z.fromJSONSchema({$schema:normalized.$schema,$defs:normalized.$defs,$ref:`#/$defs/${kind}`} as Parameters<typeof z.fromJSONSchema>[0],{defaultTarget:'draft-2020-12',registry:z.registry()});
   // Zod 4.6.7, already locked, supports only local refs here; no request/fetch is performed.
   validators={Source:compile('Source').refine(record=>[...String((record as Record<string,unknown>).id)].length<=240,'Source.id deve ter até 240 pontos de código Unicode.'),Learning:compile('Learning'),Relation:compile('Relation')};compiled.set(version,validators);
  }
  const selected=validators;
  return{version,status:Object.hasOwn(value,'schema_path')?'pinned':'legacy-unpinned-1.0.0',schema_path:`data/schema/${version}.json`,schema_sha256:hash,validate(kind,record){const result=selected[kind].safeParse(record);if(!result.success)fail('RECORD_SCHEMA_MISMATCH',`${kind} não satisfaz JSON Schema ${version}: `+result.error.issues.slice(0,3).map(issue=>issue.path.map(String).join('.')+': '+issue.message).join('; '));}};
 }catch(error){if(error instanceof DomainError)throw error;fail('SCHEMA_FILE_INVALID','JSON Schema local não pôde ser verificado com segurança.');}
}
