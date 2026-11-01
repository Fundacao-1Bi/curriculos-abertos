/** Synthetic PDF text exists only in the disposable, owned integration database. */
import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { migrate } from '../scripts/migrate';
import { pool } from '../src/db/client';
import { importBundle } from '../src/domain/publication';
import type { Bundle, Learning, Source } from '../src/shared/contracts';
import { testDatabaseName } from './domain-safety';

const allowed = process.env.DOMAIN_INTEGRATION_TEST === '1';
const publication = 'test-pdf-word-search';
const source: Source = {
 id: 'test-pdf-word-source', uf: 'BR', title: 'Isolated PDF word-search fixture',
 issuer: 'Synthetic test only', official_url: 'https://example.org/test-pdf',
 artifact_url: 'https://example.org/test-pdf.pdf', stages: ['EF'], components: ['Matemática'],
 edition: 'test', document_date: null, homologation_date: null, application_period: null,
 document_type: 'test_fixture', normative_parts: ['test'], redistribution: 'Test only',
 collected_at: null, sha256: null, local_path: null, status: 'test',
};
const canonical = ['Desenvolver progres- sivamente a aprendizagem.', 'Preservar guarda-chuva e a - b.', 'Desenvolver progressivamente a aprendizagem.'];
const items: Learning[] = canonical.map((text, index) => ({
 id: `pdf-word-${index}`, curriculum_id: source.id, source_id: source.id, uf: 'BR',
 code: `TEST-PDF-${index}`, text, normalized_text: '', editorial_note: null,
 kind: 'habilidade', parent_id: null,
 positions: [{ stage: 'EF', component: 'Matemática', area: null, years: [5], year_label: '5º', age_group: null, period: null }],
 evidence: [{ source_id: source.id, page: 1, printed_page: null, section: null, excerpt: text }],
 extraction_revision: 'test',
}));
const bundle: Bundle = {
 id: publication, schema_version: '1.0.0', created_at: '2026-10-28T00:00:00Z',
 extraction_revision: 'test', mapping_revision: 'test', sources: [source], items,
 relations: [], coverage: [], changelog: [],
};

before(async () => {
 if (!allowed) return;
 const expected = testDatabaseName(process.env.DATABASE_URL);
 assert.equal((await pool.query('SELECT current_database() AS name')).rows[0]?.name, expected);
 await migrate();
 await importBundle(bundle, { makeDefault: false });
});
after(async () => { await pool.end(); });

test('PDF search joins only letter-hyphen-whitespace-letter sequences', { skip: !allowed }, async () => {
 const cases: [string | null, string | null][] = [
  ['progres- sivamente', 'progressivamente'],
  ['progres- \nsiva- \tmente', 'progressivamente'],
  ['educa- ção e avalia- ção', 'educação e avaliação'],
  ['guarda-chuva', 'guarda-chuva'],
  ['a - b; 1- 2; a- 2; 1- b', 'a - b; 1- 2; a- 2; 1- b'],
  ['pré-escola e palavra– quebrada', 'pré-escola e palavra– quebrada'],
  ['', ''], [null, null],
 ];
 for (const [input, expected] of cases) {
  const result = await pool.query('SELECT public.curriculum_join_pdf_hyphens($1::text) AS value', [input]);
  assert.equal(result.rows[0].value, expected);
 }
 const metadata = await pool.query("SELECT provolatile,proparallel,proisstrict FROM pg_catalog.pg_proc WHERE oid='public.curriculum_join_pdf_hyphens(text)'::pg_catalog.regprocedure");
 assert.deepEqual(metadata.rows[0], { provolatile: 'i', proparallel: 's', proisstrict: true });
});

test('partial PDF search indexes find auxiliary words and preserve canonical records', { skip: !allowed }, async () => {
 const result = await pool.query("SELECT id,text,normalized_text,payload->>'text' AS canonical_text FROM public.items WHERE publication_id=$1 ORDER BY id", [publication]);
 assert.deepEqual(result.rows.map(row => row.text), canonical);
 assert.deepEqual(result.rows.map(row => row.canonical_text), canonical);
 assert.match(result.rows[0].normalized_text, /progres- sivamente/);
 const predicate = "normalized_text ~ '[[:alpha:]]-[[:space:]]+[[:alpha:]]'";
 const expressions = [
  "public.curriculum_join_pdf_hyphens(normalized_text) LIKE '%progressivamente%'",
  "pg_catalog.to_tsvector('pg_catalog.portuguese'::pg_catalog.regconfig, public.curriculum_join_pdf_hyphens(normalized_text)) @@ pg_catalog.plainto_tsquery('pg_catalog.portuguese'::pg_catalog.regconfig, 'progressivamente')",
 ];
 const client = await pool.connect();
 try {
  await client.query('BEGIN');
  await client.query('SET LOCAL enable_seqscan=off');
  for (const [index, expression] of expressions.entries()) {
   const sql = `SELECT id FROM public.items WHERE publication_id=$1 AND ${predicate} AND ${expression}`;
   assert.deepEqual((await client.query(sql, [publication])).rows.map(row => row.id), ['pdf-word-0']);
   // A tiny publication is cheaper through its B-tree. Verify expression-index
   // eligibility independently of that unrelated publication selectivity.
   const plan = await client.query(`EXPLAIN (FORMAT JSON) SELECT id FROM public.items WHERE ${predicate} AND ${expression}`);
   assert.match(JSON.stringify(plan.rows), new RegExp(index === 0 ? 'items_publication_pdf_joined_text_trgm_idx' : 'items_publication_pdf_joined_text_fts_idx'));
  }
  assert.equal((await client.query(`SELECT count(*)::int AS count FROM public.items WHERE publication_id=$1 AND ${predicate}`, [publication])).rows[0].count, 1);
  await client.query('ROLLBACK');
 } catch (error) {
  await client.query('ROLLBACK');
  throw error;
 } finally { client.release(); }
 const indexes = await pool.query("SELECT indexname,indexdef FROM pg_catalog.pg_indexes WHERE schemaname='public' AND indexname IN ('items_publication_pdf_joined_text_trgm_idx','items_publication_pdf_joined_text_fts_idx') ORDER BY indexname");
 assert.equal(indexes.rows.length, 2);
 for (const row of indexes.rows) assert.match(row.indexdef, /WHERE \(normalized_text ~/);
 await migrate(); // Ledger prevents reapplying/rebuilding an already applied migration.
});
