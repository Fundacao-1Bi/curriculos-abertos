-- Mutable, audited exposure lifecycle is separate from immutable snapshot content.
CREATE TABLE publication_visibility (
 publication_id text PRIMARY KEY REFERENCES publications(id),
 status text NOT NULL DEFAULT 'prepared' CHECK(status IN ('prepared','published')),
 published_at timestamptz,
 actor_id text,
 actor_type text CHECK(actor_type IN ('human','automated')),
 evidence text NOT NULL DEFAULT 'prepared_snapshot',
 CHECK((status='prepared' AND published_at IS NULL) OR (status='published' AND published_at IS NOT NULL AND actor_id IS NOT NULL AND actor_type IS NOT NULL))
);
INSERT INTO publication_visibility(publication_id,status,published_at,actor_id,actor_type,evidence)
 SELECT p.id,
 CASE WHEN selected.id IS NOT NULL OR previous.id IS NOT NULL OR current.publication_id IS NOT NULL THEN 'published' ELSE 'prepared' END,
 CASE WHEN selected.id IS NOT NULL THEN selected.created_at WHEN previous.id IS NOT NULL OR current.publication_id IS NOT NULL THEN now() ELSE NULL END,
 CASE WHEN selected.id IS NOT NULL THEN selected.actor_id WHEN previous.id IS NOT NULL OR current.publication_id IS NOT NULL THEN 'visibility-migration' ELSE NULL END,
 CASE WHEN selected.id IS NOT NULL THEN selected.actor_type WHEN previous.id IS NOT NULL OR current.publication_id IS NOT NULL THEN 'automated' ELSE NULL END,
 CASE WHEN selected.id IS NOT NULL THEN 'publication_event:'||selected.id::text WHEN previous.id IS NOT NULL THEN 'previous_publication_event:'||previous.id::text WHEN current.publication_id IS NOT NULL THEN 'current_publication_at_migration' ELSE 'prepared_snapshot' END
 FROM publications p
 LEFT JOIN current_publication current ON current.publication_id=p.id
 LEFT JOIN LATERAL (SELECT id,actor_id,actor_type,created_at FROM publication_events WHERE publication_id=p.id ORDER BY created_at,id LIMIT 1) selected ON true
 LEFT JOIN LATERAL (SELECT id FROM publication_events WHERE previous_id=p.id ORDER BY created_at,id LIMIT 1) previous ON true;
CREATE FUNCTION public.initialize_publication_visibility() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN INSERT INTO public.publication_visibility(publication_id) VALUES(NEW.id); RETURN NEW; END $$;
CREATE TRIGGER initialize_publication_visibility AFTER INSERT ON publications FOR EACH ROW EXECUTE FUNCTION public.initialize_publication_visibility();
CREATE FUNCTION public.protect_publication_visibility() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.publication_id<>NEW.publication_id THEN RAISE EXCEPTION 'Publication visibility identity is immutable'; END IF;
 IF OLD.status='published' AND (NEW.status<>'published' OR NEW.published_at IS DISTINCT FROM OLD.published_at OR NEW.actor_id IS DISTINCT FROM OLD.actor_id OR NEW.actor_type IS DISTINCT FROM OLD.actor_type OR NEW.evidence IS DISTINCT FROM OLD.evidence) THEN
 RAISE EXCEPTION 'Historical public exposure cannot be erased or reassigned'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER protect_publication_visibility BEFORE UPDATE ON publication_visibility FOR EACH ROW EXECUTE FUNCTION public.protect_publication_visibility();
CREATE FUNCTION public.require_public_default() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.publication_visibility WHERE publication_id=NEW.publication_id AND status='published') THEN RAISE EXCEPTION 'Default publication must be explicitly published'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER require_public_default BEFORE INSERT OR UPDATE ON current_publication FOR EACH ROW EXECUTE FUNCTION public.require_public_default();
CREATE INDEX publication_visibility_status_idx ON publication_visibility(status,publication_id);
