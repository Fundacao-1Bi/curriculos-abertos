import { pool } from '../src/db/client';
import { resolveBundleFile } from '../src/domain/bundle-file';
import { importArtifactFile } from '../src/domain/shards';
const explicit=process.argv.find((x,i)=>i>1&&!x.startsWith('--'))??process.env.DATA_BUNDLE;
try {
 const selected=await resolveBundleFile(explicit);
 const result=await importArtifactFile(selected.path,{...selected,makeDefault:!process.argv.includes('--prepare-only')});
 console.log(JSON.stringify({event:'publication_imported',...result}));
}catch(error){console.error(JSON.stringify({event:'import_failed',message:(error as Error).message}));process.exitCode=1;}finally{await pool.end();}
