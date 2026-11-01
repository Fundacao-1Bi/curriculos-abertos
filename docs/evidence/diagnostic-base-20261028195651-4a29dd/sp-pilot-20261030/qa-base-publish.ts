// Diagnostic-only publication of a prepared full BASE candidate on the isolated QA (localhost:3002).
// Sequential base-plus-source-update jobs through the authenticated admin API:
// enqueue -> wait -> validate -> publish, one SP Source at a time (each publication
// becomes the pinned base of the next). Temporary automated admin is deleted at the end.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import { pool } from '../../../../src/db/client';

const base = 'http://localhost:3002', origin = base;
const sources = (process.env.SP_SOURCES || 'sp-seduc156-corpo-2026,sp-seduc156-anexos-matrizes-2026,sp-educacao-digital-midiatica-2026,sp-curriculo-em-isbn,sp-curriculo-eief-isbn').split(',');
const out = process.env.SP_OUT || 'docs/evidence/diagnostic-base-20261028195651-4a29dd/sp-pilot-20261030/qa-sp-publication.json';
const password = randomBytes(30).toString('base64url'), email = `qa-sp-pilot-${randomUUID().slice(0, 8)}@example.invalid`;
const timeout = Number(process.env.SP_TIMEOUT_MS || 10_800_000);
let resumeJob = process.env.SP_RESUME_JOB || '';
const log = (event: string, detail?: unknown) => console.log(JSON.stringify({ at: new Date().toISOString(), event, ...(detail ? { detail } : {}) }));
const sleep = (ms: number) => new Promise<void>(r => setTimeout(r, ms));

async function run(args: string[], input: string) {
  const p = spawn(args[0], args.slice(1), { stdio: ['pipe', 'pipe', 'pipe'], env: process.env });
  p.stdin.end(input); let o = '', e = '';
  p.stdout.on('data', (b: Buffer) => o += b); p.stderr.on('data', (b: Buffer) => e = (e + b).slice(-3000));
  const code = await new Promise<number | null>(done => p.once('close', done));
  assert.equal(code, 0, e.replaceAll(password, '[redacted]')); return o;
}
async function request(path: string, body?: unknown, cookie?: string, expected = 200) {
  const response = await fetch(new URL(path, base), { method: body === undefined ? 'GET' : 'POST', headers: { Origin: origin, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...(cookie ? { Cookie: cookie } : {}) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(180000) });
  const json = await response.json(); assert.equal(response.status, expected, `${path}: ${JSON.stringify(json)}`); return { response, json };
}
const current = async () => (await pool.query('SELECT publication_id FROM current_publication WHERE singleton=true')).rows[0].publication_id as string;

let account: string | null = null;
const candidate = process.env.BASE_CANDIDATE!; assert(candidate);
const outBase = process.env.BASE_OUT!; assert(outBase);
const started_at = new Date().toISOString();
const original = await current();
try {
  account = JSON.parse((await run([process.execPath, '--import', 'tsx', 'scripts/admin-create.ts', '--email', email, '--role', 'administrator', '--actor-type', 'automated'], password + '\n')).trim()).id;
  const auth = await request('/api/auth/sign-in/email', { email, password });
  const cookie = auth.response.headers.getSetCookie().map(v => v.split(';')[0]).join('; '); assert(cookie);
  const preview = (await request(`/api/admin/candidates/${encodeURIComponent(candidate)}`, undefined, cookie)).json.data;
  assert.equal(preview.visibility, 'prepared');
  const validation = (await request(`/api/admin/candidates/${encodeURIComponent(candidate)}/validate`, { reason: 'Validação técnica automatizada do BASE completo com SP reconciliada (piloto diagnóstico).' }, cookie)).json.data;
  log('validated', validation);
  assert.equal(validation.valid, true);
  const published = (await request(`/api/admin/candidates/${encodeURIComponent(candidate)}/publish`, { reason: 'Piloto SP diagnóstico (QA isolado): publicação explícita do BASE completo com SP reconciliada.' }, cookie)).json.data;
  assert.equal(await current(), candidate); assert.equal(published.previous_id, original);
  await writeFile(outBase, JSON.stringify({ schema_version: 1, diagnostic_only: true, national_release_asserted: false, actor_type: 'automated', started_at, completed_at: new Date().toISOString(), original_default: original, final_default: await current(), candidate, counts: preview.counts, validation, publication_event: published.publication_event?.id, passed: true }, null, 2) + '\n');
} catch (error) {
  await writeFile(outBase, JSON.stringify({ schema_version: 1, diagnostic_only: true, started_at, failed_at: new Date().toISOString(), original_default: original, current_default: await current(), candidate, passed: false, error: error instanceof Error ? error.message : String(error) }, null, 2) + '\n');
  console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 1;
} finally {
  if (account) await pool.query('DELETE FROM "user" WHERE id=$1', [account]);
  await pool.end();
}
