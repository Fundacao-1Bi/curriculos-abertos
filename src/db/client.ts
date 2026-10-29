import { drizzle } from 'drizzle-orm/node-postgres';
import * as schema from './schema';
import pg from 'pg';
const globalDb = globalThis as unknown as { curriculumPool?: pg.Pool };
export const pool = globalDb.curriculumPool ?? new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  max: Number(process.env.DATABASE_POOL_SIZE ?? 12),
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 10_000,
  statement_timeout: 20_000,
});
if (process.env.NODE_ENV !== 'production') globalDb.curriculumPool = pool;
export async function ping() { const result = await pool.query('SELECT 1 AS ok'); return result.rows[0].ok === 1; }

export const db=drizzle(pool,{schema});
