import {exportIngestionBase} from '../src/domain/ingestion-update';
import {pool} from '../src/db/client';
const value=(name:string)=>{const index=process.argv.indexOf(name);return index<0?undefined:process.argv[index+1];};
try{const publication=value('--publication'),directory=value('--directory');if(!publication||!directory)throw Error('Uso: export-ingestion-base.ts --publication ID --directory data/bundles/DIRETORIO');console.log(JSON.stringify(await exportIngestionBase({base_publication:publication,directory})));}catch(error){console.error((error as Error).message);process.exitCode=1;}finally{await pool.end();}
