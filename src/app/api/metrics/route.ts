import { requireActor, AdminError } from '../../../admin/auth';
import { pool } from '../../../db/client';
export const dynamic='force-dynamic';
export async function GET(request:Request){
  try{
    await requireActor(request.headers,true);
    const [jobs,requests]=await Promise.all([pool.query('SELECT type,status,count(*)::int AS count FROM jobs GROUP BY type,status'),pool.query("SELECT route,status,sum(requests)::int AS requests,sum(total_ms)/NULLIF(sum(requests),0) AS mean_ms FROM request_metrics WHERE bucket>now()-interval '24 hours' GROUP BY route,status")]);
    return Response.json({jobs:jobs.rows,requests:requests.rows});
  }catch(error){return Response.json({error:error instanceof AdminError?error.code:'unavailable'},{status:error instanceof AdminError?error.status:503});}
}
