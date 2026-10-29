import { pool } from '../src/db/client';
import { importArtifactFile } from '../src/domain/shards';
import { resolveBundleFile } from '../src/domain/bundle-file';
try {
  const existing=await pool.query('SELECT count(*)::int AS count FROM publications');
  if(existing.rows[0].count>0)console.log('Publicações existentes preservadas; importação inicial dispensada.');
  else {
    const selected=await resolveBundleFile(process.env.DATA_BUNDLE);
    const result=await importArtifactFile(selected.path,{...selected,makeDefault:true});
    console.log(JSON.stringify({event:'initial_publication_imported',...result,national_release:'not_asserted'}));
  }
}catch(error){console.error(JSON.stringify({event:'bootstrap_import_failed',message:error instanceof Error?error.message:'Falha de importação.'}));process.exitCode=1;}
finally{await pool.end();}
