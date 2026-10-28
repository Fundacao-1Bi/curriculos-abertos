/** Release gate. Never substitutes implementation flags for executed evidence. */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export interface Assertion { name:string; passed:boolean; details?:unknown }
export interface ExecutionEvidence { schema_version:1; kind:string; command:string[]; producer:string; started_at:string; completed_at:string; exit_code:number|null; source_tree_sha256:string; publication:string|null; assertions:Assertion[]; artifacts:{path:string;sha256:string}[]; [key:string]:unknown }
export interface Check {id:string; passed:boolean; detail:string; evidence:string[]}
const trackedRoots=['src','scripts','pipeline','tests'];
const trackedFiles=['package.json','package-lock.json','tsconfig.json','next.config.ts','Dockerfile','compose.yaml','Makefile','.env.example','.dockerignore','eslint.config.mjs','playwright.config.ts','docs/requirements.md'];
export const sha256=(data:string|Buffer)=>createHash('sha256').update(data).digest('hex');
export function sourceTreeHash(root=process.cwd()):string {
  const paths:string[]=[];
  function walk(path:string){ if(!existsSync(path))return; for(const entry of readdirSync(path,{withFileTypes:true})){if(entry.name.startsWith('.')||entry.name==='__pycache__')continue;const p=join(path,entry.name);if(entry.isDirectory())walk(p);else if(entry.isFile()&&!p.endsWith('.pyc'))paths.push(p);} }
  for(const name of trackedRoots)walk(join(root,name));
  for(const name of trackedFiles)if(existsSync(join(root,name)))paths.push(join(root,name));
  const hash=createHash('sha256'); for(const path of paths.sort())hash.update(relative(root,path)).update('\0').update(readFileSync(path)).update('\0');
  return hash.digest('hex');
}

export function validateEvidence(value:unknown, root:string, codeHash:string, publication:string|null):string[] {
  const errors:string[]=[];
  if(!value||typeof value!=='object')return ['registro ausente ou inválido'];
  const e=value as Partial<ExecutionEvidence>;
  if(e.schema_version!==1)errors.push('schema de evidência não suportado');
  if(!e.kind||!e.producer||!Array.isArray(e.command)||!e.command.length)errors.push('tipo, produtor ou comando ausente');
  if(e.exit_code!==0)errors.push('execução não terminou com exit 0');
  if(e.source_tree_sha256!==codeHash)errors.push('código da execução difere da árvore atual');
  if(publication&&!['types','lint','build','tests'].includes(e.kind||'')&&e.publication!==publication)errors.push('publicação da execução difere do bundle');
  const started=Date.parse(e.started_at||''), completed=Date.parse(e.completed_at||'');
  if(!Number.isFinite(started)||!Number.isFinite(completed)||completed<started||completed>Date.now()+60_000)errors.push('datas de execução inválidas');
  if(!Array.isArray(e.assertions)||e.assertions.length===0||e.assertions.some(a=>!a||typeof a.name!=='string'||a.passed!==true))errors.push('asserções ausentes ou falhas');
  if(!Array.isArray(e.artifacts)||!e.artifacts.length)errors.push('artefatos de execução ausentes');
  else for(const artifact of e.artifacts){
    const path=resolve(root,artifact.path);if(!path.startsWith(resolve(root)+'/')||!existsSync(path)||!statSync(path).isFile()){errors.push(`artefato inexistente/externo: ${artifact.path}`);continue;}
    if(sha256(readFileSync(path))!==artifact.sha256)errors.push(`checksum divergente: ${artifact.path}`);
  }
  if(e.producer){const producer=resolve(root,e.producer);if(!producer.startsWith(resolve(root)+'/')||!existsSync(producer))errors.push('produtor não está no repositório');}
  return errors;
}

const evidenceKinds={
  containers:['docker','compose','build'], types:['npm','run','typecheck'], build:['npm','run','build'], lint:['npm','run','lint'], tests:['npm','test'],
  api:['npx','tsx','scripts/api-verify.ts'], mcp:['npx','tsx','scripts/mcp-verify.ts'],
  browser:['npx','playwright','test'], production:['npx','tsx','scripts/qa-production.ts'], recovery:['npx','tsx','scripts/qa-recovery.ts'], operations:['npx','tsx','scripts/ops-smoke.ts'],
  performance:['npx','tsx','scripts/qa-performance.ts'], admin:['npx','tsx','scripts/ops-verify.ts','--admin'],
  sources:['bash','scripts/sources-check.sh'], audit:['npx','tsx','scripts/audit-verify.ts'],
} as const;
export type EvidenceKind=keyof typeof evidenceKinds;
function option(args:string[],key:string):string|undefined{const i=args.indexOf(key);return i<0?undefined:args[i+1];}
export function recordExecution(kind:EvidenceKind, args:string[], root=process.cwd()):number{
  if(!(kind in evidenceKinds))throw new Error('Tipo desconhecido de evidência');
  const sep=args.indexOf('--'); const command=sep<0?[...evidenceKinds[kind]]:args.slice(sep+1);
  const expected=evidenceKinds[kind];
  if(!expected.every((part,i)=>command[i]===part))throw new Error(`Comando obrigatório para ${kind}: ${expected.join(' ')}`);
  let publication=option(args,'--publication')||null;
  if((kind==='browser'||kind==='tests')&&command.length!==expected.length)throw new Error('O gate exige execução integral, sem filtro de testes, grep, projeto ou shard.');
  const producer=kind==='containers'?'Dockerfile':kind==='types'||kind==='build'||kind==='lint'||kind==='tests'?'package.json':kind==='browser'?'playwright.config.ts':kind==='sources'?'scripts/sources-check.sh':expected[2]||expected[1];
  const source_tree_sha256=sourceTreeHash(root), started_at=new Date().toISOString();
  const result=spawnSync(command[0],command.slice(1),{cwd:root,encoding:'utf8',timeout:600_000,maxBuffer:32*1024*1024,env:process.env});
  const completed_at=new Date().toISOString(), prefix=`docs/evidence/executions/${kind}`;
  mkdirSync(join(root,dirname(prefix)),{recursive:true});
  const log=(result.stdout||'')+(result.stderr||'')+(result.error?`\n${result.error.message}\n`:'');
  writeFileSync(join(root,`${prefix}.log`),log);
  const assertions:Assertion[]=[{name:'processo concluiu com sucesso',passed:result.status===0}];
  const artifacts:{path:string;sha256:string}[]=[{path:`${prefix}.log`,sha256:sha256(log)}];
  const reports:Partial<Record<EvidenceKind,string>>={api:'docs/evidence/api-verification.json',mcp:'docs/evidence/mcp-interoperability.json',browser:'docs/evidence/browser-results.json',admin:'docs/evidence/admin-operations.json',performance:'docs/evidence/performance.json',audit:'docs/evidence/audit-integrated.json',production:'docs/evidence/production-install.json',recovery:'docs/evidence/backup-restore.json'};
  const object=(value:unknown):Record<string,unknown>=>value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
  const path=reports[kind];
  if(path){let report:Record<string,unknown>={};let reportCurrent=false;try{const bytes=readFileSync(join(root,path));report=object(JSON.parse(bytes.toString('utf8')));reportCurrent=statSync(join(root,path)).mtimeMs>=Date.parse(started_at)-1000;artifacts.push({path,sha256:sha256(bytes)});}catch{/* missing execution proof */}
   let reportedPublications:unknown[]=[];let reportPassed=false;
   if(kind==='api'){reportedPublications=[report.publication];reportPassed=report.success===true;}
   else if(kind==='mcp'){const results=Array.isArray(report.results)?report.results.map(object):[];reportedPublications=results.map(row=>row.publication).filter(Boolean);reportPassed=report.success===true&&['http','stdio'].every(transport=>results.some(row=>row.transport===transport&&row.success===true));}
   else if(kind==='admin'){reportedPublications=[report.base_publication];reportPassed=report.result==='passed';}
   else if(kind==='performance'){reportedPublications=[report.publication];reportPassed=report.exit_code===0;}
   else if(kind==='browser'){const annotations:Record<string,unknown>[]=[];const visit=(value:unknown)=>{if(Array.isArray(value)){for(const entry of value)visit(entry);}else if(value&&typeof value==='object'){const row=object(value);if(row.type==='data-publication')annotations.push(row);for(const nested of Object.values(row))visit(nested);}};visit(report.suites);reportedPublications=annotations.map(row=>row.description);const stats=object(report.stats),config=object(report.config),projects=Array.isArray(config.projects)?config.projects.map(object):[];reportPassed=Number(stats.expected)>0&&stats.unexpected===0&&stats.skipped===0&&Number(stats.flaky||0)===0&&annotations.length>=Number(stats.expected)&&['desktop','mobile'].every(name=>projects.some(project=>project.name===name));}
   else {reportedPublications=[report.publication];reportPassed=report.passed===true;}
   const unique=[...new Set(reportedPublications.filter((value):value is string=>typeof value==='string'&&value.length>0))];if(!publication&&unique.length===1)publication=unique[0];
   assertions.push({name:'relatório estruturado foi gerado nesta execução e aprovado',passed:reportCurrent&&reportPassed,details:{path,report_current:reportCurrent,report_passed:reportPassed}});
   assertions.push({name:'publicação do relatório real coincide com alvo',passed:unique.length===1&&unique[0]===publication,details:{reported_publications:unique,target:publication}});
  }
  if(kind==='operations'){const records=log.split('\n').flatMap(line=>{try{return[object(JSON.parse(line))];}catch{return[];}});const smoke=records.find(row=>row.event==='ops_smoke_passed');const rows=Array.isArray(smoke?.results)?smoke.results.map(object):[];const actual=rows.map(row=>object(row.result).publication).find(value=>typeof value==='string');if(!publication&&typeof actual==='string')publication=actual;assertions.push({name:'smoke real identifica a publicação consultada',passed:typeof actual==='string'&&actual===publication});}
  if(kind==='tests'){const skipped=[...log.matchAll(/(?:ℹ|#)\s+skipped\s+(\d+)/g)].map(match=>Number(match[1]));assertions.push({name:'testes relevantes executados sem skips',passed:skipped.length>0&&skipped.every(value=>value===0),details:{skipped_counts:skipped}});}
  const record:ExecutionEvidence={schema_version:1,kind,command,producer,started_at,completed_at,exit_code:result.status,source_tree_sha256,publication,data_scope:['types','lint','build','tests'].includes(kind)?'code_only':'publication',assertions,artifacts};
  writeFileSync(join(root,`${prefix}.json`),JSON.stringify(record,null,2)+'\n');
  process.stdout.write(log); return result.status===0&&assertions.every(assertion=>assertion.passed)?0:1;
}

const requirementsEvidence:Record<string,string[]>={
 'ESC-01':['data','browser','api','mcp'],'ESC-02':['data','audit'],'ESC-03':['browser','api','mcp','admin','operations'],'ESC-04':['audit'],'ESC-05':['audit','browser','api','mcp'],
 'ORQ-01':['audit'],'ORQ-02':['audit'],
 'DAT-01':['data','tests','api'],'DAT-02':['data','tests','audit'],'DAT-03':['tests','browser','api','mcp'],'DAT-04':['tests','api','mcp','operations'],'DAT-05':['data','audit'],
 'ING-01':['data'],'ING-02':['data','operations','admin'],'ING-03':['data'],'ING-04':['data','operations'],'ING-05':['data'],
 'FUN-01':['data','browser'],'FUN-02':['data','browser'],'FUN-03':['tests','browser','api'],'FUN-04':['browser','api'],'FUN-05':['data','browser','api'],'FUN-06':['browser','api','tests'],'FUN-07':['data','browser','api'],'FUN-08':['browser','api','operations'],'FUN-09':['data','browser','operations'],'FUN-10':['browser','api','mcp'],'FUN-11':['browser','admin'],'FUN-12':['browser'],
 'API-01':['api'],'API-02':['api','tests'], 'MCP-01':['mcp'],'MCP-02':['mcp'],'MCP-03':['mcp'],
 'ADM-01':['admin'],'ADM-02':['admin','operations'],'ADM-03':['sources','operations'],
 'ARQ-01':['types','build','containers','operations'],'ARQ-02':['tests','production','operations'],'ARQ-03':['audit','data'],
 'SEG-01':['audit','tests','api','admin'],'SEG-02':['operations','admin','production','recovery'],
 'OPS-01':['containers','production','operations','data','negative'],'OPS-02':['data','operations','recovery'],'OPS-03':['production'],'OPS-04':['production','recovery','operations','admin'],
 'QA-01':['lint','types','tests','build','api','mcp','browser','data','negative'],'QA-02':['browser','api','mcp','admin','operations'],'QA-03':['browser'],'QA-04':['performance','data'],'QA-05':['audit'],
 'ACE-01':['data','browser','api','mcp'],'ACE-02':['data','negative','containers','lint','types','tests','build','api','mcp','browser','admin','operations','production','recovery','performance','audit'],'ACE-03':['audit'],'ACE-04':['audit'],
};
const implementations:Record<string,string>={ESC:'src/shared/contracts.ts; src/domain; portal/API/MCP',ORQ:'docs/architecture.md; docs/progress.md',DAT:'src/shared/contracts.ts; src/db; src/domain',ING:'pipeline; data/manifests; data/bundles; data/coverage-manifest.json',FUN:'src/app; src/components; src/domain/service.ts',API:'src/app/api/v1; src/mcp/contracts.ts',MCP:'src/app/mcp; src/mcp; scripts/mcp-verify.ts',ADM:'src/admin; src/app/admin; src/worker',ARQ:'package-lock.json; src/db; compose.yaml',SEG:'src/admin; src/mcp; pipeline; testes de autorização',OPS:'Dockerfile; compose.yaml; scripts/ops*; Makefile',QA:'tests; docs/evidence; scripts/release-check.ts',ACE:'docs/audit.md; relatório deste comando'};

export function evaluateRelease(root=process.cwd(), bundleArg?:string){
 const codeHash=sourceTreeHash(root), checks:Check[]=[];
 const requirements=readFileSync(join(root,'docs/requirements.md'),'utf8');
 const ids=[...requirements.matchAll(/^### ([A-Z]+-\d+)\. (.+)$/gm)].map(m=>({id:m[1],title:m[2]}));
 let dataReport:unknown=null, publication:string|null=null;
 const dataCommand=['python3','pipeline/release_check.py','--json',...(bundleArg?['--bundle',bundleArg]:[])];
 const data=spawnSync(dataCommand[0],dataCommand.slice(1),{cwd:root,encoding:'utf8',timeout:180_000,maxBuffer:16*1024*1024});
 try{dataReport=JSON.parse(data.stdout||'null');publication=(dataReport as {publication?:string;publication_id?:string})?.publication||(dataReport as {publication_id?:string})?.publication_id||null;}catch{/* parser error is blocking */}
 const documentary=dataReport as {passed?:boolean;checks?:unknown[]}|null;
 const dataPassed=data.status===0&&Boolean(publication)&&documentary?.passed===true&&Array.isArray(documentary.checks)&&documentary.checks.length>0;
 checks.push({id:'data',passed:dataPassed,detail:dataPassed?'Corpus e reconciliação aprovados pelo validador documental':'Corpus nacional não aprovado; detalhes no resultado documental',evidence:['pipeline/release_check.py','data/coverage-manifest.json']});
 const negative=spawnSync('python3',['pipeline/release_check.py','--self-test'],{cwd:root,encoding:'utf8',timeout:30_000,maxBuffer:1024*1024});let negativeReport:Record<string,unknown>|null=null;try{negativeReport=JSON.parse(negative.stdout);}catch{/* fail closed */}
 const negativePassed=negative.status===0&&negativeReport?.passed===true&&negativeReport.fixture_isolated===true&&negativeReport.published_data_modified===false&&negativeReport.baseline_passed===true&&negativeReport.mutated_passed===false&&typeof negativeReport.baseline_sha256==='string'&&negativeReport.baseline_sha256!==negativeReport.mutated_sha256&&Array.isArray(negativeReport.newly_missing_scope)&&negativeReport.newly_missing_scope.length>0;
 checks.push({id:'negative',passed:negativePassed,detail:negativePassed?'Recorte isolado passa antes e bloqueia após remoção controlada de componente obrigatório':'Caso negativo documental não demonstrado',evidence:['docs/evidence/data-release-negative.json']});
 const evidenceDetails:Record<string,unknown>={};
 for(const kind of Object.keys(evidenceKinds)){
  const path=`docs/evidence/executions/${kind}.json`;let record:unknown=null;let errors:string[];
  try{record=JSON.parse(readFileSync(join(root,path),'utf8'));errors=validateEvidence(record,root,codeHash,publication);const executed=record as ExecutionEvidence;const expected=evidenceKinds[kind as EvidenceKind];if(executed.kind!==kind||!expected.every((part,index)=>executed.command?.[index]===part))errors.push('tipo/comando não corresponde ao gate');}catch{errors=['execução não registrada'];}
  checks.push({id:kind,passed:errors.length===0,detail:errors.length?errors.join('; '):'Execução e artefatos conferidos para o código/publicação',evidence:[path]});
  evidenceDetails[kind]={errors,record};
 }
 const matrix=ids.map(({id,title})=>{
  const needed=requirementsEvidence[id]||['unmapped'];const failed=needed.filter(kind=>!checks.find(c=>c.id===kind)?.passed);
  return {id,requirement:title,implementation:implementations[id.split('-')[0]]||'',test_or_inspection:needed,code_sha256:codeHash,publication,result:failed.length?'não verificado':'verificado',pending:failed,evidence:needed.flatMap(kind=>checks.find(c=>c.id===kind)?.evidence||[])};
 });
 return {schema_version:1,generated_at:new Date().toISOString(),actor_type:'automated',actor_id:'codex-independent-auditor',source_tree_sha256:codeHash,publication,passed:matrix.every(row=>row.result==='verificado'),checks,requirements:matrix,documentary_report:dataReport,negative_report:negativeReport,documentary_execution:{command:dataCommand,exit_code:data.status,error:data.error?.message||null,stderr:data.stderr?.slice(0,2000)||null},evidence:evidenceDetails,limitations:['Conferência automatizada; não equivale a homologação institucional ou revisão pedagógica humana.','Registros de execução comprovam os comandos e artefatos. A auditoria independente deve conferir o conteúdo dos testes e a cobertura das jornadas.']};
}
function markdown(report:ReturnType<typeof evaluateRelease>){return `# Matriz de verificação\n\nGerada por scripts/release-check.ts em ${report.generated_at}. Ator: auditor automatizado independente. Código SHA-256: \`${report.source_tree_sha256}\`. Publicação: \`${report.publication||'não identificada'}\`. Resultado do lançamento nacional: **${report.passed?'APROVADO':'NÃO APROVADO'}**.\n\nA existência de código ou teste não comprova execução. Cada gate confere código, publicação, término, asserções e checksums dos artefatos. Dados dependem do inventário e da reconciliação documental, não do número de siglas cadastradas.\n\n| ID | Requisito | Implementação/rota | Teste/inspeção | Entrada/recorte | Evidência | Código | Publicação | Resultado | Pendência |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n${report.requirements.map(row=>`| ${row.id} | ${row.requirement} | ${row.implementation} | ${row.test_or_inspection.join(', ')} | publicação nacional / jornadas previstas no mandato | ${row.evidence.join('; ')} | ${report.source_tree_sha256.slice(0,12)} | ${row.publication||'não identificada'} | ${row.result} | ${row.pending.join(', ')||'—'} |`).join('\n')}\n\n## Gates de execução\n\n${report.checks.map(check=>`- ${check.id}: ${check.passed?'verificado':'não verificado'} — ${check.detail}`).join('\n')}\n\n## Limites\n\n${report.limitations.join('\n\n')}\n`}
function main(){const args=process.argv.slice(2);if(args[0]==='fingerprint'){console.log(sourceTreeHash());return;}
 if(args[0]==='record'){process.exitCode=recordExecution(option(args,'--kind') as EvidenceKind,args);return;}
 const report=evaluateRelease(process.cwd(),option(args,'--bundle'));
 const output=option(args,'--output')||'docs/evidence/release-check.json';mkdirSync(dirname(output),{recursive:true});writeFileSync(output,JSON.stringify(report,null,2)+'\n');writeFileSync('docs/verification.md',markdown(report));
 if(args.includes('--json'))console.log(JSON.stringify(report));else console.log(`Lançamento ${report.passed?'APROVADO':'NÃO APROVADO'}; ${report.requirements.filter(r=>r.result==='verificado').length}/${report.requirements.length} requisitos verificados. Relatório: ${output}`);
 process.exitCode=report.passed?0:1;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url))main();
