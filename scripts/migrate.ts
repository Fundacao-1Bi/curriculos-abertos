import { readdir, readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { pool } from '../src/db/client';
export async function migrate() {
  const client=await pool.connect();
  try {
    await client.query('SELECT pg_advisory_lock(918273645)');
    await client.query('CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, sha256 text NOT NULL, executed_at timestamptz NOT NULL DEFAULT now())');
    for (const name of (await readdir(resolve('src/db/migrations'))).filter(n=>n.endsWith('.sql')).sort()) {
      const sql=await readFile(resolve('src/db/migrations',name),'utf8');
      const sha256=createHash('sha256').update(sql).digest('hex');
      const previous=await client.query('SELECT sha256 FROM schema_migrations WHERE name=$1',[name]);
      if(previous.rowCount) {if(previous.rows[0].sha256!==sha256) throw new Error(`Migration altered: ${name}`); continue;}
      await client.query('BEGIN');
      try {await client.query(sql);await client.query('INSERT INTO schema_migrations(name,sha256) VALUES($1,$2)',[name,sha256]);await client.query('COMMIT'); console.log(JSON.stringify({event:'migration_applied',name,sha256}));}
      catch(error) {await client.query('ROLLBACK');throw error;}
    }
  } finally {await client.query('SELECT pg_advisory_unlock(918273645)');client.release();}
}
if(process.argv[1] && import.meta.url===pathToFileURL(resolve(process.argv[1])).href) {
 migrate().catch(e=>{console.error(e.message);process.exitCode=1;}).finally(()=>pool.end());
}
