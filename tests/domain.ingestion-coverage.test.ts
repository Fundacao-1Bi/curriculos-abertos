import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mergeSourceAttributedCoverageValues } from '../src/domain/ingestion-coverage';
import { DomainError } from '../src/domain/errors';

const part=(source_id:string,part:string)=>({source_id,part,edition:'test-edition'});
const domainError=(error:unknown)=>error instanceof DomainError&&error.status===422&&error.code==='INGESTION_COVERAGE_AMBIGUOUS';

test('coverage inventory retains every outside-source part and replaces only explicitly targeted entries',()=>{
 const outside=part('source-outside','Unidade 1'),old=part('source-target','Texto antigo'),updated=part('source-target','Texto novo');
 const base={source_ids:['source-outside','source-target'],expected_parts:[outside,old],expected_parts_count:2};
 const raw={source_ids:['source-target','source-foreign'],expected_parts:[updated,part('source-foreign','Não importar')],expected_parts_count:2};
 const originalBase=JSON.stringify(base),originalRaw=JSON.stringify(raw);
 const merged=mergeSourceAttributedCoverageValues([base],[raw],'expected_parts',['source-target']);
 assert.deepEqual(merged,[outside,updated]);assert.equal(merged[0],outside);assert.equal(merged[1],updated);
 assert.equal(JSON.stringify(base),originalBase);assert.equal(JSON.stringify(raw),originalRaw);
});

test('coverage processed/reconciled parts preserve attribution and deterministic first occurrence',()=>{
 for(const key of ['processed_parts','reconciled_parts']){
  const outside=part('untouched','Parte preservada'),target=part('updated','Parte substituída');
  const merged=mergeSourceAttributedCoverageValues([{source_ids:['untouched','updated'],[key]:[outside,part('updated','Antiga')]}],[{source_ids:['updated'],[key]:[target,{edition:'test-edition',part:'Parte substituída',source_id:'updated'}]}],key,['updated']);
  assert.deepEqual(merged,[outside,target]);
 }
});

test('legacy mixed aggregate or unattributed inventories fail explicitly without dropping outside parts',()=>{
 for(const legacy of [3,undefined]){
  const base={source_ids:['outside','target'],expected_parts:legacy,expected_parts_count:3};
  assert.throws(()=>mergeSourceAttributedCoverageValues([base],[],'expected_parts',['target']),domainError);
 }
 assert.throws(()=>mergeSourceAttributedCoverageValues([{source_ids:['outside','target'],expected_parts:[{part:'sem atribuição'}]}],[],'expected_parts',['target']),domainError);
 assert.throws(()=>mergeSourceAttributedCoverageValues([],[{source_ids:['target'],expected_parts:[{part:'sem atribuição'}]}],'expected_parts',['target']),domainError);
 assert.throws(()=>mergeSourceAttributedCoverageValues([{source_ids:['outside'],expected_parts:[part('outside','Real')],expected_parts_count:2}],[],'expected_parts',['target']),domainError);
 assert.deepEqual(mergeSourceAttributedCoverageValues([{source_ids:['target'],expected_parts:3}],[],'expected_parts',['target']),[]);
 assert.deepEqual(mergeSourceAttributedCoverageValues([{source_ids:['outside'],expected_parts:0}],[],'expected_parts',['target']),[]);
});

test('critical errors retain only attributable outside-base and target-raw diagnostics',()=>{
 const outside={source_id:'outside',error:'Erro preservado'},updated={source_id:'target',error:'Erro atual'};
 const result=mergeSourceAttributedCoverageValues([{source_ids:['outside','target'],critical_errors:[outside,{source_id:'target',error:'Erro antigo'}]}],[{source_ids:['target','foreign'],critical_errors:[updated,{source_id:'foreign',error:'Fora do escopo'}]}],'critical_errors',['target']);
 assert.deepEqual(result,[outside,updated]);
 assert.deepEqual(mergeSourceAttributedCoverageValues([{source_ids:['outside'],critical_errors:['Diagnóstico global desta fonte']}],[{source_ids:['target'],critical_errors:['Novo diagnóstico']}],'critical_errors',['target']),['Diagnóstico global desta fonte','Novo diagnóstico']);
 assert.throws(()=>mergeSourceAttributedCoverageValues([{source_ids:['outside','target'],critical_errors:['Diagnóstico sem atribuição']}],[],'critical_errors',['target']),domainError);
});

test('coverage helpers never fabricate inventory entries from positive raw aggregates',()=>{
 assert.throws(()=>mergeSourceAttributedCoverageValues([],[{source_ids:['target'],processed_parts:4}],'processed_parts',['target']),domainError);
 assert.throws(()=>mergeSourceAttributedCoverageValues([],[{source_ids:['target'],processed_parts_count:1}],'processed_parts',['target']),domainError);
 assert.throws(()=>mergeSourceAttributedCoverageValues([{source_ids:[],expected_parts:[{part:'Origem desconhecida'}]}],[],'expected_parts',['target']),domainError);
 assert.deepEqual(mergeSourceAttributedCoverageValues([],[{source_ids:['target'],processed_parts:[],processed_parts_count:0}],'processed_parts',['target']),[]);
});
