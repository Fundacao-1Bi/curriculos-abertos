import {pool} from '../db/client';
import {resolvePublication} from './service';

/** Choices come from the same published snapshot used by the results. */
export async function listKindOptions(publication:string):Promise<string[]> {
 const fixed=await resolvePublication(publication);
 const result=await pool.query<{kind:string}>('SELECT DISTINCT kind FROM items WHERE publication_id=$1 ORDER BY kind',[fixed]);
 return result.rows.map(row=>row.kind);
}
