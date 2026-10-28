import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,mkdirSync,writeFileSync,rmSync } from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {sha256,sourceTreeHash,validateEvidence,recordExecution,type ExecutionEvidence} from '../scripts/release-check';
test('evidência exige código/publicação e artefatos íntegros, nunca somente um pronto manual',()=>{
 const root=mkdtempSync(join(tmpdir(),'curriculos-release-'));
 try{writeFileSync(join(root,'package.json'),'{}');writeFileSync(join(root,'run.log'),'actual test output');
 const hash=sourceTreeHash(root);const e:ExecutionEvidence={schema_version:1,kind:'api',command:['npx','tsx','scripts/api-verify.ts'],producer:'package.json',started_at:new Date().toISOString(),completed_at:new Date().toISOString(),exit_code:0,source_tree_sha256:hash,publication:'test-only-fixture',assertions:[{name:'contrato',passed:true}],artifacts:[{path:'run.log',sha256:sha256('actual test output')}]};
 assert.deepEqual(validateEvidence(e,root,hash,'test-only-fixture'),[]);
 assert.ok(validateEvidence({...e,source_tree_sha256:'old'},root,hash,'test-only-fixture').some(x=>x.includes('árvore')));
 assert.ok(validateEvidence({...e,publication:'other'},root,hash,'test-only-fixture').some(x=>x.includes('publicação')));assert.deepEqual(validateEvidence({...e,kind:'types',publication:null},root,hash,'test-only-fixture'),[]);
 assert.ok(validateEvidence({...e,exit_code:1},root,hash,'test-only-fixture').length);
 writeFileSync(join(root,'run.log'),'changed');assert.ok(validateEvidence(e,root,hash,'test-only-fixture').some(x=>x.includes('checksum')));
 assert.ok(validateEvidence({ready:true},root,hash,'test-only-fixture').length);
 }finally{rmSync(root,{recursive:true,force:true});}
});
test('hash de código muda com alteração e independe de docs de progresso',()=>{
 const root=mkdtempSync(join(tmpdir(),'curriculos-code-'));
 try{writeFileSync(join(root,'package.json'),'{}');const a=sourceTreeHash(root);mkdirSync(join(root,'docs'));writeFileSync(join(root,'docs/progress.md'),'progresso');assert.equal(sourceTreeHash(root),a);writeFileSync(join(root,'docs/requirements.md'),'mandato');assert.notEqual(sourceTreeHash(root),a);writeFileSync(join(root,'package.json'),'{"changed":true}');assert.notEqual(sourceTreeHash(root),a);}finally{rmSync(root,{recursive:true,force:true});}
});

test('gate recusa execução de navegador filtrada ou teste parcial antes de iniciar processo',()=>{assert.throws(()=>recordExecution('browser',['--','npx','playwright','test','--grep','um caso']),/execução integral/);assert.throws(()=>recordExecution('tests',['--','npm','test','--','um-arquivo']),/execução integral/);assert.throws(()=>recordExecution('api',['--','true']),/Comando obrigatório/);});

test('schema público de dados invalida evidência quando adicionado, alterado ou removido',()=>{
 const root=mkdtempSync(join(tmpdir(),'curriculos-schema-'));
 try{writeFileSync(join(root,'package.json'),'{}');const absent=sourceTreeHash(root);mkdirSync(join(root,'data/schema'),{recursive:true});const path=join(root,'data/schema/1.0.0.json');writeFileSync(path,'{"type":"object"}');const before=sourceTreeHash(root);assert.notEqual(before,absent);writeFileSync(path,'{"type":"array"}');assert.notEqual(sourceTreeHash(root),before);rmSync(path);assert.equal(sourceTreeHash(root),absent);}finally{rmSync(root,{recursive:true,force:true});}
});
