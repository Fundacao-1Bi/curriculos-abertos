import {test} from 'node:test';
import assert from 'node:assert/strict';
import {sourceDate} from '../src/shared/dates';

test('partial source dates never acquire an invented month or day',()=>{
 assert.equal(sourceDate('2018'),'2018');assert.equal(sourceDate('2023'),'2023');assert.equal(sourceDate('2021-12'),'12/2021');assert.equal(sourceDate('2022-03'),'03/2022');
 assert.equal(sourceDate('2025-02-30'),'2025-02-30');assert.equal(sourceDate('2026-13'),'2026-13');assert.equal(sourceDate('data não confirmada'),'data não confirmada');
});
test('calendar dates remain the same under different execution timezones',()=>{
 const previous=process.env.TZ;
 try{for(const timezone of ['UTC','America/Sao_Paulo','Pacific/Honolulu']){process.env.TZ=timezone;assert.equal(sourceDate('2026-10-28'),'28/10/2026');assert.equal(sourceDate('2024-02-29'),'29/02/2024');}}
 finally{if(previous===undefined)delete process.env.TZ;else process.env.TZ=previous;}
 assert.equal(sourceDate('2026-10-28T01:00:00Z'),'27/10/2026');assert.equal(sourceDate(null),'Data não informada');
});
