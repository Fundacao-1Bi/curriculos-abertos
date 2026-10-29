import { writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';
import { pool } from '../src/db/client';
import * as domain from '../src/domain/service';
const started_at=new Date().toISOString();
const checks:{name:string;ms:number;details:unknown}[]=[];
async function check<T>(name:string,action:()=>Promise<T>,inspect:(value:T)=>unknown) {const start=performance.now();const value=await action();checks.push({name,ms:performance.now()-start,details:inspect(value)});return value;}
try{
 const publication=await domain.resolvePublication();
 const ufs=await check('ufs',()=>domain.listUfs({publication}),r=>{assert.equal(r.data.length,27);return{total:r.total,ready:r.data.filter(x=>x.ready).length,item_count:r.data.reduce((n,x)=>n+x.item_count,0),by_uf:r.data.map(x=>({uf:x.uf,item_count:x.item_count,source_count:x.source_count,status:x.status}))};});
 assert.ok(ufs.data.some(x=>x.item_count>0));
 const national=await check('national_lookup',()=>domain.searchLearnings({publication,uf:'BR',limit:1}),r=>{assert.ok(r.data[0]?.code);return{total:r.total,id:r.data[0].id,code:r.data[0].code};});
 const nationalId=national.data[0].id;
 await check('exact_code',()=>domain.searchLearnings({publication,q:national.data[0].code!,limit:5}),r=>{assert.ok(r.data.some(i=>i.code===national.data[0].code));return{total:r.total,returned:r.data.length,next:r.next};});
 await check('get_national_item',()=>domain.getLearning(nationalId,{publication}),r=>{assert.equal(r.data.id,nationalId);assert.ok(r.data.evidence.length);return{id:r.data.id,source_id:r.data.source_id,evidence:r.data.evidence.length,relations:r.data.relations.length};});
 await check('panorama',()=>domain.panorama(nationalId,{publication,limit:5}),r=>{assert.equal(r.data.ufs.length,27);return{uf_count:27,total_local_items:r.data.ufs.reduce((n,x)=>n+x.total,0),states:r.data.ufs.map(x=>({uf:x.uf,status:x.status,total:x.total}))};});
 await check('compare_three_ufs',()=>domain.compare({publication,ufs:['SP','MG','PR'],limit:5}),r=>{assert.equal(r.data.columns.length,3);return{comparable:r.data.comparable,columns:r.data.columns.map(x=>({uf:x.uf,total:x.total,returned:x.items.length})),shared_references:r.data.shared_references.length};});
 await check('analyses',()=>domain.analyses({publication,stage:'EF',limit:5}),r=>{assert.ok(r.data.unique_items>0);assert.equal(r.data.matrix.rows[0]?.ufs.length,27);return{unique_items:r.data.unique_items,relations:r.data.relations,matrix_total:r.data.matrix.total,matrix_returned:r.data.matrix.rows.length};});
 await check('publications',()=>domain.listPublications({publication}),r=>{assert.ok(r.data.some(x=>x.id===publication&&x.is_default));return{total:r.total,ids:r.data.map(x=>x.id)};});
 await writeFile('docs/evidence/domain-real-corpus.json',JSON.stringify({producer:'scripts/domain-real-check.ts',started_at,completed_at:new Date().toISOString(),publication,scope:'Sequential service diagnostics over real loaded corpus; not HTTP load test and not evidence of national editorial completeness.',checks,exit_code:0},null,2)+'\n');
 console.log(JSON.stringify({publication,checks:checks.map(c=>({name:c.name,ms:c.ms})),exit_code:0}));
}catch(error){await writeFile('docs/evidence/domain-real-corpus.json',JSON.stringify({producer:'scripts/domain-real-check.ts',started_at,completed_at:new Date().toISOString(),checks,error:(error as Error).message,exit_code:1},null,2)+'\n');console.error((error as Error).message);process.exitCode=1;}finally{await pool.end();}
