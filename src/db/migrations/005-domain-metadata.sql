-- Small immutable derived tables avoid detoasting the national JSONB snapshot on public metadata reads.
CREATE TABLE IF NOT EXISTS publication_metadata (
 publication_id text PRIMARY KEY REFERENCES publications(id),
 changelog jsonb NOT NULL,
 payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS publication_coverage (
 publication_id text NOT NULL REFERENCES publications(id),
 row_index integer NOT NULL,
 uf text, stage text, component text,
 payload jsonb NOT NULL,
 PRIMARY KEY(publication_id,row_index)
);
INSERT INTO publication_metadata(publication_id,changelog,payload)
 SELECT id,coalesce(payload->'changelog','[]'::jsonb),jsonb_build_object(
 'publication_kind',payload->'publication_kind','coverage_statement',payload->'coverage_statement','national_release_ready',payload->'national_release_ready')
 FROM publications ON CONFLICT DO NOTHING;
INSERT INTO publication_coverage(publication_id,row_index,uf,stage,component,payload)
 SELECT p.id,c.ordinality::integer,c.value->>'uf',c.value->>'stage',c.value->>'component',c.value
 FROM publications p CROSS JOIN LATERAL jsonb_array_elements(p.payload->'coverage') WITH ORDINALITY AS c(value,ordinality)
 ON CONFLICT DO NOTHING;
CREATE INDEX IF NOT EXISTS publication_coverage_scope_idx ON publication_coverage(publication_id,uf,stage,component);
CREATE TRIGGER publication_metadata_immutable BEFORE UPDATE OR DELETE ON publication_metadata FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
CREATE TRIGGER publication_coverage_immutable BEFORE UPDATE OR DELETE ON publication_coverage FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
