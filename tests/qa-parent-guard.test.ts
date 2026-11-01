import test from 'node:test';
import assert from 'node:assert/strict';
import {watchQaParent} from '../scripts/qa-parent-guard';

test('a live QA owner does not contain work, and stopping disables checks',async()=>{
 let checks=0,contained=0,failed=0;
 const guard=watchQaParent({assertParent:()=>{checks++;},containOwnedWork:async()=>{contained++;},onFailure:()=>{failed++;},intervalMs:10000});
 guard.check();guard.check();await guard.stop();guard.check();
 assert.equal(checks,2);assert.equal(contained,0);assert.equal(failed,0);assert.equal(guard.failed(),false);
});

test('loss of authenticated parent contains only the supplied owned work before child termination',async()=>{
 const events:string[]=[];
 const guard=watchQaParent({assertParent:()=>{throw Error('owner gone');},containOwnedWork:async()=>{events.push('owned-work-contained');},onFailure:()=>{events.push('child-exit');},intervalMs:10000});
 guard.check();guard.check();await guard.stop();
 assert.deepEqual(events,['owned-work-contained','child-exit']);assert.equal(guard.failed(),true);
});

test('an unavailable containment connection still fails the child instead of resuming new work',async()=>{
 let failed=0;
 const guard=watchQaParent({assertParent:()=>{throw Error('owner gone');},containOwnedWork:async()=>{throw Error('control connection failed');},onFailure:()=>{failed++;},intervalMs:10000});
 guard.check();await guard.stop();assert.equal(failed,1);assert.equal(guard.failed(),true);
});
