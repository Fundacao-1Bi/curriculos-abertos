import { betterAuth } from 'better-auth';
import { pool } from '../db/client';
import { randomUUID } from 'node:crypto';

function buildAuth() {
  const secret = process.env.BETTER_AUTH_SECRET;
  if (!secret || secret.length < 32) throw new Error('BETTER_AUTH_SECRET deve conter pelo menos 32 caracteres.');
  return betterAuth({
    appName: process.env.APP_NAME || 'Currículos Abertos',
    database: pool,
    baseURL: process.env.PUBLIC_URL || 'http://localhost:3000',
    secret,
    emailAndPassword: { enabled: true, disableSignUp: true, minPasswordLength: 14, maxPasswordLength: 128 },
    trustedOrigins: [process.env.PUBLIC_URL || 'http://localhost:3000'],
    session: { expiresIn: 60 * 60 * 8, updateAge: 60 * 30 },
    advanced: { useSecureCookies: new URL(process.env.PUBLIC_URL || 'http://localhost:3000').protocol === 'https:' },
    rateLimit: { enabled: true, window: 60, max: 20 },
  });
}
let instance: ReturnType<typeof buildAuth> | undefined;
export function getAuth() { return instance ??= buildAuth(); }
export type Actor = { id: string; actor_type: 'human'|'automated'; role: 'administrator'|'curator'; name: string };
export class AdminError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
export async function requireActor(headers: Headers, administrator = false): Promise<Actor> {
  const session = await getAuth().api.getSession({ headers });
  if (!session?.user) throw new AdminError(401, 'authentication_required', 'Entre na administração.');
  const result = await pool.query<{role: Actor['role'];actor_type: Actor['actor_type']}>('SELECT role,actor_type FROM admin_roles WHERE user_id=$1', [session.user.id]);
  const role = result.rows[0];
  if (!role || (administrator && role.role !== 'administrator')) throw new AdminError(403, 'forbidden', 'Seu papel não permite esta operação.');
  return { id: session.user.id, name: session.user.name, ...role };
}
export function requireSameOrigin(request: Request) {
  const allowed = new URL(process.env.PUBLIC_URL || 'http://localhost:3000').origin;
  const origin = request.headers.get('origin');
  if (origin !== allowed) throw new AdminError(403, 'origin_rejected', 'Origem da mutação não autorizada.');
  const url = new URL(request.url);
  if (url.host !== new URL(allowed).host && request.headers.get('x-forwarded-host') !== new URL(allowed).host) {
    throw new AdminError(403, 'host_rejected', 'Host não autorizado.');
  }
}
export async function audit(actor: Pick<Actor,'id'|'actor_type'>, action: string, entity_type: string, entity_id: string, reason: string, before: unknown = null, after: unknown = null) {
  await pool.query('INSERT INTO audit_events(id,actor_id,actor_type,action,entity_type,entity_id,reason,before_data,after_data) VALUES($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb)', [randomUUID(),actor.id,actor.actor_type,action,entity_type,entity_id,reason,JSON.stringify(before),JSON.stringify(after)]);
}
