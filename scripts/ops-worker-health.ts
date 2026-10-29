import { pool } from '../src/db/client';
try {const result=await pool.query("SELECT count(*)::int AS count FROM worker_heartbeats WHERE seen_at>now()-interval '45 seconds'");process.exitCode=result.rows[0].count>0?0:1;}catch{process.exitCode=1;}finally{await pool.end();}
