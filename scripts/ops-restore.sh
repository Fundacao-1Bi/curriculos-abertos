#!/usr/bin/env bash
set -euo pipefail
backup_dir=${1:?Informe BACKUP=var/backups/data}
restore_db=${2:-curriculos_restore_test}
if [[ ! "$restore_db" =~ ^curriculos_restore_[a-z0-9_]+$ ]]; then
  echo 'Restauração exige um banco descartável com prefixo curriculos_restore_.' >&2
  exit 2
fi
node --input-type=module - "$backup_dir" <<'JS'
import {createHash} from 'node:crypto';import {readFileSync,createReadStream} from 'node:fs';import {join} from 'node:path';
const root=process.argv[2];const manifest=JSON.parse(readFileSync(join(root,'manifest.json'),'utf8'));for(const file of ['database.dump','data.tgz','storage.tgz']){const hash=createHash('sha256');for await(const chunk of createReadStream(join(root,file)))hash.update(chunk);const actual=hash.digest('hex');if(actual!==manifest.checksums[file])throw Error(`Checksum inválido: ${file}`);}
JS
if docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT datname FROM pg_database"' | rg -x "$restore_db" >/dev/null; then
  echo 'Banco de restauração já existe; nenhum dado foi alterado.' >&2
  exit 2
fi
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" "$1"' -- "$restore_db"
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error' -- "$restore_db" < "$backup_dir/database.dump"
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
