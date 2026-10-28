CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE TABLE IF NOT EXISTS publications (
 id text PRIMARY KEY, schema_version text NOT NULL, created_at timestamptz NOT NULL,
 extraction_revision text NOT NULL, mapping_revision text NOT NULL,
 sha256 text NOT NULL, item_count integer NOT NULL CHECK(item_count>=0),
 source_count integer NOT NULL CHECK(source_count>=0), relation_count integer NOT NULL CHECK(relation_count>=0),
 payload jsonb NOT NULL, imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS current_publication (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 publication_id text NOT NULL REFERENCES publications(id)
);
CREATE TABLE IF NOT EXISTS sources (
 publication_id text NOT NULL REFERENCES publications(id), id text NOT NULL,
 uf text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY(publication_id,id)
);
CREATE TABLE IF NOT EXISTS items (
 publication_id text NOT NULL REFERENCES publications(id), id text NOT NULL,
 uf text NOT NULL, curriculum_id text NOT NULL, source_id text NOT NULL,
 code text, text text NOT NULL, normalized_text text NOT NULL, kind text NOT NULL,
 positions jsonb NOT NULL, evidence jsonb NOT NULL, payload jsonb NOT NULL,
 search_vector tsvector GENERATED ALWAYS AS (to_tsvector('portuguese', normalized_text)) STORED,
 PRIMARY KEY(publication_id,id),
 FOREIGN KEY(publication_id,source_id) REFERENCES sources(publication_id,id)
);
CREATE TABLE IF NOT EXISTS relations (
 publication_id text NOT NULL REFERENCES publications(id), id text NOT NULL,
 relation_type text NOT NULL, origin text NOT NULL,
 technical_validation_status text NOT NULL, pedagogical_review_status text NOT NULL,
 publication_status text NOT NULL, payload jsonb NOT NULL, PRIMARY KEY(publication_id,id)
);
CREATE TABLE IF NOT EXISTS relation_members (
 publication_id text NOT NULL, relation_id text NOT NULL, item_id text NOT NULL,
 role text NOT NULL CHECK(role IN ('source','target')), scope text NOT NULL,
 PRIMARY KEY(publication_id,relation_id,item_id,role),
 FOREIGN KEY(publication_id,relation_id) REFERENCES relations(publication_id,id),
 FOREIGN KEY(publication_id,item_id) REFERENCES items(publication_id,id)
);
CREATE TABLE IF NOT EXISTS publication_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 publication_id text NOT NULL REFERENCES publications(id), previous_id text,
 actor_id text NOT NULL, actor_type text NOT NULL CHECK(actor_type IN ('human','automated')),
 reason text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS items_uf_idx ON items(publication_id,uf);
CREATE INDEX IF NOT EXISTS items_code_idx ON items(publication_id,code);
CREATE INDEX IF NOT EXISTS items_curriculum_idx ON items(publication_id,curriculum_id);
CREATE INDEX IF NOT EXISTS items_search_idx ON items USING gin(search_vector);
CREATE INDEX IF NOT EXISTS items_positions_idx ON items USING gin(positions);
CREATE INDEX IF NOT EXISTS members_item_idx ON relation_members(publication_id,item_id);
CREATE INDEX IF NOT EXISTS sources_uf_idx ON sources(publication_id,uf);
CREATE OR REPLACE FUNCTION protect_published_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Published snapshots are immutable; import a new publication'; END $$;
CREATE TRIGGER publications_immutable BEFORE UPDATE OR DELETE ON publications FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
CREATE TRIGGER sources_immutable BEFORE UPDATE OR DELETE ON sources FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
CREATE TRIGGER items_immutable BEFORE UPDATE OR DELETE ON items FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
CREATE TRIGGER relations_immutable BEFORE UPDATE OR DELETE ON relations FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
CREATE TRIGGER members_immutable BEFORE UPDATE OR DELETE ON relation_members FOR EACH ROW EXECUTE FUNCTION protect_published_snapshot();
