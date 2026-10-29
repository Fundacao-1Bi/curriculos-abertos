import assert from 'node:assert/strict';
import { pool } from '../src/db/client';
const base=process.env.VERIFY_URL || process.env.PUBLIC_URL || 'http://localhost:3000';
const results:Record<string,unknown>[]=[];
for(const route of ['/api/health','/api/ready']) {const response=await fetch(new URL(route,base));const body=await response.json();assert.equal(response.status,200,`${route} deve estar pronto`);results.push({route,status:response.status,result:body});}
for(const route of ['/api/admin/overview','/api/metrics']){const response=await fetch(new URL(route,base));assert.equal(response.status,401,`${route} deve exigir sessão`);results.push({route,status:response.status});}
const worker=await pool.query("SELECT count(*)::int count FROM worker_heartbeats WHERE seen_at>now()-interval '45 seconds'");assert(worker.rows[0].count>0,'Worker precisa estar vivo.');
console.log(JSON.stringify({event:'ops_smoke_passed',at:new Date().toISOString(),results,worker_alive:true}));
await pool.end();
