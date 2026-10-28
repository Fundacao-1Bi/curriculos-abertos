import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { pool } from '../db/client';
const schema = z.object({
  record_url:z.string().max(1000).optional(), record_id:z.string().max(500).optional(),
  description:z.string().trim().min(10).max(6000), evidence_url:z.url().max(2000).optional(),
  kind:z.enum(['error','source','relation']), honeypot:z.string().max(200).optional()
});
export async function createContribution(input:unknown) {
  const parsed = schema.parse(input);
  if (parsed.honeypot) throw new Error('Contribuição não aceita.');
  if (parsed.record_url && !parsed.record_url.startsWith('/') && !/^https?:\/\//i.test(parsed.record_url)) throw new Error('URL de registro inválida.');
  if (parsed.evidence_url && !/^https?:\/\//i.test(parsed.evidence_url)) throw new Error('URL de evidência inválida.');
  const id=randomUUID();
  await pool.query('INSERT INTO contributions(id,kind,record_url,record_id,description,evidence_url) VALUES($1,$2,$3,$4,$5,$6)',[id,parsed.kind,parsed.record_url || null,parsed.record_id || null,parsed.description,parsed.evidence_url || null]);
  return {id,status:'pending',message:'Contribuição recebida para avaliação. Os dados publicados não foram alterados.'};
}
export async function getContribution(id:string) {
  if(!z.uuid().safeParse(id).success) return null;
  const result=await pool.query('SELECT id,status,created_at,updated_at FROM contributions WHERE id=$1',[id]);
  return result.rows[0] || null;
}
