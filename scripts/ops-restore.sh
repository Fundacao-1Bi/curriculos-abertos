#!/usr/bin/env bash
set -euo pipefail
backup_dir=${1:?Informe BACKUP=var/backups/data}
restore_db=${2:-curriculos_restore_test}
if [[ ! "$restore_db" =~ ^curriculos_restore_[a-z0-9_]+$ ]]; then
  echo 'Restauração exige um banco descartável com prefixo curriculos_restore_.' >&2
  exit 2
fi
qa_restore=false
if [[ -n "${QA_EXECUTOR_RUN_ID:-}${RESTORE_CLIENT_NAME:-}${RESTORE_APPLICATION_NAME:-}${RESTORE_DATABASE_PRECREATED:-}" ]]; then
  [[ "${QA_EXECUTOR_RUN_ID:-}" =~ ^qa-[a-z0-9-]+$ ]] || { echo 'QA restore requires a valid executor identity.' >&2; exit 2; }
  [[ "${RESTORE_CLIENT_NAME:-}" =~ ^curriculos-qa-command-[a-f0-9-]{36}$ ]] || { echo 'QA restore requires an owned one-off client.' >&2; exit 2; }
  [[ "${RESTORE_APPLICATION_NAME:-}" =~ ^qa-restore-[a-f0-9-]{36}$ ]] || { echo 'QA restore requires a scoped application name.' >&2; exit 2; }
  [[ "${COMPOSE_PROJECT_NAME:-}" =~ ^curriculos-abertos-clean-[a-z0-9-]+$ ]] || { echo 'QA restore requires an isolated Compose project.' >&2; exit 2; }
  [[ "${POSTGRES_USER:-}" == curriculos_qa && "${POSTGRES_DB:-}" == curriculos_qa && "${RESTORE_DATABASE_PRECREATED:-}" == true ]] || { echo 'QA restore requires its registered precreated disposable database.' >&2; exit 2; }
  [[ "$restore_db" =~ ^curriculos_restore_qa_[0-9]{14}_[a-f0-9]{8}$ ]] || { echo 'QA restore database namespace is invalid.' >&2; exit 2; }
  qa_restore=true
fi
# Resolve the prospective target before creating a database; it must be new.
node --input-type=module - "$restore_db" <<'JS'
import {existsSync,lstatSync,realpathSync} from 'node:fs';import {resolve} from 'node:path';
for(const directory of ['var','var/restore'])if(existsSync(directory)){const info=lstatSync(directory);if(!info.isDirectory()||info.isSymbolicLink()||realpathSync(directory)!==resolve(directory))throw Error('Restore parent must not redirect through symlinks');}
if(existsSync(resolve('var/restore',process.argv[2])))throw Error('Restore directory already exists; retained unchanged');
JS
node --input-type=module - "$backup_dir" <<'JS'
import {createHash} from 'node:crypto';import {readFileSync,createReadStream} from 'node:fs';import {join} from 'node:path';
const root=process.argv[2];const manifest=JSON.parse(readFileSync(join(root,'manifest.json'),'utf8'));for(const file of ['database.dump','data.tgz','storage.tgz']){const hash=createHash('sha256');for await(const chunk of createReadStream(join(root,file)))hash.update(chunk);const actual=hash.digest('hex');if(actual!==manifest.checksums[file])throw Error(`Checksum inválido: ${file}`);}
JS
database_exists=false
if docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT datname FROM pg_database"' | rg -x "$restore_db" >/dev/null; then database_exists=true; fi
if [[ "$qa_restore" == true ]]; then
  [[ "$database_exists" == true ]] || { echo 'Registered QA restore database is missing.' >&2; exit 2; }
  tables=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -At -v ON_ERROR_STOP=1 -c "$2"' -- "$restore_db" "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
  [[ "$tables" == 0 ]] || { echo 'QA restore only accepts its new empty database.' >&2; exit 2; }
  db_container=$(docker compose ps -q db)
  [[ "$db_container" =~ ^[a-f0-9]{64}$ ]] || { echo 'Immutable QA database container ID required.' >&2; exit 2; }
  actual_project=$(docker inspect "$db_container" --format '{{index .Config.Labels "com.docker.compose.project"}}')
  actual_service=$(docker inspect "$db_container" --format '{{index .Config.Labels "com.docker.compose.service"}}')
  [[ "$actual_project" == "$COMPOSE_PROJECT_NAME" && "$actual_service" == db ]] || { echo 'QA database container ownership mismatch.' >&2; exit 2; }
  restore_host=$(docker inspect "$db_container" --format '{{.Name}}'); restore_host=${restore_host#/}
  [[ "$restore_host" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo 'Inspectable QA database hostname required.' >&2; exit 2; }
  restore_image=$(docker inspect "$db_container" --format '{{.Image}}')
  [[ "$restore_image" =~ ^sha256:[a-f0-9]{64}$ ]] || { echo 'Immutable PostgreSQL client image required.' >&2; exit 2; }
  restore_network=$(docker inspect "$db_container" --format '{{range $name, $config := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}')
  [[ "$restore_network" =~ ^[A-Za-z0-9_.-]+$ ]] || { echo 'QA database must have exactly one inspectable network.' >&2; exit 2; }
  # A one-off client can be stopped independently. It mounts no database volume.
  # Credentials stay in inherited env, never command arguments or receipts.
  PGPASSWORD="${POSTGRES_PASSWORD:?QA PostgreSQL password missing}" PGAPPNAME="$RESTORE_APPLICATION_NAME" \
    docker run --rm --pull=never --name "$RESTORE_CLIENT_NAME" \
      --label "org.curriculos-abertos.qa-run=$QA_EXECUTOR_RUN_ID" \
      --network "$restore_network" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16777216 \
      --cap-drop ALL --security-opt no-new-privileges --pids-limit 64 --memory 1g --cpus 1 \
      --user postgres --entrypoint pg_restore -e PGPASSWORD -e PGAPPNAME \
      "$restore_image" -h "$restore_host" -U curriculos_qa -d "$restore_db" --exit-on-error < "$backup_dir/database.dump"
else
  [[ "$database_exists" == false ]] || { echo 'Banco de restauração já existe; nenhum dado foi alterado.' >&2; exit 2; }
  docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' -- "$restore_db"
  docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error' -- "$restore_db" < "$backup_dir/database.dump"
fi
mkdir -p "var/restore/$restore_db/data" "var/restore/$restore_db/storage"
# Validate archive member names before extracting to an isolated directory.
python3 - "$backup_dir" <<'PY'
import sys,tarfile,pathlib
for name in ['data.tgz','storage.tgz']:
 with tarfile.open(pathlib.Path(sys.argv[1])/name) as archive:
  for member in archive.getmembers():
   p=pathlib.PurePosixPath(member.name)
   if p.is_absolute() or '..' in p.parts or member.issym() or member.islnk():raise SystemExit('Membro de arquivo não permitido.')
PY
tar -xzf "$backup_dir/data.tgz" -C "var/restore/$restore_db/data"
tar -xzf "$backup_dir/storage.tgz" -C "var/restore/$restore_db/storage"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "SELECT (SELECT count(*) FROM publications) AS publications,(SELECT count(*) FROM items) AS items,(SELECT count(*) FROM sources) AS sources,(SELECT count(*) FROM relations) AS relations,(SELECT count(*) FROM admin_roles) AS administrators;"' -- "$restore_db"
printf 'Restauração isolada concluída em banco %s e var/restore/%s\n' "$restore_db" "$restore_db"
