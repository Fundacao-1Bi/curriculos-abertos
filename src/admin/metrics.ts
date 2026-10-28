import { pool } from '../db/client';
export async function recordRequestMetric(route:string,status:number,elapsedMs:number) {
  // Store route patterns, not query strings, credentials, IDs, or personal data.
  const pattern=route.replace(/[a-f0-9]{8}-[a-f0-9-]{27,}/gi,':id').slice(0,200);
  await pool.query("INSERT INTO request_metrics(bucket,route,status,requests,total_ms) VALUES(date_trunc('minute',now()),$1,$2,1,$3) ON CONFLICT(bucket,route,status) DO UPDATE SET requests=request_metrics.requests+1,total_ms=request_metrics.total_ms+excluded.total_ms",[pattern,status,elapsedMs]);
}
