/** Server-owned provenance bridge. BASE records always come from PostgreSQL, never a caller JSON capture. */
import {createHash,randomUUID} from 'node:crypto';
import {createReadStream,existsSync,readFileSync} from 'node:fs';
import {link,mkdir,open,readFile,realpath,stat,unlink} from 'node:fs/promises';
import {dirname,isAbsolute,relative,resolve,sep} from 'node:path';
import {spawn} from 'node:child_process';
import type pg from 'pg';
import {z} from 'zod';
import {DomainError} from './errors';
import type {ShardedManifest} from './shards';
const hash=z.string().regex(/^[a-f0-9]{64}$/),id=z.string().min(1).max(500);
const receiptSchema=z.object({publication:id,artifact:z.string().min(1).max(1500),artifact_sha256:hash}).strict();
const pinSchema=z.object({path:z.string().min(1).max(1500),sha256:hash}).strict();
export type IngestionArtifactReceipt=z.infer<typeof receiptSchema>;
export type IngestionFilePin=z.infer<typeof pinSchema>;
export interface IngestionProvenanceInput {
 original_raw_receipt:IngestionArtifactReceipt;
 raster_stage_receipt:IngestionFilePin|null;
 technical_evaluation_receipt:IngestionFilePin;
 receipt_directory:string;
}
const CLI='scripts/technical-ingestion-provenance.py';
const RUNTIME_FILES=['src/domain/ingestion-provenance.ts','src/domain/ingestion-update.ts','src/domain/ingestion-coverage.ts','src/domain/shard-writer.ts','src/domain/shards.ts','src/domain/publication.ts','src/domain/visibility.ts','src/worker/ingestion.ts','src/worker/main.ts','src/worker/jobs.ts','scripts/technical-ingestion-provenance.py','pipeline/technical_provenance.py','pipeline/validate_artifact.py','pipeline/distribution.py','pipeline/release_check.py','pipeline/requirements.txt','package.json','package-lock.json'];
const MAX_RECEIPT=64*1024*1024;
// Freeze the source bytes observed when this module is loaded, not only when a job starts.
const LOADED_RUNTIME_PINS=Object.fromEntries(RUNTIME_FILES.map(path=>[path,createHash('sha256').update(readFileSync(resolve(path))).digest('hex')]));
const digest=(value:string|Buffer)=>createHash('sha256').update(value).digest('hex');
const fail=(message:string):never=>{throw new DomainError(409,'INGESTION_PROVENANCE_MISMATCH',message);};
/** The identity envelopes contain strings, booleans, null and bounded integer counts, not numeric corpus payloads. */
export function canonicalProvenance(value:unknown):string {
 if(value===null||typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
 if(typeof value==='number'&&Number.isSafeInteger(value))return JSON.stringify(value);
 if(Array.isArray(value))return'['+value.map(canonicalProvenance).join(',')+']';
 if(value&&typeof value==='object')return'{'+Object.entries(value).sort(([a],[b])=>Buffer.compare(Buffer.from(a),Buffer.from(b))).map(([k,v])=>JSON.stringify(k)+':'+canonicalProvenance(v)).join(',')+'}';
 return fail('Valor não canônico no envelope de proveniência.');
}
export const provenanceDigest=(value:unknown)=>digest(canonicalProvenance(value));
async function fileHash(path:string){const h=createHash('sha256');for await(const chunk of createReadStream(path))h.update(chunk);return h.digest('hex');}
async function located(path:string,allowed:'var'|'bundles'|'proof'|'runtime'){
 if(isAbsolute(path)||path.split(/[\\/]/).includes('..'))return fail('Caminho de proveniência deve ser relativo e não pode escapar do repositório.');
 const root=await realpath(process.cwd()),actual=await realpath(resolve(path));
 const prefixes=allowed==='var'?['var']:allowed==='bundles'?['data/bundles']:allowed==='proof'?['docs/evidence','data/manifests']:['src','scripts','pipeline'];
 if(!(allowed==='runtime'&&['package.json','package-lock.json'].some(p=>actual===resolve(root,p)))&&!prefixes.some(p=>actual.startsWith(resolve(root,p)+sep)))return fail('Arquivo fora do armazenamento permitido para sua função.');
 return actual;
}
async function pinned(pin:IngestionFilePin,allowed:'var'|'bundles'|'proof'|'runtime',json=false){
 const value=pinSchema.parse(pin),path=await located(value.path,allowed),info=await stat(path);
 if(!info.isFile()||(json&&info.size>MAX_RECEIPT)||await fileHash(path)!==value.sha256)return fail('Checksum, tamanho ou tipo de arquivo de proveniência diverge.');
 if(!json)return path;
 return JSON.parse(await readFile(path,'utf8')) as Record<string,unknown>;
}
function object(value:unknown):Record<string,unknown>{if(!value||typeof value!=='object'||Array.isArray(value))return fail('Objeto de proveniência inválido.');return value as Record<string,unknown>;}
function exactIds(value:unknown){const ids=z.array(id).max(10000).parse(value);if(new Set(ids).size!==ids.length)return fail('IDs repetidos no denominador da consulta SQL.');return [...ids].sort();}
function equal(a:unknown,b:unknown,label:string){if(canonicalProvenance(a)!==canonicalProvenance(b))fail(label);}
function internalReceipt(value:Record<string,unknown>){const {receipt_sha256,...content}=value;if(!hash.safeParse(receipt_sha256).success||provenanceDigest(content)!==receipt_sha256)fail('Digest interno do recibo diverge dos dados.');}
async function immutableOutput(path:string,content:string){
 await mkdir(dirname(path),{recursive:true});const parent=await realpath(dirname(path));if(!parent.startsWith((await realpath(resolve('var')))+sep))fail('Saída de recibo deve ficar em var/.');
 const temporary=path+'.tmp-'+randomUUID(),file=await open(temporary,'wx',0o600);try{await file.writeFile(content);await file.sync();}finally{await file.close();}
 try{await link(temporary,path);}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;if(await fileHash(path)!==digest(content))fail('Colisão de recibo imutável com bytes diferentes.');}finally{await unlink(temporary).catch(()=>{});}
}
async function runTechnical(args:string[],signal?:AbortSignal){
 signal?.throwIfAborted();
 const python=process.env.PIPELINE_PYTHON||process.env.PYTHON_BIN||(existsSync('var/venv-pipeline/bin/python')?resolve('var/venv-pipeline/bin/python'):'python3');
 await new Promise<void>((accept,reject)=>{
  const child=spawn(python,[CLI,...args],{stdio:['ignore','ignore','pipe']});let stderr='',aborted=false,timedOut=false,killer:NodeJS.Timeout|undefined;
  const terminate=()=>{if(child.exitCode!==null)return;child.kill('SIGTERM');if(!killer){killer=setTimeout(()=>child.kill('SIGKILL'),5000);killer.unref();}};
  const onAbort=()=>{aborted=true;terminate();};signal?.addEventListener('abort',onAbort,{once:true});if(signal?.aborted)onAbort();
  const timeout=setTimeout(()=>{timedOut=true;terminate();},Math.max(1000,Number(process.env.JOB_TIMEOUT_SECONDS||7200)*1000));timeout.unref();
  const cleanup=()=>{clearTimeout(timeout);if(killer)clearTimeout(killer);signal?.removeEventListener('abort',onAbort);};
  child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-16000);});
  child.once('error',error=>{cleanup();reject(error);});
  // Cancellation waits for close; an unresponsive child still receives SIGKILL.
  child.once('close',code=>{cleanup();if(aborted)reject(signal?.reason??new Error('Ingestion aborted'));else if(code===0&&!timedOut)accept();else reject(new DomainError(409,'TECHNICAL_PROVENANCE_REPLAY_FAILED','Reavaliação técnica RAW/provas recusada: '+stderr.slice(-1200)));});
 });
}
export async function evaluateIngestionProvenance(input:{effective_raw_receipt:IngestionArtifactReceipt;job_scope:{base_publication:string;base_publication_sha256:string;base_artifact_sha256:string;target_source_ids:string[];context_source_ids:string[]};receipt_directory:string;signal?:AbortSignal}):Promise<IngestionFilePin>{
 const receipt=receiptSchema.parse(input.effective_raw_receipt),scope={...input.job_scope,target_source_ids:exactIds(input.job_scope.target_source_ids),context_source_ids:exactIds(input.job_scope.context_source_ids)};
 hash.parse(scope.base_publication_sha256);hash.parse(scope.base_artifact_sha256);
 if(isAbsolute(input.receipt_directory)||input.receipt_directory.split(/[\\/]/).includes('..')||!resolve(input.receipt_directory).startsWith(resolve('var')+sep))fail('Diretório dos recibos deve ficar em var/.');
 const cliSha=await fileHash(await located(CLI,'runtime')),key=provenanceDigest({receipt,scope,cliSha}),directory=resolve(input.receipt_directory),rp=resolve(directory,'raw-'+key+'.json'),sp=resolve(directory,'scope-'+key+'.json'),out=resolve(directory,'evaluation-'+key+'.json');
 await immutableOutput(rp,canonicalProvenance(receipt));await immutableOutput(sp,canonicalProvenance(scope));
 await runTechnical(['evaluate','--storage-root',process.cwd(),'--proof-root',process.cwd(),'--raw-receipt',rp,'--raw-receipt-sha256',await fileHash(rp),'--job-scope',sp,'--job-scope-sha256',await fileHash(sp),'--output-receipt',out],input.signal);
 if(await fileHash(await located(CLI,'runtime'))!==cliSha)fail('CLI mudou durante avaliação.');return{path:relative(process.cwd(),out),sha256:await fileHash(out)};
}
type Base={id:string;sha256:string};
async function assertBase(client:pg.PoolClient,base:Base){
 hash.parse(base.sha256);const row=(await client.query("SELECT p.sha256 FROM publications p JOIN publication_visibility v ON v.publication_id=p.id AND v.status='published' WHERE p.id=$1",[base.id])).rows[0];
 if(!row||row.sha256!==base.sha256)fail('Base SQL publicada diverge da identidade fixada.');
}
/** Exact JSONB text is streamed into the capture: large integer/decimal values never pass through JS numbers. */
export async function captureTechnicalBaseRecords(client:pg.PoolClient,input:{base_publication:string;base_publication_sha256:string;queried_item_ids:string[];output_file:string}){
 const base={id:input.base_publication,sha256:input.base_publication_sha256};await assertBase(client,base);const wanted=exactIds(input.queried_item_ids);
 if(isAbsolute(input.output_file)||input.output_file.split(/[\\/]/).includes('..')||!resolve(input.output_file).startsWith(resolve('var')+sep))fail('Captura SQL deve ficar em var/.');
 const filename=resolve(input.output_file);await mkdir(dirname(filename),{recursive:true});const physicalParent=await realpath(dirname(filename));if(!physicalParent.startsWith((await realpath(resolve('var')))+sep))fail('Diretório de captura SQL fora de var/.');
 const temporary=filename+'.tmp-'+randomUUID(),file=await open(temporary,'wx',0o600),streamHash=createHash('sha256');let bytes=0,first=true;
 const observed=new Map<string,{source_id:string;text_sha256:string}>();
 const write=async(text:string)=>{bytes+=Buffer.byteLength(text);if(bytes>MAX_RECEIPT)fail('Captura SQL excede o limite explícito de 64MiB.');streamHash.update(text);await file.writeFile(text);};
 try{
  await write('{"format":"technical-base-record-capture-v1","base_publication":'+JSON.stringify(base.id)+',"base_publication_sha256":'+JSON.stringify(base.sha256)+',"queried_item_ids":'+JSON.stringify(wanted)+',"records":[');
  for(let start=0;start<wanted.length;start+=8){const rows=(await client.query('SELECT id,source_id,text,payload::text AS payload_text FROM items WHERE publication_id=$1 AND id=ANY($2::text[]) ORDER BY id',[base.id,wanted.slice(start,start+8)])).rows;
   for(const row of rows){if(observed.has(row.id))fail('ID SQL duplicado durante captura.');observed.set(row.id,{source_id:row.source_id,text_sha256:digest(row.text)});await write((first?'':',')+row.payload_text);first=false;}
  }
  await write(']}');await file.sync();
 }catch(error){await unlink(temporary).catch(()=>{});throw error;}finally{await file.close();}
 const sha256=streamHash.digest('hex');if(await fileHash(temporary)!==sha256){await unlink(temporary);fail('Escrita parcial na captura SQL.');}try{await link(temporary,filename);}catch(error){if((error as NodeJS.ErrnoException).code!=='EEXIST')throw error;if(await fileHash(filename)!==sha256)fail('Captura anterior tem conteúdo diferente para os mesmos inputs SQL.');}finally{await unlink(temporary).catch(()=>{});}
 await assertBase(client,base);return{pin:{path:relative(process.cwd(),filename),sha256},queried_item_ids:wanted,observed};
}
function eventWanted(events:unknown[]){return exactIds(events.flatMap(value=>{const event=object(value);return event.same_id===true?[event.item_id]:z.array(z.record(z.string(),z.unknown())).parse(event.pairs).map(pair=>pair.superseded_item_id);}));}
function verifyEffects(events:unknown[],base:Base,target:string[],observed:Map<string,{source_id:string;text_sha256:string}>){
 for(const value of events){const event=object(value);if(!target.includes(String(event.source_id))||event.type!=='extraction_correction'||event.actor_type!=='automated'||event.previous_publications_immutable!==true||event.official_curriculum_edition_changed!==false)fail('Evento técnico fora da fonte alvo ou com promoção indevida.');
  equal(event.effect_base_publication,base.id,'Evento não pertence à base SQL.');equal(event.effect_base_publication_sha256,base.sha256,'SHA do efeito técnico diverge da base SQL.');
  if(event.same_id===true){const old=observed.get(String(event.item_id));if(old&&old.source_id!==event.source_id)fail('Correção same-ID aponta para outra Source.');let expected:string;
   if(!old)expected='documented_historical_text_correction';else if(old.text_sha256===event.before_text_sha256)expected='corrects_text_in_pinned_base';else if(old.text_sha256===event.after_text_sha256)expected='already_corrected_in_pinned_base';else return fail('Texto atual SQL não coincide com before/after da prova técnica.');
   equal(event.observed_effect,expected,'Efeito same-ID não corresponde ao registro SQL.');equal(event.current_base_before_text_sha256,old?.text_sha256??null,'Texto antes da correção diverge da captura SQL.');
  }else for(const rawPair of z.array(z.unknown()).parse(event.pairs)){const pair=object(rawPair),old=observed.get(String(pair.superseded_item_id));if(old&&old.source_id!==event.source_id)fail('Supersessão aponta para outra fonte na base SQL.');equal(pair.old_item_exists_in_pinned_base,Boolean(old),'Presença do ID antigo foi declarada incorretamente.');equal(pair.observed_effect,old?'supersedes_item_from_pinned_base':'documented_historical_extraction_correction','Remoção atual foi confundida com correção histórica.');}
 }
}
async function runtimePins(){const files:Record<string,string>={};for(const path of RUNTIME_FILES)files[path]=await fileHash(await located(path,'runtime'));equal(files,LOADED_RUNTIME_PINS,'Código em disco diverge dos bytes observados no carregamento do módulo; reinicie o processo com a versão correta.');return files;}
export type PreparedIngestionProvenance=Awaited<ReturnType<typeof prepareIngestionProvenance>>;
/** Called inside the compositor's pinned repeatable-read transaction. The CLI replays RAW/proofs; SQL authority stays here. */
export async function prepareIngestionProvenance(client:pg.PoolClient,input:{base:Base;target_source_ids:string[];raw:ShardedManifest;effective_raw_receipt:IngestionArtifactReceipt;provenance:IngestionProvenanceInput;signal?:AbortSignal}){
 input.signal?.throwIfAborted();
 const {base,raw}=input,target=exactIds(input.target_source_ids),effective=receiptSchema.parse(input.effective_raw_receipt),original=receiptSchema.parse(input.provenance.original_raw_receipt);
 const before=await runtimePins(),files:Record<string,string>={...before},evaluationPin=pinSchema.parse(input.provenance.technical_evaluation_receipt);
 const evaluation=object(await pinned(evaluationPin,'var',true));internalReceipt(evaluation);if(evaluation.format!=='technical-source-update-evaluation-v1')fail('Formato de avaliação técnica inválido.');
 const scope={base_publication:base.id,base_publication_sha256:base.sha256,base_artifact_sha256:raw.base_artifact_sha256,target_source_ids:target,context_source_ids:raw.context_source_ids};
 equal(evaluation.raw_receipt,effective,'Avaliação técnica não corresponde ao RAW efetivo.');equal(evaluation.job_scope,scope,'Avaliação não corresponde à base/contexto/alvos do compositor.');
 const cli=object(evaluation.cli);if(cli.path!==CLI||cli.sha256!==await fileHash(await located(CLI,'runtime')))fail('CLI técnico do recibo difere do executável atual.');files[CLI]=String(cli.sha256);
 const producer=object(evaluation.producer_fingerprint);if(producer.producer_file_sha256!==await fileHash(await located('pipeline/technical_provenance.py','runtime')))fail('Produtor técnico mudou após a avaliação.');files['pipeline/technical_provenance.py']=String(producer.producer_file_sha256);
 const assessed=object(evaluation.evaluation),wanted=exactIds(evaluation.wanted_base_item_ids);equal(wanted,eventWanted(z.array(z.unknown()).parse(assessed.events)),'Denominador de IDs da avaliação não corresponde aos eventos.');
 equal(wanted,exactIds([...z.array(id).parse(assessed.superseded_ids_absent),...z.array(id).parse(assessed.same_id_text_corrections_verified)]),'IDs procurados na base divergem da avaliação.');
 for(const [path,sha256] of Object.entries(object(assessed.proof_pins))){hash.parse(sha256);await pinned({path,sha256:String(sha256)},'proof');files[path]=String(sha256);}
 const directory=input.provenance.receipt_directory;if(isAbsolute(directory)||directory.split(/[\\/]/).includes('..')||!resolve(directory).startsWith(resolve('var')+sep))fail('Diretório dos recibos deve ficar em var/.');
 const capture=await captureTechnicalBaseRecords(client,{base_publication:base.id,base_publication_sha256:base.sha256,queried_item_ids:wanted,output_file:relative(process.cwd(),resolve(directory,'base-records-'+evaluationPin.sha256+'.json'))});
 const identityPath=relative(process.cwd(),resolve(directory,'identity-'+digest(evaluationPin.sha256+capture.pin.sha256+String(cli.sha256))+'.json'));
 await runTechnical(['contextualize','--storage-root',process.cwd(),'--proof-root',process.cwd(),'--evaluation-receipt',evaluationPin.path,'--evaluation-receipt-sha256',evaluationPin.sha256,'--base-record-capture',capture.pin.path,'--base-record-capture-sha256',capture.pin.sha256,'--output-receipt',identityPath],input.signal);
 input.signal?.throwIfAborted();
 const identityPin={path:identityPath,sha256:await fileHash(await located(identityPath,'var'))},identity=object(await pinned(identityPin,'var',true));internalReceipt(identity);
 if(identity.format!=='technical-source-update-identity-v1'||identity.sql_authority_asserted_by_cli!==false)fail('Formato ou autoridade do recibo técnico incorretos.');
 equal(identity.raw_receipt,effective,'RAW da identidade técnica diverge.');equal(identity.job_scope,scope,'Escopo da identidade técnica diverge.');equal(identity.evaluation_receipt_file_sha256,evaluationPin.sha256,'Avaliação não foi fixada na identidade.');equal(identity.base_record_capture_file_sha256,capture.pin.sha256,'Captura SQL não foi fixada na identidade.');equal(identity.producer_fingerprint,producer,'Produtor diverge entre fases.');
 const payload=object(identity.identity_payload),events=z.array(z.unknown()).parse(payload.events);equal(payload.base_publication,base,'Base da identidade técnica diverge do SQL.');equal(payload.target_source_ids,target,'Alvos da identidade técnica divergem.');equal(identity.identity_payload_sha256,provenanceDigest(payload),'Digest do payload de identidade diverge.');equal(identity.technical_events_sha256,identity.identity_payload_sha256,'Eventos e payload têm identidades diferentes.');verifyEffects(events,base,target,capture.observed);
 const amTargets=target.filter(sid=>['am-rca-ei','am-rca-ef-ai','am-rca-ef-af','am-rca-em'].includes(sid));
 if(amTargets.length&&!input.provenance.raster_stage_receipt)fail('Alvos AM exigem recibo do estágio raster.');
 let raster:Record<string,unknown>|null=null;
 if(input.provenance.raster_stage_receipt){const pin=pinSchema.parse(input.provenance.raster_stage_receipt),stage=object(await pinned(pin,'var',true)),augmentation=object(stage.augmentation_receipt);internalReceipt(augmentation);if(augmentation.format!=='primary-raster-reference-augmentation-receipt-v1'||augmentation.source_body_verified!==false||augmentation.ready_promoted!==false||augmentation.promotion_performed!==false)fail('Formato/escopo da etapa raster inválido.');equal(stage.original_raw_receipt,original,'Recibo raster perdeu o RAW original.');equal(stage.effective_raw_receipt,effective,'Recibo raster não corresponde ao RAW efetivo.');equal(augmentation.base_publication,base.id,'Base do raster diverge.');equal(augmentation.base_publication_sha256,base.sha256,'SHA da base do raster diverge.');equal(augmentation.base_artifact_sha256,raw.base_artifact_sha256,'Contexto BR do raster diverge.');equal(augmentation.target_source_ids,target,'Alvos raster divergem.');equal(augmentation.context_source_ids,raw.context_source_ids,'Contexto BR raster diverge.');
  const rasterProducer=object(augmentation.producer),producerFiles=object(rasterProducer.files);equal(Object.keys(producerFiles).sort(),['raster_augmentation.py','raster_review_scoped.py','raster_review.py','distribution.py','validate_artifact.py'].sort(),'Inventário dos módulos raster diverge.');equal(rasterProducer.sha256,provenanceDigest({revision:rasterProducer.revision,files:producerFiles}),'Fingerprint raster diverge.');for(const [name,sha256] of Object.entries(producerFiles)){const path='pipeline/'+name;await pinned({path,sha256:String(sha256)},'runtime');files[path]=String(sha256);}
  const rasterCli={path:'scripts/augment-ingestion-raw.py',sha256:await fileHash(await located('scripts/augment-ingestion-raw.py','runtime'))};files[rasterCli.path]=rasterCli.sha256;
  if(!amTargets.length&&augmentation.bypass_exact!==true)fail('Fontes não AM devem usar bypass raster exato.');
  if(augmentation.bypass_exact===true)equal(original,effective,'Bypass raster alterou caminho/ID/SHA do original.');
  raster={receipt_path:pin.path,receipt_file_sha256:pin.sha256,internal_receipt_sha256:augmentation.receipt_sha256,producer_sha256:rasterProducer.sha256,cli:rasterCli};files[pin.path]=pin.sha256;
 }else equal(original,effective,'RAW alterado sem recibo explícito de augmentação.');
 const originalPath=await located(original.artifact,'bundles');if(await fileHash(originalPath)!==original.artifact_sha256)fail('RAW original foi alterado.');files[original.artifact]=original.artifact_sha256;files[effective.artifact]=effective.artifact_sha256;files[evaluationPin.path]=evaluationPin.sha256;files[identityPin.path]=identityPin.sha256;files[capture.pin.path]=capture.pin.sha256;
 const orchestration={format:'source-update-orchestration-v1',original_raw_receipt:original,effective_raw_receipt:effective,raster_stage:raster,technical_stage:{required:events.length>0,identity_payload_sha256:identity.identity_payload_sha256,receipt_path:identityPin.path,receipt_file_sha256:identityPin.sha256,producer_fingerprint_sha256:producer.sha256,evaluate_cli:cli,contextualize_cli:cli,evaluation_receipt:evaluationPin,base_record_capture:capture.pin,sql_authority:'domain_postgresql_repeatable_read'},runtime_files:before};
 const prepared={orchestration_provenance:orchestration,orchestration_sha256:provenanceDigest(orchestration),technical_events_sha256:String(identity.technical_events_sha256),technical_events:events,technical_identity_payload:payload,files};await assertIngestionProvenanceUnchanged(prepared);input.signal?.throwIfAborted();return prepared;
}
export async function assertIngestionProvenanceUnchanged(proof:{files:Record<string,string>}){for(const [path,sha256] of Object.entries(proof.files)){if(await fileHash(resolve(path))!==sha256)fail('Código/prova/recibo mudou durante a composição: '+path);}}
