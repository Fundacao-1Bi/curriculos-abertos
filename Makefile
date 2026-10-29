SHELL := /bin/bash
COMPOSE ?= docker compose
ADMIN_TTY := $(shell if test -t 0; then printf '%s' ''; else printf '%s' '-T'; fi)
.PHONY: configure preflight runtime-images image bootstrap up down verify release-check data-import data-ingest sources-check backup restore admin-create admin-reset logs
configure:
	npm exec -- tsx scripts/ops-configure.ts
runtime-images:
	python3 scripts/ops-pull-runtime.py all
preflight: configure
	node --env-file=.env --import tsx scripts/ops-preflight.ts
image: preflight
ifeq ($(IMAGE_BUILD_METHOD),lifecycle)
	node --env-file=.env --import tsx scripts/ops-build-fallback.ts
else
	$(COMPOSE) build
endif
	node --env-file=.env --import tsx scripts/ops-image-verify.ts
bootstrap: image
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm app npm run db:migrate
	$(COMPOSE) run --rm -e DATA_BUNDLE="$(DATA_BUNDLE)" app npm exec -- tsx scripts/ops-init.ts
	$(COMPOSE) up -d --wait app worker
	@echo 'Serviços iniciados. Crie administrador: make admin-create EMAIL=seu-email ACTOR_TYPE=human (senha via stdin).'
up:
	node --env-file=.env --import tsx scripts/ops-image-verify.ts
	$(COMPOSE) up -d --wait

down:
	$(COMPOSE) down
verify:
	$(COMPOSE) exec -T app npm run typecheck
	$(COMPOSE) exec -T app sh -c 'TEST_DATABASE_ADMIN_URL="$$DATABASE_URL" npm test' 
	$(COMPOSE) exec -T app npm exec -- tsx scripts/mcp-verify.ts
	$(COMPOSE) exec -T app npm exec -- tsx scripts/ops-smoke.ts
	$(COMPOSE) exec -T app npm exec -- tsx scripts/api-verify.ts
release-check:
	$(COMPOSE) run --rm --no-deps -T -v "$(CURDIR)/docs:/app/docs" app npm exec -- tsx scripts/release-check.ts

data-import:
	$(COMPOSE) run --rm -e DATA_BUNDLE="$(DATA_BUNDLE)" app npm exec -- tsx scripts/import-data.ts $(DATA_BUNDLE)
data-ingest:
	$(COMPOSE) exec -T worker npm exec -- tsx scripts/ops-enqueue.ts ingest $(SOURCE)
sources-check:
	$(COMPOSE) exec -T worker npm exec -- tsx scripts/ops-enqueue.ts source-check $(SOURCE)
backup:
	bash scripts/ops-backup.sh
restore:
	bash scripts/ops-restore.sh "$(BACKUP)" "$(RESTORE_DB)"
admin-create:
	$(COMPOSE) exec $(ADMIN_TTY) app npm exec -- tsx scripts/admin-create.ts --email "$(EMAIL)" --name "$(NAME)" --role "$(or $(ROLE),administrator)" --actor-type "$(or $(ACTOR_TYPE),automated)"
admin-reset:
	$(COMPOSE) exec $(ADMIN_TTY) app npm exec -- tsx scripts/admin-reset.ts --email "$(EMAIL)"
logs:
	$(COMPOSE) logs --tail 100 app worker
