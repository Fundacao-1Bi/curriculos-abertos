import {after,test} from 'node:test';
import assert from 'node:assert/strict';
import {parseAgeMonths,validatePositionAge} from '../src/domain/age';
import {boundedQuery,itemFilter} from '../src/domain/service';
import {pool} from '../src/db/client';
after(()=>pool.end());
const proof={source_id:'age-test',page:3,section:'Cabeçalho etário',excerpt:'0 A 1 ANO'};
test('age range parses only bounded inclusive documented months without guessing from group labels',()=>{
 assert.deepEqual(parseAgeMonths('0-6'),{min:0,max:6});assert.deepEqual(parseAgeMonths('60'),{min:60,max:60});assert.deepEqual(parseAgeMonths('1800'),{min:1800,max:1800});
 for(const value of ['-1','6-0','1801','BEBÊS','0.5','0-6 OR true',6,''])assert.throws(()=>parseAgeMonths(value));
 assert.throws(()=>boundedQuery({age_months:'12-0'}));assert.equal(boundedQuery({age_months:'0-6'}).age_months,'0-6');
 validatePositionAge({age_group:'BEBÊS'});validatePositionAge({age_label:'0 A 1 ANO',age_min_months:0,age_max_months:12,age_evidence:[proof],age_interval_origin:'explicit_source_header_units_to_months'},'age-test');
 for(const value of [{age_min_months:0},{age_min_months:12,age_max_months:0},{age_min_months:0,age_max_months:6},{age_min_months:0,age_max_months:6,age_evidence:proof},{age_min_months:0,age_max_months:6,age_evidence:[{...proof,source_id:'other'}]},{age_min_months:0.5,age_max_months:6,age_evidence:[proof]},{age_min_months:0,age_max_months:6,age_evidence:[{...proof,page:null,section:null}]}])assert.throws(()=>validatePositionAge(value,'age-test'));
});
test('age SQL uses parameterized intersection and both original labels; unknowns require an explicit opt-in',()=>{
 const strict=itemFilter({age_months:'0-6',age_group:'  BEBÊS  '},'age-publication');assert.ok(strict.values.includes(0));assert.ok(strict.values.includes(6));assert.ok(strict.values.includes('bebes'));assert.match(strict.where,/age_label/);assert.match(strict.where,/age_min_months/);assert.match(strict.where,/age_max_months/);assert.match(strict.where,/age_evidence/);assert.doesNotMatch(strict.where,/OR \(CASE.*IS NULL/);
 const unknown=itemFilter({age_months:'0-6',include_unknown_positions:true},'age-publication');assert.match(unknown.where,/OR \(CASE.*IS NULL/);assert.match(unknown.where,/jsonb_array_length\(i.positions\)=0/);assert.ok(!unknown.values.includes('BEBÊS'));
});
