// Diagnostic-only SP pilot publication on the isolated QA (localhost:3002).
// Sequential base-plus-source-update jobs through the authenticated admin API:
// enqueue -> wait -> validate -> publish, one SP Source at a time (each publication
// becomes the pinned base of the next). Temporary automated admin is deleted at the end.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import { pool } from '../../src/db/client';

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
const steps: unknown[] = [];
const started_at = new Date().toISOString();
const original = await current();
try {
  account = JSON.parse((await run([process.execPath, '--import', 'tsx', 'scripts/admin-create.ts', '--email', email, '--role', 'administrator', '--actor-type', 'automated'], password + '\n')).trim()).id;
  const auth = await request('/api/auth/sign-in/email', { email, password });
  const cookie = auth.response.headers.getSetCookie().map(v => v.split(';')[0]).join('; '); assert(cookie);
  log('temporary_automated_administrator_logged_in');
  for (const source of sources) {
    const before = await current();
    let queued: any;
    if (resumeJob) {
      queued = (await pool.query('SELECT id,payload FROM jobs WHERE id=$1', [resumeJob])).rows[0]; resumeJob = '';
      assert.equal(queued.payload.base_publication, before); assert.deepEqual(queued.payload.target_sources, [source]);
      log('resumed_existing_job', { source, job_id: queued.id, base_publication: before });
    } else {
      queued = (await request('/api/admin/jobs', { type: 'ingest', source, cached_only: process.env.SP_CACHED_ONLY === 'true' }, cookie)).json.data;
      assert.equal(queued.payload.base_publication, before); assert.deepEqual(queued.payload.target_sources, [source]);
      log('enqueued', { source, job_id: queued.id, base_publication: before });
    }
    const deadline = Date.now() + timeout; let job: any, lastStage = '';
    for (;;) {
      job = (await pool.query('SELECT id,status,result,progress,error,attempts FROM jobs WHERE id=$1', [queued.id])).rows[0];
      const stage = `${job.status}:${job.progress?.stage ?? ''}`; if (stage !== lastStage) { log('progress', { source, stage }); lastStage = stage; }
      if (['succeeded', 'failed', 'cancelled'].includes(job.status)) break;
      assert(Date.now() < deadline, `job ${queued.id} exceeded ${timeout} ms`); await sleep(10000);
    }
    assert.equal(job.status, 'succeeded', job.error || 'job did not succeed');
    const publication = job.result.publication as string;
    const preview = (await request(`/api/admin/candidates/${encodeURIComponent(publication)}`, undefined, cookie)).json.data;
    assert.equal(preview.visibility, 'prepared'); assert(preview.sources.some((r: { id: string }) => r.id === source));
    const validation = (await request(`/api/admin/candidates/${encodeURIComponent(publication)}/validate`, { reason: `Validação técnica automatizada do piloto SP: ${source}.` }, cookie)).json.data;
    assert.equal(validation.valid, true); assert.equal(validation.global_update_verified, true);
    const published = (await request(`/api/admin/candidates/${encodeURIComponent(publication)}/publish`, { reason: `Piloto SP diagnóstico (QA isolado): publicação explícita da atualização de ${source}.` }, cookie)).json.data;
    assert.equal(await current(), publication); assert.equal(published.previous_id, before);
    const step = { source, job_id: job.id, attempts: job.attempts, base_publication: before, publication, raw_receipt: job.result.raw_receipt?.publication, artifact_sha256: job.result.artifact_sha256, counts: preview.counts, validation: { valid: validation.valid, global_update_verified: validation.global_update_verified, human_pedagogical_approval: validation.human_pedagogical_approval }, publication_event: published.publication_event?.id };
    steps.push(step); log('published', step);
  }
  await writeFile(out, JSON.stringify({ schema_version: 1, diagnostic_only: true, national_release_asserted: false, actor_type: 'automated', started_at, completed_at: new Date().toISOString(), original_default: original, final_default: await current(), steps, passed: true }, null, 2) + '\n');
} catch (error) {
  await writeFile(out, JSON.stringify({ schema_version: 1, diagnostic_only: true, started_at, failed_at: new Date().toISOString(), original_default: original, current_default: await current(), steps, passed: false, error: error instanceof Error ? error.message : String(error) }, null, 2) + '\n');
  console.error(error instanceof Error ? error.message : String(error)); process.exitCode = 1;
} finally {
  if (account) await pool.query('DELETE FROM "user" WHERE id=$1', [account]);
  await pool.end();
}
