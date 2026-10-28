import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync,mkdirSync,writeFileSync,rmSync } from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {sha256,sourceTreeHash,validateEvidence,recordExecution,ingestionScopeErrors,type ExecutionEvidence} from '../scripts/release-check';
test('evidência exige código/publicação e artefatos íntegros, nunca somente um pronto manual',()=>{
 const root=mkdtempSync(join(tmpdir(),'curriculos-release-'));
 try{writeFileSync(join(root,'package.json'),'{}');writeFileSync(join(root,'run.log'),'actual test output');
 const hash=sourceTreeHash(root);const e:ExecutionEvidence={schema_version:1,kind:'api',command:['npx','tsx','scripts/api-verify.ts'],producer:'package.json',started_at:new Date().toISOString(),completed_at:new Date().toISOString(),exit_code:0,source_tree_sha256:hash,publication:'test-only-fixture',assertions:[{name:'contrato',passed:true}],artifacts:[{path:'run.log',sha256:sha256('actual test output')}]};
 assert.deepEqual(validateEvidence(e,root,hash,'test-only-fixture'),[]);
 assert.ok(validateEvidence({...e,source_tree_sha256:'old'},root,hash,'test-only-fixture').some(x=>x.includes('árvore')));
 assert.ok(validateEvidence({...e,publication:'other'},root,hash,'test-only-fixture').some(x=>x.includes('publicação')));assert.deepEqual(validateEvidence({...e,kind:'types',command:['npm','run','typecheck'],publication:null},root,hash,'test-only-fixture'),[]);
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
test('mudança de Source ou adapter invalida prova anterior de ingestão mesmo sem mudar publicação',()=>{
 const root=mkdtempSync(join(tmpdir(),'curriculos-ingestion-inputs-'));
 try{writeFileSync(join(root,'package.json'),'{}');mkdirSync(join(root,'data/manifests/uncoded'),{recursive:true});writeFileSync(join(root,'data/manifests/source.json'),'{"id":"isolated-source","url":"https://example.invalid/one"}');const adapter=join(root,'data/manifests/uncoded/one.json');writeFileSync(adapter,'{"items":[{"text":"literal original"}]}');const before=sourceTreeHash(root);writeFileSync(join(root,'run.log'),'isolated ingestion test result');const evidence:ExecutionEvidence={schema_version:1,kind:'ingestion',command:['npx','tsx','scripts/qa-ingestion-admin.ts'],producer:'package.json',started_at:new Date().toISOString(),completed_at:new Date().toISOString(),exit_code:0,source_tree_sha256:before,publication:'same-publication',assertions:[{name:'scope',passed:true}],artifacts:[{path:'run.log',sha256:sha256('isolated ingestion test result')}]};assert.deepEqual(validateEvidence(evidence,root,before,'same-publication'),[]);writeFileSync(adapter,'{"items":[{"text":"different literal"}]}');const after=sourceTreeHash(root);assert.notEqual(after,before);assert.ok(validateEvidence(evidence,root,after,'same-publication').some(error=>error.includes('árvore')));writeFileSync(join(root,'data/manifests/source.json'),'{"id":"isolated-source","url":"https://example.invalid/two"}');assert.notEqual(sourceTreeHash(root),after);}finally{rmSync(root,{recursive:true,force:true});}
});
test('help não pode se passar por build, tipos ou lint executados com sucesso',()=>{
 for(const[kind,command]of [['containers',['docker','compose','build','--help']],['types',['npm','run','typecheck','--','--help']],['lint',['npm','run','lint','--','--help']],['build',['npm','run','build','--','--help']]] as const)assert.throws(()=>recordExecution(kind,['--',...command]),/execução integral/);
 const root=mkdtempSync(join(tmpdir(),'curriculos-help-'));try{writeFileSync(join(root,'Dockerfile'),'FROM example.invalid/test');writeFileSync(join(root,'help.log'),'Usage: build [OPTIONS]');const evidence:ExecutionEvidence={schema_version:1,kind:'containers',command:['docker','compose','build','--help'],producer:'Dockerfile',started_at:new Date().toISOString(),completed_at:new Date().toISOString(),exit_code:0,source_tree_sha256:sourceTreeHash(root),publication:null,assertions:[{name:'exit zero',passed:true}],artifacts:[{path:'help.log',sha256:sha256('Usage: build [OPTIONS]')}]};assert.ok(validateEvidence(evidence,root,sourceTreeHash(root),null).some(error=>error.includes('execução integral')));}finally{rmSync(root,{recursive:true,force:true});}
});
test('J11 parcial não comprova atualização global; retenção precisa de inventário, hashes e evento de base',()=>{
 const digest=sha256('isolated fixture of computed canonical records');const proof={before_count:1,after_count:1,before_sha256:digest,after_sha256:digest};
 const report={original_default:'isolated-base',publication:'isolated-candidate',source:'target-source',update_scope:{mode:'base-plus-source-update',base_publication:'isolated-base',candidate_publication:'isolated-candidate',target_source_ids:['target-source'],base_source_ids:['target-source','retained-source'],unaffected_sources:[{source_id:'retained-source',before:{items:2,source_sha256:digest,items_sha256:digest},after:{items:2,source_sha256:digest,items_sha256:digest}}],relations_excluding_target:proof,coverage_excluding_target:proof,publication_event:{id:'isolated-event',previous_id:'isolated-base',publication_id:'isolated-candidate'},actor_type:'automated',actor_id:'isolated-test-auditor',method:'SQL canonical record comparison, isolated test fixture only'}};
 assert.deepEqual(ingestionScopeErrors(report),[]);
 assert.ok(ingestionScopeErrors({...report,update_scope:{mode:'partial-candidate',global_update_verified:true}}).some(error=>error.includes('J11 global')));
 assert.ok(ingestionScopeErrors({...report,update_scope:{...report.update_scope,unaffected_sources:[]}}).some(error=>error.includes('inventário')));
 const changed=structuredClone(report);changed.update_scope.unaffected_sources[0].after.items=0;assert.ok(ingestionScopeErrors(changed).some(error=>error.includes('não preservados')));
 const stale=structuredClone(report);stale.update_scope.publication_event.previous_id='another-default';assert.ok(ingestionScopeErrors(stale).some(error=>error.includes('base efetivamente')));
 assert.ok(ingestionScopeErrors({...report,update_scope:{...report.update_scope,relations_excluding_target:{...proof,after_sha256:sha256('changed')}}}).some(error=>error.includes('relations_excluding_target')));
});
