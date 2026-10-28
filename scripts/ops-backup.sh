#!/usr/bin/env bash
set -euo pipefail
umask 077
backup_stamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p var/backups
backup_dir=$(mktemp -d "var/backups/${backup_stamp}-XXXXXX")
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_dir/database.dump"
tar -czf "$backup_dir/data.tgz" data/manifests data/bundles data/coverage-manifest.json
# Public exports, worker checkpoints and OCR/source monitor state share the persistent storage volume.
docker compose exec -T worker tar -czf - -C /app/var --exclude='./backups' . > "$backup_dir/storage.tgz"
node --input-type=module - "$backup_dir" <<'JS'
import {createHash} from 'node:crypto';import {createReadStream,writeFileSync} from 'node:fs';import {join} from 'node:path';
const dir=process.argv[2];const files=['database.dump','data.tgz','storage.tgz'];async function digest(path){const hash=createHash('sha256');for await(const chunk of createReadStream(path))hash.update(chunk);return hash.digest('hex');}const checksums=Object.fromEntries(await Promise.all(files.map(async file=>[file,await digest(join(dir,file))])));writeFileSync(join(dir,'manifest.json'),JSON.stringify({created_at:new Date().toISOString(),format:'pg-custom+tar',checksums,contains_admin_private_data:true},null,2));
JS
printf 'Backup privado criado em %s\n' "$backup_dir"
