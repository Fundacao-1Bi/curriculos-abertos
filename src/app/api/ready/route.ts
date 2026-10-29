import { pool } from '../../../db/client';
export const dynamic='force-dynamic';
export const runtime='nodejs';
export async function GET(){
  try{
    await pool.query('SELECT 1');
    const publication=await pool.query('SELECT publication_id FROM current_publication LIMIT 1');
    const worker=await pool.query("SELECT count(*)::int AS count FROM worker_heartbeats WHERE seen_at>now()-interval '45 seconds'");
    const ready=!!publication.rows[0]?.publication_id && worker.rows[0]?.count>0;
    return Response.json({status:ready?'ready':'not_ready',database:'ok',publication:publication.rows[0]?.publication_id || null,worker:worker.rows[0]?.count>0?'ok':'unavailable'}, {status:ready?200:503});
  }catch{return Response.json({status:'not_ready',message:'O serviço ainda não está pronto.'},{status:503});}
}
