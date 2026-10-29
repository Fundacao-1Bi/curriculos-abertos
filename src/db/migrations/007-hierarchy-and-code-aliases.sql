CREATE INDEX IF NOT EXISTS items_parent_idx ON items(publication_id,(payload->>'parent_id'));
CREATE OR REPLACE FUNCTION curriculum_search_aliases(input jsonb) RETURNS jsonb
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
 SELECT coalesce(jsonb_agg(public.curriculum_search_code(v)), '[]'::jsonb)
 FROM jsonb_array_elements_text(CASE WHEN jsonb_typeof(input)='array' THEN input ELSE '[]'::jsonb END) AS a(v)
$$;
-- Expression index avoids rewriting existing immutable item rows and their large text indexes.
CREATE INDEX IF NOT EXISTS items_code_aliases_gin_idx ON items USING gin(curriculum_search_aliases(payload->'code_aliases') jsonb_path_ops);
