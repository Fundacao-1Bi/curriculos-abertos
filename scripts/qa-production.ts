/** Clean, isolated Compose installation and persistence verification. Never touches the main project. */
import assert from 'node:assert/strict';
import { randomBytes,randomUUID } from 'node:crypto';
import { existsSync,mkdirSync,readFileSync,writeFileSync } from 'node:fs';
import { resolve,relative,isAbsolute } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import type { Learning } from '../src/shared/contracts';
import { sourceTreeHash } from './release-check';
import {artifactFootprint,productionBudget,measureDatabaseFootprint,assertCapacityAvailable,type ArtifactFootprint,type DatabaseFootprint,type CapacityBudget} from './qa-capacity';
import {withQaRun,currentQaRun} from './qa-executor';
import { openAuditArtifact,inspectAuditArtifact,latestAuditPublication,sampleBatches,matchSample,type SampleReference } from './audit-artifact';
export interface CleanState {project:string;env_file:string;base_url:string;database_port:number;image:string;image_id:string;publication:string;snapshot:Record<string,unknown>;created_at:string;source_tree_sha256:string;diagnostic_only?:boolean;diagnostic_label?:string;capacity?:{artifact:ArtifactFootprint;production_budget:CapacityBudget;database?:DatabaseFootprint};artifact?:{publication:string;format:string;manifest_sha256:string;items:number;relations:number;sources:number;parts_verified:number;schema_verified:boolean;schema_path:string|null;schema_sha256:string|null};}
export const cleanStatePath='var/qa-clean-state.json';
export function run(command:string,args:string[],options:{input?:string|Buffer;env?:Record<string,string|undefined>;binary?:boolean;timeout?:number;supervised?:boolean;ownedContainerName?:string;ownedDatabaseOperation?:{container_id:string;project:string;database:string;application_name:string}}={}) {
 const supervised=options.supervised||options.ownedContainerName||(command==='bash'&&args.some(arg=>['scripts/ops-backup.sh','scripts/ops-restore.sh'].includes(arg)))||args.includes('scripts/ops-image-verify.ts');
 if(supervised)return currentQaRun().commandSync(command,args,{...options,env:{...process.env,...options.env}});
 const result=spawnSync(command,args,{cwd:process.cwd(),env:{...process.env,...options.env},input:options.input,encoding:options.binary?undefined:'utf8',maxBuffer:32*1024*1024,timeout:options.timeout||300_000});
 if(result.status!==0){const raw=String(result.stderr||result.stdout||result.error?.message||'sem diagnóstico');throw new Error(`${command} ${args.slice(0,2).join(' ')}: exit ${result.status}; ${raw.slice(-5000)}`);}
 return options.binary?Buffer.from(result.stdout):String(result.stdout);
}
export function verifyRuntimeImage(image:string){
 const qa=currentQaRun(),name='curriculos-qa-command-'+randomUUID();qa.checkpoint();
 const probeResource=qa.registerResource({kind:'container',id:name,owned:true,disposition:'disposable',metadata:{purpose:'read_only_image_probe',image}});
 let verificationError:unknown;
 try{run(process.execPath,['--import','tsx','scripts/ops-image-verify.ts','--image',image,'--probe-name',name,'--qa-run-id',qa.record.id],{ownedContainerName:name});}catch(error){verificationError=error;}
 // The shipped verifier uses --rm. Confirm absence; never claim cleanup after an
 // unchecked best-effort docker rm from its failure handler.
 const probe=spawnSync('docker',['inspect',name,'--format','{{.Id}}'],{encoding:'utf8',timeout:15000,maxBuffer:1024*1024});
 if(probe.status!==0&&/No such (object|container)/i.test(probe.stderr)){qa.recordReport('runtime-image-probe-absence',{resource_id:probeResource,absence_verified:true,observed_at:new Date().toISOString(),method:'docker inspect returned No such object/container; no delete issued by caller'});qa.markResource(probeResource,'cleaned');}else{qa.markResource(probeResource,'retained');if(!verificationError)verificationError=new Error('Image verification probe still exists or Docker inspection failed; resource retained for reconciliation.');}
 if(verificationError)throw verificationError;
 const report=JSON.parse(readFileSync('docs/evidence/image-files-verification.json','utf8')) as {passed:boolean;image:string;image_id:string;image_files:{source_tree_sha256:string;filesystem_free_bytes:number}};
 assert.equal(report.passed,true);assert.equal(report.image,image);assert.equal(report.image_files.source_tree_sha256,sourceTreeHash());assert.match(report.image_id,/^sha256:[a-f0-9]{64}$/);assert.ok(Number.isSafeInteger(report.image_files.filesystem_free_bytes));qa.recordReport('runtime-image-verification',report);return report;
}
export function resolveQaComposeOverride(configured:string|undefined):string{assert.ok(configured,'Override Compose isolado é obrigatório para QA');const path=resolve(configured),varRoot=resolve('var'),relativePath=relative(varRoot,path);assert.ok(relativePath&&!relativePath.startsWith('..')&&!isAbsolute(relativePath),'Override Compose QA precisa permanecer dentro de var/');assert.ok(existsSync(path),'Override Compose QA não existe.');return path;}
export function isolatedEnvironment(state:Pick<CleanState,'project'|'env_file'>):Record<string,string>{assert.match(state.project,/^curriculos-abertos-clean-[a-z0-9-]+$/,'Projeto QA inválido');assert.match(state.env_file,/^var\/qa-clean-[a-zA-Z0-9-]+\.env$/,'Arquivo de ambiente QA fora do isolamento');const values:Record<string,string>={};for(const line of readFileSync(state.env_file,'utf8').split('\n')){const match=line.match(/^([A-Z][A-Z0-9_]*)=(.*)$/);if(match)values[match[1]]=match[2];}assert.equal(values.POSTGRES_USER,'curriculos_qa');assert.equal(values.POSTGRES_DB,'curriculos_qa');if(!values.POSTGRES_PASSWORD||!values.BETTER_AUTH_SECRET)throw new Error('Segredos QA locais ausentes.');const override=resolveQaComposeOverride(values.QA_COMPOSE_OVERRIDE);values.DATABASE_VOLUME=state.project+'_database';values.DATABASE_VOLUME_EXTERNAL='false';values.DATA_BUNDLE='';values.COMPOSE_FILE=`${resolve('compose.yaml')}:${override}`;values.COMPOSE_PROFILES='';values.STORAGE_VOLUME=state.project+'_storage';values.COMPOSE_PROJECT_NAME=state.project;values.COMPOSE_ENV_FILES=state.env_file;values.DATABASE_URL=`postgresql://curriculos_qa:${values.POSTGRES_PASSWORD}@db:5432/curriculos_qa`;return values;}
export function compose(state:Pick<CleanState,'project'|'env_file'>,args:string[],options:Parameters<typeof run>[2]={}){
 const qa=currentQaRun(),supervised=['up','run','restart','start'].includes(args[0]);if(supervised)qa.checkpoint();
 let ownedContainerName:string|undefined;
 if(args[0]==='run'){
  assert.ok(args.includes('--rm'),'QA one-off commands require --rm');assert.ok(!args.includes('--name'),'QA one-off name is assigned by the executor');
  ownedContainerName='curriculos-qa-command-'+randomUUID();qa.registerResource({kind:'container',id:ownedContainerName,project:state.project,owned:true,disposition:'disposable',metadata:{purpose:'supervised_compose_run',qa_run_id:qa.record.id}});
  args=['run','--name',ownedContainerName,'--label','org.curriculos-abertos.qa-run='+qa.record.id,...args.slice(1)];
 }
 let failure:unknown;
 try{return run('docker',['compose','--env-file',state.env_file,'-p',state.project,...args],{...options,supervised,ownedContainerName,env:{...options.env,...isolatedEnvironment(state)}});}catch(error){failure=error;throw error;}
 finally{if(ownedContainerName){const inspected=spawnSync('docker',['inspect',ownedContainerName,'--format','{{.Id}}'],{encoding:'utf8',timeout:15000,maxBuffer:1024*1024});if(inspected.status!==0&&/No such (object|container)/i.test(inspected.stderr||''))qa.markResource(ownedContainerName,'cleaned',{absence_verified:true});else{qa.markResource(ownedContainerName,'retained',{absence_verified:false});if(!failure)throw Error('Owned one-off container remains or Docker inspection failed; retained for reconciliation');}}}
}
export function sql(state:Pick<CleanState,'project'|'env_file'>,statement:string,database='curriculos_qa'){
 return String(compose(state,['exec','-T','db','psql','-U','curriculos_qa','-d',database,'-At','-v','ON_ERROR_STOP=1','-c',statement])).trim();
}
export const snapshotSql=`SELECT json_build_object('publication',(SELECT publication_id FROM current_publication WHERE singleton=true),'publications',(SELECT count(*) FROM publications),'items',(SELECT count(*) FROM items),'sources',(SELECT count(*) FROM sources),'relations',(SELECT count(*) FROM relations),'admins',(SELECT count(*) FROM admin_roles),'publication_metadata_digest',(SELECT md5(string_agg(id||':'||sha256||':'||storage_format,',' ORDER BY id)) FROM publications),'items_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM items),'source_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM sources),'relations_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM relations));`;
export async function waitReady(base:string){let last='';for(let n=0;n<60;n++){try{const r=await fetch(base+'/api/ready',{signal:AbortSignal.timeout(5000)});if(r.status===200)return await r.json() as Record<string,unknown>;last=String(r.status);}catch(e){last=e instanceof Error?e.message:String(e);}await new Promise(r=>setTimeout(r,1000));}throw new Error(`Readiness não atingida: ${last}`);}
export function loadCleanState(){const state=JSON.parse(readFileSync(cleanStatePath,'utf8')) as CleanState;if(!/^curriculos-abertos-clean-[a-z0-9-]+$/.test(state.project)||!/^var\/qa-clean-[a-zA-Z0-9-]+\.env$/.test(state.env_file))throw new Error('Estado de projeto QA fora do isolamento esperado.');return state;}
async function main(){const qa=currentQaRun();const started_at=new Date().toISOString(),diagnosticOnly=process.env.QA_DIAGNOSTIC_ONLY==='true',diagnosticLabel=diagnosticOnly?(process.env.QA_DIAGNOSTIC_LABEL||'Incomplete BASE diagnostic; not national acceptance'):undefined;const checks:{name:string;passed:boolean;detail?:unknown}[]=[];let state:CleanState|undefined;
 try{
 const token=new Date().toISOString().replace(/\D/g,'').slice(0,14)+'-'+randomBytes(3).toString('hex');
 const project=`curriculos-abertos-clean-${token}`,env_file=`var/qa-clean-${token}.env`,port=Number(process.env.QA_PORT||3001),database_port=Number(process.env.QA_DATABASE_PORT||55438),image=`curriculos-abertos:${process.env.RELEASE_TAG||'local'}`;
 const compose_override=process.env.QA_COMPOSE_OVERRIDE?resolveQaComposeOverride(process.env.QA_COMPOSE_OVERRIDE):resolve(`var/qa-clean-${token}.compose.yaml`);
 assert.ok(Number.isInteger(port)&&port>0&&port<=65535&&Number.isInteger(database_port)&&database_port>0&&database_port<=65535&&port!==3000&&database_port!==55437,'QA deve usar portas diferentes da distribuição principal');

 const publication=process.env.QA_PUBLICATION||await latestAuditPublication();const artifact=await openAuditArtifact(publication),verified=await inspectAuditArtifact(artifact);assert.ok(verified.passed,JSON.stringify(verified.errors));assert.equal(verified.schema_verified,true,'Distribuição precisa incluir JSON Schema declarado e verificado');
 const pinnedArtifact=relative(process.cwd(),artifact.path);assert.ok(pinnedArtifact.startsWith('data/bundles/')&&!pinnedArtifact.split('/').includes('..'),'Artefato QA deve estar no diretório de distribuição');
 const footprint=await artifactFootprint(artifact),capacity=productionBudget(footprint);const hostStats=(await import('node:fs')).statfsSync('.');
 qa.reserve(capacity);const verifiedImage=verifyRuntimeImage(image);checks.push({name:'imagem real verificada antes de criar ambiente ou volumes QA',passed:true,detail:{image,image_id:verifiedImage.image_id,source_tree_sha256:verifiedImage.image_files.source_tree_sha256}});
 const available=assertCapacityAvailable(capacity,{host:hostStats.bavail*hostStats.bsize,docker:verifiedImage.image_files.filesystem_free_bytes});checks.push({name:'orçamento de instalação calculado pelo artefato antes de criar ambiente',passed:true,detail:{footprint,capacity,available}});
 qa.setInputs({project,publication,manifest_sha256:verified.manifest_sha256,image_id:verifiedImage.image_id,source_tree_sha256:sourceTreeHash()});
 const projectResource=qa.registerResource({kind:'compose-project',id:project,project,owned:true,disposition:'retain'});const volumeResources=[project+'_database',project+'_storage'].map(id=>qa.registerResource({kind:'volume',id,project,owned:true,disposition:'retain'}));
 const envResource=qa.registerResource({kind:'file',id:env_file,path:env_file,project,owned:true,disposition:'retain'});
 const overrideResource=qa.registerResource({kind:'file',id:compose_override,path:compose_override,project,owned:!process.env.QA_COMPOSE_OVERRIDE,disposition:'retain'});
 mkdirSync('var',{recursive:true});if(!process.env.QA_COMPOSE_OVERRIDE){qa.checkpoint();writeFileSync(compose_override,'services:\n  worker:\n    volumes:\n      - storage:/app/var\n      - ./data:/app/data:ro\n',{mode:0o600,flag:'wx'});qa.markResource(overrideResource,'created');}else qa.markResource(overrideResource,'retained');
 mkdirSync('var',{recursive:true});const password=randomBytes(32).toString('hex');const secret=randomBytes(48).toString('hex');
 const base_url=`http://localhost:${port}`;
 const configuredDb=existsSync('.env')?readFileSync('.env','utf8').match(/^POSTGRES_IMAGE=(.+)$/m)?.[1].trim():undefined;const postgresImage=process.env.QA_POSTGRES_IMAGE||process.env.POSTGRES_IMAGE||configuredDb||'postgres:17.11-bookworm';assert.match(postgresImage,/^[a-zA-Z0-9_./:@-]+$/,'Referência de imagem PostgreSQL inválida');
 const env=`DATABASE_VOLUME=${project}_database\nDATABASE_VOLUME_EXTERNAL=false\nDATA_BUNDLE=\nSTORAGE_VOLUME=${project}_storage\nPOSTGRES_IMAGE=${postgresImage}\nPOSTGRES_USER=curriculos_qa\nPOSTGRES_DB=curriculos_qa\nPOSTGRES_PASSWORD=${password}\nBETTER_AUTH_SECRET=${secret}\nPUBLIC_URL=${base_url}\nPORT=${port}\nDATABASE_PORT=${database_port}\nRELEASE_TAG=${process.env.RELEASE_TAG||'local'}\nQA_COMPOSE_OVERRIDE=${compose_override}\nPUBLIC_RATE_LIMIT=1000\nMCP_ALLOWED_HOSTS=localhost:${port},127.0.0.1:${port}\nSOURCE_CHECK_ENABLED=false\n`;
 qa.checkpoint();writeFileSync(env_file,env,{mode:0o600,flag:'wx'});qa.markResource(envResource,'created');
 const image_id=verifiedImage.image_id;
 state={project,env_file,base_url,database_port,image,image_id,publication:'',snapshot:{},created_at:new Date().toISOString(),source_tree_sha256:sourceTreeHash(),diagnostic_only:diagnosticOnly,...(diagnosticLabel?{diagnostic_label:diagnosticLabel}:{}),capacity:{artifact:footprint,production_budget:capacity}};
 const prefix=project+'_';const volumes=String(run('docker',['volume','ls','--format','{{.Name}}'])).split('\n');assert.ok(!volumes.some(v=>v.startsWith(prefix)),'Instalação exige volumes novos');
 const effective=JSON.parse(String(compose(state,['config','--format','json']))) as {name:string;volumes:{database:{name:string;external?:boolean};storage:{name:string}};services:{db:{environment:{POSTGRES_USER:string;POSTGRES_DB:string}};worker:{volumes:{target:string;read_only?:boolean}[]}}};assert.equal(effective.name,project);assert.equal(effective.volumes.database.name,project+'_database');assert.notEqual(effective.volumes.database.external,true);assert.equal(effective.volumes.storage.name,project+'_storage');assert.equal(effective.services.db.environment.POSTGRES_USER,'curriculos_qa');assert.equal(effective.services.db.environment.POSTGRES_DB,'curriculos_qa');const workerDataMount=effective.services.worker.volumes.find(volume=>volume.target==='/app/data');assert.equal(workerDataMount?.read_only,true,'Worker QA precisa montar os dados ativos como somente leitura');
 checks.push({name:'projeto isolado, configuração efetiva própria e volumes ausentes antes da instalação',passed:true,detail:{project,image_id,database_volume:effective.volumes.database.name,storage_volume:effective.volumes.storage.name}});
 state.artifact={publication:verified.publication,format:verified.format,manifest_sha256:verified.manifest_sha256,items:verified.items,relations:verified.relations,sources:verified.sources,parts_verified:verified.parts_verified,schema_verified:verified.schema_verified,schema_path:verified.schema_path,schema_sha256:verified.schema_sha256};
 checks.push({name:'todos shards do artefato entregue lidos e verificados antes da instalação',passed:true,detail:state.artifact});
 compose(state,['up','-d','--wait','--no-build','db']);qa.markResource(projectResource,'created');qa.markResource(volumeResources[0],'created');
 assert.equal(sql(state,"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"),'0');
 checks.push({name:'PostgreSQL inicialmente vazio confirmado',passed:true});
 compose(state,['run','--rm','--no-deps','app','npm','run','db:migrate']);
 const migrationsBefore=sql(state,'SELECT count(*) FROM schema_migrations');assert.ok(Number(migrationsBefore)>0);
 compose(state,['run','--rm','--no-deps','app','npm','run','db:migrate']);assert.equal(sql(state,'SELECT count(*) FROM schema_migrations'),migrationsBefore);
 checks.push({name:'migrations em banco vazio e reexecução idempotente',passed:true,detail:{migrations:Number(migrationsBefore)}});
 compose(state,['run','--rm','--no-deps','-e',`DATA_BUNDLE=${pinnedArtifact}`,'app','npx','tsx','scripts/ops-init.ts'],{timeout:30*60*1000});
 const imported=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;assert.ok(Number(imported.items)>0,'Publicação real precisa conter registros');assert.equal(imported.publication,state.artifact.publication);assert.equal(Number(imported.items),state.artifact.items);assert.equal(Number(imported.relations),state.artifact.relations);assert.equal(Number(imported.sources),state.artifact.sources);
 if(artifact.format==='curriculos-abertos/sharded-v1'){const stored=JSON.parse(sql(state,"SELECT json_build_object('storage_format',storage_format,'manifest_sha256',artifact_manifest_sha256,'embedded_items',payload ? 'items','embedded_relations',payload ? 'relations') FROM publications WHERE id=(SELECT publication_id FROM current_publication WHERE singleton=true)")) as Record<string,unknown>;assert.equal(stored.storage_format,'relational-v1');assert.equal(stored.manifest_sha256,artifact.sha256);assert.equal(stored.embedded_items,false);assert.equal(stored.embedded_relations,false);checks.push({name:'publicação persistida relacionalmente sem JSON nacional embutido',passed:true,detail:stored});}
 compose(state,['run','--rm','--no-deps','-e',`DATA_BUNDLE=${pinnedArtifact}`,'app','npx','tsx','scripts/ops-init.ts'],{timeout:30*60*1000});assert.deepEqual(JSON.parse(sql(state,snapshotSql)),imported);
 checks.push({name:'bundle real importado e segundo bootstrap preserva publicação/contagens/checksums',passed:true,detail:imported});
 state.capacity!.database=measureDatabaseFootprint(state.artifact.publication,statement=>sql(state!,statement));checks.push({name:'PostgreSQL e maior UF medidos para orçamento das próximas etapas',passed:true,detail:state.capacity!.database});
 const administratorPassword=randomBytes(24).toString('base64url');
 compose(state,['run','--rm','--no-deps','-T','app','npx','tsx','scripts/admin-create.ts','--email','production-qa@example.invalid','--name','Auditoria automatizada de instalação','--role','administrator','--actor-type','automated'],{input:administratorPassword+'\n'});
 assert.equal(sql(state,"SELECT count(*) FROM admin_roles WHERE role='administrator' AND actor_type='automated'"),'1');
 checks.push({name:'primeiro administrador criado por CLI com senha aleatória via stdin e ator automatizado',passed:true});
 compose(state,['up','-d','--wait','--no-build','app','worker']);qa.markResource(volumeResources[1],'created');
 await waitReady(base_url);
 const appContainer=String(compose(state,['ps','-q','app'])).trim();const workerContainer=String(compose(state,['ps','-q','worker'])).trim();
 assert.equal(String(run('docker',['inspect',appContainer,'--format','{{.Image}}'])).trim(),image_id);assert.equal(String(run('docker',['inspect',workerContainer,'--format','{{.Image}}'])).trim(),image_id);
 const imageHash=String(compose(state,['exec','-T','app','npx','tsx','scripts/release-check.ts','fingerprint'])).trim();assert.equal(imageHash,state.source_tree_sha256,'Imagem deve conter a árvore de código efetivamente entregue');
 checks.push({name:'imagem executada contém hash de código entregue e readiness de banco/publicação real',passed:true});
 const login=await fetch(base_url+'/api/auth/sign-in/email',{method:'POST',headers:{'Content-Type':'application/json',Origin:base_url},body:JSON.stringify({email:'production-qa@example.invalid',password:administratorPassword}),signal:AbortSignal.timeout(15000)});assert.equal(login.status,200,'Login real do primeiro administrador');
 checks.push({name:'login administrativo real sem serviço de email',passed:true});
 const api=await fetch(base_url+'/api/v1/aprendizagens?limit=1',{signal:AbortSignal.timeout(15000)});assert.equal(api.status,200);const apiBody=await api.json() as {publication:string;data:unknown[]};assert.equal(apiBody.publication,imported.publication);assert.equal(apiBody.data.length,1);
 const client=new Client({name:'curriculos-production-install-audit',version:'1.0.0'});try{await client.connect(new StreamableHTTPClientTransport(new URL(base_url+'/mcp')));const tools=await client.listTools();assert.equal(tools.tools.length,10);const call=await client.callTool({name:'buscar_aprendizagens',arguments:{publication:imported.publication,limit:1}});assert.ok(!call.isError);assert.equal((call.structuredContent as {publication?:string})?.publication,imported.publication);}finally{await client.close();}
 checks.push({name:'API HTTP real e cliente MCP Streamable HTTP negociaram e consultaram publicação importada',passed:true});
 const cleanSamples=new Map<string,SampleReference>();for(const sample of verified.samples)if(!cleanSamples.has(sample.uf))cleanSamples.set(sample.uf,sample);for(const sample of [...verified.samples].sort((a,b)=>b.text_length-a.text_length).slice(0,3))cleanSamples.set('long:'+sample.id,sample);
 for(const batch of sampleBatches([...new Map([...cleanSamples.values()].map(sample=>[sample.id,sample])).values()])){const response:Response=await fetch(base_url+'/api/v1/aprendizagens/consulta-lote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({publication:state.artifact.publication,ids:batch.map(sample=>sample.id)}),signal:AbortSignal.timeout(30000)});assert.equal(response.status,200);const body=await response.json() as {publication:string;data:{status:string;item:Learning|null}[]};assert.equal(body.publication,state.artifact.publication);assert.equal(body.data.length,batch.length);for(let index=0;index<batch.length;index++){const row=body.data[index];assert.equal(row.status,'found');assert.ok(row.item);matchSample(row.item,batch[index]);}}
 checks.push({name:'amostras reais por UF e textos longos preservados na instalação limpa',passed:true,detail:{samples:cleanSamples.size}});
 
 let heartbeat=false;for(let attempt=0;attempt<30;attempt++){heartbeat=Number(sql(state,"SELECT count(*) FROM worker_heartbeats WHERE seen_at > now()-interval '60 seconds'"))>0;if(heartbeat)break;await new Promise(r=>setTimeout(r,1000));}assert.ok(heartbeat,'Worker precisa persistir heartbeat');
 checks.push({name:'worker real conectado ao PostgreSQL persistiu heartbeat recente',passed:true});
 const before=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;
 compose(state,['restart','db','app','worker']);compose(state,['up','-d','--wait','--no-build','db','app','worker']);await waitReady(base_url);
 const after=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;assert.deepEqual(after,before);
 checks.push({name:'reinício de banco/app/worker preservou default, IDs, textos, relações e administrador',passed:true,detail:after});
 state.publication=String(after.publication);state.snapshot=after;writeFileSync(cleanStatePath,JSON.stringify(state,null,2)+'\n',{mode:0o600});
 const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source_tree_sha256:state.source_tree_sha256,publication:state.publication,project,base_url,image,image_id,artifact:state.artifact,diagnostic_only:diagnosticOnly,...(diagnosticLabel?{diagnostic_label:diagnosticLabel}:{}),checks,passed:true,remote_deployment:false,national_release_asserted:false};
 qa.recordReport('production-install',report);mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/production-install.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }catch(error){const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),checks,diagnostic_only:diagnosticOnly,...(diagnosticLabel?{diagnostic_label:diagnosticLabel}:{}),passed:false,error:error instanceof Error?error.message:String(error),project:state?.project,env_file:state?.env_file};qa.recordReport('production-install-failed',report);mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/production-install.json',JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report,null,2));process.exitCode=1;}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await withQaRun({kind:'production',purpose:'Instalação QA vazia, isolada e com prova de persistência',requiresDocker:true},main);
