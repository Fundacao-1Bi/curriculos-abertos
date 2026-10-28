import { existsSync, writeFileSync, chmodSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
if(existsSync('.env')){console.log('Configuração existente preservada.');process.exit(0);}
const password=randomBytes(32).toString('hex');
const secret=randomBytes(48).toString('base64url');
const text=`POSTGRES_USER=curriculos\nPOSTGRES_DB=curriculos\nPOSTGRES_PASSWORD=${password}\nBETTER_AUTH_SECRET=${secret}\nPUBLIC_URL=http://localhost:3000\nPORT=3000\nDATABASE_PORT=55437\nDATABASE_URL=postgresql://curriculos:${password}@localhost:55437/curriculos\nSTORAGE_DIR=var\nEXPORT_STORAGE_DIR=var\nSOURCE_CHECK_ENABLED=false\nSOURCE_CHECK_INTERVAL_SECONDS=86400\nJOB_TIMEOUT_SECONDS=7200\nPUBLIC_RATE_LIMIT=120\nEXPORT_RATE_LIMIT=10\nMCP_ALLOWED_HOSTS=localhost:3000,127.0.0.1:3000\n`;
writeFileSync('.env',text,{mode:0o600,flag:'wx'});chmodSync('.env',0o600);
console.log('Configuração criada em .env com segredos aleatórios locais. Nenhum segredo foi exibido.');
