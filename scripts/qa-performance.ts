import {writeFile,mkdir} from 'node:fs/promises';
import os from 'node:os';
import assert from 'node:assert/strict';
const base=process.env.TEST_BASE_URL??'http://127.0.0.1:3000';
const started_at=new Date().toISOString();
const get=async(path:string)=>{const r=await fetch(base+path);const body=await r.json();assert.ok(r.ok,`${r.status} ${path} ${JSON.stringify(body).slice(0,200)}`);return body;};
const publications=await get('/api/v1/publicacoes');
const pub=publications.data.find((p:{is_default?:boolean})=>p.is_default)??publications.data[0];
const publication=publications.publication||pub?.id;
assert.ok(publication,'Publicação carregada necessária para medição real');
const first=await get(`/api/v1/aprendizagens?publication=${encodeURIComponent(publication)}&limit=1`);
assert.ok(first.data.length,'Não medir corpus vazio');
const id=first.data[0].id;
const codeLookup=await get(`/api/v1/aprendizagens?uf=BR&publication=${encodeURIComponent(publication)}&limit=100`);
const codeItem=codeLookup.data.find((item:{code?:string})=>typeof item.code==='string'&&/^[A-Z]{2}\d{2}[A-Z]{2}\d{2}$/.test(item.code));
assert.ok(codeItem,'O corpus precisa conter um código nacional representativo para o ensaio de lookup.');
const code=codeItem.code;
const bncc=await get(`/api/v1/aprendizagens?uf=BR&publication=${encodeURIComponent(publication)}&limit=1`);
const suffix=`publication=${encodeURIComponent(publication)}`;
const operations=[
 {kind:'id',target:500,path:`/api/v1/aprendizagens/${encodeURIComponent(id)}?${suffix}`},
 {kind:'code',target:500,path:`/api/v1/aprendizagens?q=${encodeURIComponent(code??'educação')}&${suffix}`},
 {kind:'search',target:1500,path:`/api/v1/aprendizagens?q=matemática&stage=EF&${suffix}`},
 ...(bncc.data.length?[{kind:'panorama',target:1500,path:`/api/v1/bncc/aprendizagens/${encodeURIComponent(bncc.data[0].id)}/panorama?${suffix}`}]:[]),
 {kind:'compare',target:3000,path:'/api/v1/comparacoes',body:{ufs:['SP','MG','PR'],publication,limit:25}},
];
const request=async(op:{kind:string;target:number;path:string;body?:unknown})=>{const start=performance.now();let status=0;try{const r=await fetch(base+op.path,op.body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(op.body)}:undefined);status=r.status;await r.arrayBuffer();return {kind:op.kind,ms:performance.now()-start,status,ok:r.ok};}catch(error){return {kind:op.kind,ms:performance.now()-start,status,ok:false,error:String(error)};}};
const initial=[];
for(const op of operations)initial.push(await request(op));
const measurements:Awaited<ReturnType<typeof request>>[]=[];
let cursor=0;
await Promise.all(Array.from({length:10},async()=>{while(cursor<200){const index=cursor++; measurements.push(await request(operations[index%operations.length]));}}));
const ambiguous_numeric_fragment=await request({kind:'ambiguous_numeric_fragment_diagnostic',target:0,path:`/api/v1/aprendizagens?q=${encodeURIComponent(String(first.data[0].code??'1.1'))}&${suffix}`});
const mandatory_operations_present=operations.some(op=>op.kind==='panorama');
const distributions=operations.map(op=>{const rows=measurements.filter(x=>x.kind===op.kind);const ordered=rows.map(x=>x.ms).sort((a,b)=>a-b);const p95=ordered[Math.ceil(ordered.length*.95)-1];return {operation:op.kind,requests:rows.length,p50_ms:ordered[Math.floor(ordered.length*.5)],p95_ms:p95,target_p95_ms:op.target,errors:rows.filter(x=>!x.ok).length,passed:p95<=op.target&&rows.every(x=>x.ok)};});
const report={producer:'scripts/qa-performance.ts',command:'npx tsx scripts/qa-performance.ts',started_at,completed_at:new Date().toISOString(),publication,environment:{platform:os.platform(),arch:os.arch(),cpus:os.cpus().length,cpu:os.cpus()[0].model,memory_bytes:os.totalmem(),node:process.version,reference:'4 vCPU / 8 GB; medição no host entregue, sem normalizar metas'},dataset:{visible_total:first.total,local_count:measurements.length},scope_note:'Medição sobre a publicação identificada; completude nacional é verificada separadamente pelo gate documental. O caso de código usa um código BNCC representativo; um fragmento numérico curto e ambíguo é registrado à parte, sem substituir as metas.',concurrency:10,requests:200,initial,distributions,diagnostics:{ambiguous_numeric_fragment},assertions:[{name:'mandatory_operations_present',passed:mandatory_operations_present},{name:'200_requests_10_clients',passed:measurements.length===200},{name:'no_application_errors',passed:measurements.every(x=>x.ok)},{name:'latency_targets',passed:distributions.every(x=>x.passed)}],exit_code:mandatory_operations_present&&measurements.every(x=>x.ok)&&distributions.every(x=>x.passed)?0:1};
await mkdir('docs/evidence',{recursive:true});await writeFile('docs/evidence/performance.json',JSON.stringify(report,null,2));
console.log(JSON.stringify({publication,requests:200,concurrency:10,distributions,exit_code:report.exit_code},null,2));process.exitCode=report.exit_code;
