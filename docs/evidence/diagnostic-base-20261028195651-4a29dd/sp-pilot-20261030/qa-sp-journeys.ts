// Diagnostic-only SP journeys on the isolated QA (localhost:3002) after the SP pilot publication:
// API, MCP (HTTP), export and portal, all filtered to SP and pinned to the final publication.
// Read-only except for public export jobs. Writes only to the SP pilot evidence folder.
import assert from 'node:assert/strict';
import { createReadStream } from 'node:fs';
import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createGunzip } from 'node:zlib';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { downloadAndHash, validatePublishedJsonFile, validatePublishedCsvFile } from '../../scripts/api-export-stream';

const base = 'http://localhost:3002';
const expectedPublication = process.env.SP_PUBLICATION || 'ca-update-45e4555b35896d3d3b1fec188bf8cb80';
const SOURCES = ['sp-seduc156-corpo-2026', 'sp-seduc156-anexos-matrizes-2026', 'sp-educacao-digital-midiatica-2026', 'sp-curriculo-em-isbn', 'sp-curriculo-eief-isbn'];
const dir = 'docs/evidence/diagnostic-base-20261028195651-4a29dd/sp-pilot-20261030';
const deltaBundle = 'data/bundles/ca-49197c6e9f80e2646e61';
const report: Record<string, any> = { schema_version: 1, diagnostic_only: true, national_release_asserted: false, base, started_at: new Date().toISOString(), journeys: {}, findings: [] as string[] };
const j = report.journeys;
const enc = encodeURIComponent;
let publication = expectedPublication;
const pin = (p: string) => `${p}${p.includes('?') ? '&' : '?'}publication=${enc(publication)}`;
async function raw(path: string, expected = 200, init?: RequestInit) {
  const r = await fetch(`${base}/api/v1/${path}`, init); const t = await r.text();
  assert.equal(r.status, expected, `${path}: HTTP ${r.status} ${t.slice(0, 600)}`); return { r, t };
}
const api = async (path: string, expected = 200, init?: RequestInit) => JSON.parse((await raw(path, expected, init)).t);
const post = (body: unknown) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
async function step(name: string, fn: () => Promise<unknown>) {
  const t0 = Date.now();
  try { j[name] = { passed: true, ...(await fn() as object), ms: Date.now() - t0 }; }
  catch (e) { j[name] = { passed: false, error: e instanceof Error ? e.message : String(e), ms: Date.now() - t0 }; }
  console.log(JSON.stringify({ step: name, passed: j[name].passed, ...(j[name].error ? { error: j[name].error } : {}) }));
}

async function deltaSpItems() {
  // Bundle parts are byte-chunked: a JSONL line can continue into the next part.
  const ids = new Set<string>(); let rest = '';
  for (const f of (await readdir(deltaBundle)).filter(f => /^items-\d+\.jsonl\.gz$/.test(f)).sort())
    for await (const chunk of createReadStream(`${deltaBundle}/${f}`).pipe(createGunzip())) {
      const lines = (rest + chunk.toString('utf8')).split('\n'); rest = lines.pop()!;
      for (const line of lines) if (line.trim()) { const it = JSON.parse(line); if (it.uf === 'SP') ids.add(it.id); }
    }
  if (rest.trim()) { const it = JSON.parse(rest); if (it.uf === 'SP') ids.add(it.id); }
  return ids;
}

async function sliceId(path: string) {
  // Filtered JSON exports carry their own derived id (<publication>-slice-<hash>) plus parent_publication.
  let head = '', parent = false, tail = '';
  for await (const c of createReadStream(path, { encoding: 'utf8' })) {
    if (head.length < 4096) head += c; const w = tail + c; if (w.includes(`"parent_publication":"${publication}"`)) parent = true; tail = w.slice(-200);
  }
  const m = head.match(/^\{"id":"([^"]+)"/); assert.ok(m && m[1].startsWith(`${publication}-slice-`), 'Exportação filtrada sem id de recorte.');
  assert.ok(parent, 'Exportação filtrada sem parent_publication.'); return m[1];
}

const samples = JSON.parse(await readFile('var/jobs/source-delta-sp-20261030-samples.json', 'utf8')).samples as { item_id: string; source_id: string; code?: string; page: number; stage: string }[];
const deltaCoverage = (JSON.parse(await readFile('var/jobs/source-delta-sp-20261030-coverage.json', 'utf8')).coverage as any[]).filter(r => r.uf === 'SP');
let spTotal = 0, firstSp: any, curricula: any[] = [];

await step('api_publication', async () => {
  const v = await api('publicacoes'); assert.equal(v.publication, expectedPublication, 'Publicação padrão do QA deve ser a final do piloto SP.');
  const row = v.data.find((r: any) => r.id === publication); assert.ok(row);
  const ufs = await api(pin('ufs')); const sp = ufs.data.find((r: any) => r.uf === 'SP'); assert.ok(sp, 'UF SP ausente');
  return { publication, source_count: row.source_count, relation_count: row.relation_count, uf_row: sp };
});
await step('api_sources', async () => {
  const s = await api(pin('fontes?uf=SP')); const ids = s.data.map((r: any) => r.id).sort();
  assert.deepEqual(ids, [...SOURCES].sort());
  for (const id of SOURCES) { const one = await api(pin(`fontes/${enc(id)}`)); assert.equal(one.data.id, id); assert.equal(one.data.uf, 'SP'); }
  return { sources: ids };
});
await step('api_coverage', async () => {
  const c = await api(pin('cobertura?uf=SP')); const key = (r: any) => JSON.stringify([r.stage ?? null, r.component ?? null]);
  const qa = new Map(c.data.map((r: any) => [key(r), r])); const mismatches: string[] = [];
  for (const d of deltaCoverage) { const q: any = qa.get(key(d)); if (!q) mismatches.push(`ausente ${key(d)}`); else if (q.item_count !== d.item_count) mismatches.push(`${key(d)} ${q.item_count}!=${d.item_count}`); }
  const extra = c.data.filter((r: any) => !deltaCoverage.some(d => key(d) === key(r)));
  for (const r of extra) assert.equal(r.item_count, 0, `Recorte extra com itens: ${key(r)}`);
  assert.deepEqual(mismatches, []);
  const ready = c.data.filter((r: any) => r.ready).length;
  if (ready === 0) report.findings.push(`Cobertura SP publicada no QA: 0/${c.data.length} recortes ready (pending_revalidation_after_source_update, imposto por mergeIngestionCoverage). O recibo delta no host tem ${deltaCoverage.filter(r => r.ready).length}/${deltaCoverage.length} ready.`);
  return { rows: c.data.length, rows_matching_delta: deltaCoverage.length, extra_empty_rows: extra.map(key), ready_rows: ready, delta_ready_rows: deltaCoverage.filter(r => r.ready).length, items_in_scopes: c.data.reduce((a: number, r: any) => a + r.item_count, 0), pending: [...new Set(c.data.flatMap((r: any) => r.pending))] };
});
await step('api_learnings', async () => {
  const all = await api(pin('aprendizagens?uf=SP&limit=1')); spTotal = all.total; firstSp = all.data[0];
  const perSource: Record<string, number> = {}; for (const id of SOURCES) perSource[id] = (await api(pin(`aprendizagens?uf=SP&source_id=${enc(id)}&limit=1`))).total;
  const perStage: Record<string, number> = {}; for (const s of ['EI', 'EF', 'EM']) perStage[s] = (await api(pin(`aprendizagens?uf=SP&stage=${s}&limit=1`))).total;
  for (const s of ['EI', 'EF', 'EM']) assert.ok(perStage[s] > 0, `Etapa ${s} sem itens SP`);
  const delta = await deltaSpItems();
  const sum = Object.values(perSource).reduce((a, b) => a + b, 0);
  assert.equal(sum, spTotal, 'Soma por fonte deve igualar o total SP.');
  assert.equal(spTotal, delta.size, `Total SP no QA (${spTotal}) deve igualar os itens SP do artefato delta (${delta.size}).`);
  // Paginação estável sem duplicatas.
  const p1 = await api(pin('aprendizagens?uf=SP&limit=100')), p2 = await api(pin('aprendizagens?uf=SP&limit=100&page=2'));
  const s1 = new Set(p1.data.map((r: any) => r.id)); for (const r of p2.data) assert.ok(!s1.has(r.id));
  for (const r of [...p1.data, ...p2.data]) { assert.equal(r.uf, 'SP'); assert.ok(delta.has(r.id), `Item fora do artefato delta: ${r.id}`); assert.ok(r.evidence?.length); }
  return { total: spTotal, delta_artifact_sp_items: delta.size, per_source: perSource, per_stage: perStage };
});
await step('api_samples_157', async () => {
  const found: string[] = [], problems: string[] = [];
  for (let i = 0; i < samples.length; i += 100) {
    const chunk = samples.slice(i, i + 100); const b = await api('aprendizagens/consulta-lote', 200, post({ publication, ids: chunk.map(s => s.item_id) }));
    b.data.forEach((row: any, k: number) => {
      const s = chunk[k]; if (row.status !== 'found') { problems.push(`${s.item_id}: ${row.status}`); return; }
      if (row.item.uf !== 'SP' || row.item.source_id !== s.source_id || (s.code && row.item.code !== s.code)) problems.push(`${s.item_id}: atributos divergentes`);
      else if (!row.item.evidence?.some((e: any) => e.page === s.page || e.page_start <= s.page && s.page <= (e.page_end ?? e.page_start))) problems.push(`${s.item_id}: página ${s.page} ausente da evidência`);
      else found.push(s.item_id);
    });
  }
  assert.deepEqual(problems, []); return { samples: samples.length, found: found.length };
});
await step('api_curricula_structure', async () => {
  const c = await api(pin('curriculos?uf=SP')); curricula = c.data; assert.ok(curricula.length > 0);
  const out: any[] = [];
  for (const cur of curricula) { const s = await api(pin(`curriculos/${enc(cur.id)}/estrutura`)); assert.equal(s.hierarchy.total, s.hierarchy.nodes.length); out.push({ id: cur.id, nodes: s.hierarchy.total }); }
  return { curricula: out };
});
await step('api_compare_sp_pe', async () => {
  const c = await api('comparacoes', 200, post({ publication, ufs: ['SP', 'PE'], limit: 5 }));
  const sp = c.data.columns?.find((col: any) => col.uf === 'SP') ?? c.data.columns?.[0]; assert.ok(sp && sp.total > 0, 'Coluna SP vazia');
  return { columns: c.data.columns.map((col: any) => ({ uf: col.uf, total: col.total })) };
});

await step('mcp_http', async () => {
  const client = new Client({ name: 'sp-pilot-journey', version: '0.1.0' }); await client.connect(new StreamableHTTPClientTransport(new URL('/mcp', base)));
  try {
    const call = async (name: string, args: Record<string, unknown>) => { const r = await client.callTool({ name, arguments: args }); assert.ok(!r.isError, `${name}: ${JSON.stringify(r.content).slice(0, 400)}`); return r.structuredContent as any; };
    const checks: string[] = [];
    assert.deepEqual(await call('consultar_fontes', { publication, uf: 'SP' }), await api(pin('fontes?uf=SP'))); checks.push('consultar_fontes=API');
    assert.deepEqual(await call('consultar_cobertura', { publication, uf: 'SP' }), await api(pin('cobertura?uf=SP'))); checks.push('consultar_cobertura=API');
    assert.deepEqual(await call('listar_curriculos', { publication, uf: 'SP' }), await api(pin('curriculos?uf=SP'))); checks.push('listar_curriculos=API');
    const s = await call('buscar_aprendizagens', { publication, uf: 'SP', limit: 5 }); assert.equal(s.total, spTotal); assert.deepEqual(s.data, (await api(pin('aprendizagens?uf=SP&limit=5'))).data); checks.push('buscar_aprendizagens=API');
    for (const st of ['EI', 'EF', 'EM']) { const r = await call('buscar_aprendizagens', { publication, uf: 'SP', stage: st, limit: 1 }); assert.ok(r.total > 0); } checks.push('buscar_por_etapa');
    const ids = samples.slice(0, 20).map(x => x.item_id); const b = await call('consultar_aprendizagens', { publication, ids });
    assert.ok(b.data.every((r: any) => r.status === 'found')); checks.push('consultar_aprendizagens_20_amostras');
    const cmp = await call('comparar_curriculos', { publication, ufs: ['SP', 'PE'], limit: 2 }); assert.deepEqual(cmp, await api('comparacoes', 200, post({ publication, ufs: ['SP', 'PE'], limit: 2 }))); checks.push('comparar_curriculos=API');
    return { checks };
  } finally { await client.close(); }
});

async function exportRun(format: 'json' | 'csv', extra: Record<string, unknown>) {
  const job = await api('exportacoes', 202, post({ publication, format, ...extra })); let st = job;
  for (let i = 0; i < 900; i++) { st = await api(`exportacoes/${job.id}`); if (st.status === 'succeeded') break; if (st.status === 'failed') throw new Error(`Exportação ${job.id} falhou`); await new Promise(r => setTimeout(r, 2000)); }
  assert.equal(st.status, 'succeeded'); assert.equal(st.publication, publication);
  const { r } = await (async () => { const r = await fetch(`${base}/api/v1/exportacoes/${job.id}/arquivo`); assert.equal(r.status, 200); return { r }; })();
  assert.equal(r.headers.get('x-data-publication'), publication);
  const saved = await downloadAndHash(r, `var/qa-downloads/sp-pilot-${job.id}.${format}`); assert.equal(saved.sha256, st.sha256); assert.equal(saved.bytes, st.size);
  return { job: job.id, record_count: st.record_count, saved };
}
await step('export_sp_json_csv', async () => {
  const sample = { id: firstSp.id, text: firstSp.text, evidence: firstSp.evidence };
  const js = await exportRun('json', { uf: 'SP' }); const jid = await sliceId(js.saved.path);
  const jsum = await validatePublishedJsonFile(js.saved.path, { publication: jid, sample });
  // CSV contract: manifest row is keyed by the parent publication and carries matched/support counts.
  const cs = await exportRun('csv', { uf: 'SP' });
  const csum = await validatePublishedCsvFile(cs.saved.path, { publication, sample });
  assert.equal(Number(js.record_count), spTotal, `Recorte SP deve casar ${spTotal} itens.`); assert.equal(Number(cs.record_count), spTotal);
  assert.ok(jsum.items >= spTotal, 'Itens exportados (casados + suporte) não podem ser menos que os casados.'); assert.equal(csum.items, jsum.items);
  assert.equal(csum.relations, jsum.relations); assert.equal(csum.sources, jsum.sources);
  return { slice_id: jid, matched_items: spTotal, json: { ...js, summary: jsum }, csv: { ...cs, summary: csum } };
});
await step('export_comparison_sp_pe', async () => {
  const x = await exportRun('json', { view: 'comparison', ufs: ['SP', 'PE'] }); const payload = JSON.parse(await readFile(x.saved.path, 'utf8'));
  assert.equal(payload.publication, publication); for (const col of payload.data.columns) assert.equal(col.items.length, col.total);
  return { job: x.job, columns: payload.data.columns.map((c: any) => ({ uf: c.uf, total: c.total })) };
});

await step('portal_pages', async () => {
  const sampleItem = samples[0].item_id;
  const pages: [string, RegExp[]][] = [
    ['/', [/Curr[ií]culos/i]],
    ['/ufs/SP', [/São Paulo/]],
    ['/buscar?uf=SP', [/São Paulo|SP/]],
    ['/fontes?uf=SP', [/Currículo Paulista/]],
    ...curricula.map(c => [`/curriculos/${enc(c.id)}`, [/São Paulo|Paulista/]] as [string, RegExp[]]),
    [`/aprendizagens/${enc(sampleItem)}`, [samples[0].code ? new RegExp(samples[0].code) : /SP/]],
    ['/comparar?uf1=SP&uf2=PE', [/São Paulo|SP/]],
    ['/downloads', [/xport|Download/i]],
  ];
  const out: any[] = [];
  for (const [path, patterns] of pages) {
    const r = await fetch(base + path); const html = await r.text();
    assert.equal(r.status, 200, `${path}: HTTP ${r.status}`);
    for (const p of patterns) assert.match(html, p, `${path} sem ${p}`);
    out.push({ path, status: r.status, bytes: html.length, has_publication: html.includes(publication) });
  }
  return { pages: out };
});

report.finished_at = new Date().toISOString();
report.passed = Object.values(j).every((s: any) => s.passed);
await writeFile(`${dir}/qa-sp-journeys.json`, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ passed: report.passed, findings: report.findings }));
if (!report.passed) process.exitCode = 1;
