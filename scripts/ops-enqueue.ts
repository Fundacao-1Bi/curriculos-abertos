import { enqueueJob } from '../src/worker/jobs';
import { pool } from '../src/db/client';
const type=process.argv[2];const source=process.argv[3];
if(!['ingest','source-check'].includes(type))throw new Error('Use ingest ou source-check.');
if(source&&!/^[a-zA-Z0-9_.:-]{1,200}$/.test(source))throw new Error('ID da fonte inválido.');
const job=await enqueueJob(type,source?{source}:{});
console.log(JSON.stringify({id:job.id,type:job.type,status:job.status}));
await pool.end();
