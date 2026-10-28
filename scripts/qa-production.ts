/** Clean, isolated Compose installation and persistence verification. Never touches the main project. */
import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { existsSync,mkdirSync,readFileSync,writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { sourceTreeHash } from './release-check';
import { openAuditArtifact,inspectAuditArtifact,latestAuditPublication } from './audit-artifact';
export interface CleanState {project:string;env_file:string;base_url:string;database_port:number;image:string;image_id:string;publication:string;snapshot:Record<string,unknown>;created_at:string;source_tree_sha256:string;artifact?:{publication:string;format:string;manifest_sha256:string;items:number;relations:number;sources:number;parts_verified:number};}
export const cleanStatePath='var/qa-clean-state.json';
export function run(command:string,args:string[],options:{input?:string|Buffer;env?:Record<string,string|undefined>;binary?:boolean;timeout?:number}={}) {
 const result=spawnSync(command,args,{cwd:process.cwd(),env:{...process.env,...options.env},input:options.input,encoding:options.binary?undefined:'utf8',maxBuffer:512*1024*1024,timeout:options.timeout||300_000});
 if(result.status!==0){const raw=String(result.stderr||result.stdout||result.error?.message||'sem diagnóstico');throw new Error(`${command} ${args.slice(0,2).join(' ')}: exit ${result.status}; ${raw.slice(-5000)}`);}
 return options.binary?Buffer.from(result.stdout):String(result.stdout);
}
export function compose(state:Pick<CleanState,'project'|'env_file'>,args:string[],options:Parameters<typeof run>[2]={}){return run('docker',['compose','--env-file',state.env_file,'-p',state.project,...args],options);}
export function sql(state:Pick<CleanState,'project'|'env_file'>,statement:string,database='curriculos_qa'){
 return String(compose(state,['exec','-T','db','psql','-U','curriculos_qa','-d',database,'-At','-v','ON_ERROR_STOP=1','-c',statement])).trim();
}
export const snapshotSql=`SELECT json_build_object('publication',(SELECT publication_id FROM current_publication WHERE singleton=true),'publications',(SELECT count(*) FROM publications),'items',(SELECT count(*) FROM items),'sources',(SELECT count(*) FROM sources),'relations',(SELECT count(*) FROM relations),'admins',(SELECT count(*) FROM admin_roles),'publication_metadata_digest',(SELECT md5(string_agg(id||':'||sha256||':'||storage_format,',' ORDER BY id)) FROM publications),'items_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM items),'source_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM sources),'relations_digest',(SELECT md5(string_agg(publication_id||':'||id||':'||md5(payload::text),',' ORDER BY publication_id,id)) FROM relations));`;
export async function waitReady(base:string){let last='';for(let n=0;n<60;n++){try{const r=await fetch(base+'/api/ready',{signal:AbortSignal.timeout(5000)});if(r.status===200)return await r.json() as Record<string,unknown>;last=String(r.status);}catch(e){last=e instanceof Error?e.message:String(e);}await new Promise(r=>setTimeout(r,1000));}throw new Error(`Readiness não atingida: ${last}`);}
export function loadCleanState(){const state=JSON.parse(readFileSync(cleanStatePath,'utf8')) as CleanState;if(!/^curriculos-abertos-clean-[a-z0-9-]+$/.test(state.project)||!state.env_file.startsWith('var/qa-clean-'))throw new Error('Estado de projeto QA fora do isolamento esperado.');return state;}
async function main(){const started_at=new Date().toISOString();const checks:{name:string;passed:boolean;detail?:unknown}[]=[];let state:CleanState|undefined;
 try{
 const token=new Date().toISOString().replace(/\D/g,'').slice(0,14)+'-'+randomBytes(3).toString('hex');
 const project=`curriculos-abertos-clean-${token}`,env_file=`var/qa-clean-${token}.env`,port=Number(process.env.QA_PORT||3001),database_port=Number(process.env.QA_DATABASE_PORT||55438),image=`curriculos-abertos:${process.env.RELEASE_TAG||'local'}`;
 assert.ok(port!==3000&&database_port!==55437,'QA deve usar portas diferentes da distribuição principal');
 mkdirSync('var',{recursive:true});const password=randomBytes(32).toString('hex');const secret=randomBytes(48).toString('hex');
 const base_url=`http://localhost:${port}`;
 const configuredDb=existsSync('.env')?readFileSync('.env','utf8').match(/^POSTGRES_IMAGE=(.+)$/m)?.[1].trim():undefined;const postgresImage=process.env.QA_POSTGRES_IMAGE||process.env.POSTGRES_IMAGE||configuredDb||'postgres:17.7-bookworm';assert.match(postgresImage,/^[a-zA-Z0-9_./:@-]+$/,'Referência de imagem PostgreSQL inválida');
 const env=`POSTGRES_IMAGE=${postgresImage}\nPOSTGRES_USER=curriculos_qa\nPOSTGRES_DB=curriculos_qa\nPOSTGRES_PASSWORD=${password}\nBETTER_AUTH_SECRET=${secret}\nPUBLIC_URL=${base_url}\nPORT=${port}\nDATABASE_PORT=${database_port}\nRELEASE_TAG=${process.env.RELEASE_TAG||'local'}\nPUBLIC_RATE_LIMIT=1000\nMCP_ALLOWED_HOSTS=localhost:${port},127.0.0.1:${port}\nSOURCE_CHECK_ENABLED=false\n`;
 writeFileSync(env_file,env,{mode:0o600});
 const image_id=String(run('docker',['image','inspect',image,'--format','{{.Id}}'])).trim();
 state={project,env_file,base_url,database_port,image,image_id,publication:'',snapshot:{},created_at:new Date().toISOString(),source_tree_sha256:sourceTreeHash()};
 const prefix=project+'_';const volumes=String(run('docker',['volume','ls','--format','{{.Name}}'])).split('\n');assert.ok(!volumes.some(v=>v.startsWith(prefix)),'Instalação exige volumes novos');
 checks.push({name:'projeto isolado, imagem de produção existente e volumes ausentes antes da instalação',passed:true,detail:{project,image_id}});
 const publication=await latestAuditPublication();const artifact=await openAuditArtifact(publication),verified=await inspectAuditArtifact(artifact);assert.ok(verified.passed,JSON.stringify(verified.errors));
 state.artifact={publication:verified.publication,format:verified.format,manifest_sha256:verified.manifest_sha256,items:verified.items,relations:verified.relations,sources:verified.sources,parts_verified:verified.parts_verified};
 checks.push({name:'todos shards do artefato entregue lidos e verificados antes da instalação',passed:true,detail:state.artifact});
 compose(state,['up','-d','--wait','--no-build','db']);
 assert.equal(sql(state,"SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"),'0');
 checks.push({name:'PostgreSQL inicialmente vazio confirmado',passed:true});
 compose(state,['run','--rm','--no-deps','app','npm','run','db:migrate']);
 const migrationsBefore=sql(state,'SELECT count(*) FROM schema_migrations');assert.ok(Number(migrationsBefore)>0);
 compose(state,['run','--rm','--no-deps','app','npm','run','db:migrate']);assert.equal(sql(state,'SELECT count(*) FROM schema_migrations'),migrationsBefore);
 checks.push({name:'migrations em banco vazio e reexecução idempotente',passed:true,detail:{migrations:Number(migrationsBefore)}});
 compose(state,['run','--rm','--no-deps','app','npx','tsx','scripts/ops-init.ts']);
 const imported=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;assert.ok(Number(imported.items)>0,'Publicação real precisa conter registros');assert.equal(imported.publication,state.artifact.publication);assert.equal(Number(imported.items),state.artifact.items);assert.equal(Number(imported.relations),state.artifact.relations);assert.equal(Number(imported.sources),state.artifact.sources);
 if(artifact.format==='curriculos-abertos/sharded-v1'){const stored=JSON.parse(sql(state,"SELECT json_build_object('storage_format',storage_format,'manifest_sha256',artifact_manifest_sha256,'embedded_items',payload ? 'items','embedded_relations',payload ? 'relations') FROM publications WHERE id=(SELECT publication_id FROM current_publication WHERE singleton=true)")) as Record<string,unknown>;assert.equal(stored.storage_format,'relational-v1');assert.equal(stored.manifest_sha256,artifact.sha256);assert.equal(stored.embedded_items,false);assert.equal(stored.embedded_relations,false);checks.push({name:'publicação persistida relacionalmente sem JSON nacional embutido',passed:true,detail:stored});}
 compose(state,['run','--rm','--no-deps','app','npx','tsx','scripts/ops-init.ts']);assert.deepEqual(JSON.parse(sql(state,snapshotSql)),imported);
 checks.push({name:'bundle real importado e segundo bootstrap preserva publicação/contagens/checksums',passed:true,detail:imported});
 const administratorPassword=randomBytes(24).toString('base64url');
 compose(state,['run','--rm','--no-deps','-T','app','npx','tsx','scripts/admin-create.ts','--email','production-qa@example.invalid','--name','Auditoria automatizada de instalação','--role','administrator','--actor-type','automated'],{input:administratorPassword+'\n'});
 assert.equal(sql(state,"SELECT count(*) FROM admin_roles WHERE role='administrator' AND actor_type='automated'"),'1');
 checks.push({name:'primeiro administrador criado por CLI com senha aleatória via stdin e ator automatizado',passed:true});
 compose(state,['up','-d','--wait','--no-build','app','worker']);
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
 let heartbeat=false;for(let attempt=0;attempt<30;attempt++){heartbeat=Number(sql(state,"SELECT count(*) FROM worker_heartbeats WHERE seen_at > now()-interval '60 seconds'"))>0;if(heartbeat)break;await new Promise(r=>setTimeout(r,1000));}assert.ok(heartbeat,'Worker precisa persistir heartbeat');
 checks.push({name:'worker real conectado ao PostgreSQL persistiu heartbeat recente',passed:true});
 const before=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;
 compose(state,['restart','db','app','worker']);compose(state,['up','-d','--wait','--no-build','db','app','worker']);await waitReady(base_url);
 const after=JSON.parse(sql(state,snapshotSql)) as Record<string,unknown>;assert.deepEqual(after,before);
 checks.push({name:'reinício de banco/app/worker preservou default, IDs, textos, relações e administrador',passed:true,detail:after});
 state.publication=String(after.publication);state.snapshot=after;writeFileSync(cleanStatePath,JSON.stringify(state,null,2)+'\n',{mode:0o600});
 const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),source_tree_sha256:state.source_tree_sha256,publication:state.publication,project,base_url,image,image_id,artifact:state.artifact,checks,passed:true,remote_deployment:false,national_release_asserted:false};
 mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/production-install.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
 }catch(error){const report={schema_version:1,actor_type:'automated',started_at,completed_at:new Date().toISOString(),checks,passed:false,error:error instanceof Error?error.message:String(error),project:state?.project,env_file:state?.env_file};mkdirSync('docs/evidence',{recursive:true});writeFileSync('docs/evidence/production-install.json',JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report,null,2));process.exitCode=1;}
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))await main();
