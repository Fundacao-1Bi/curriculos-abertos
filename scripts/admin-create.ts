import { randomUUID } from 'node:crypto';
import { hashPassword } from 'better-auth/crypto';
import { z } from 'zod';
import { pool } from '../src/db/client';
import { readPassword,cliArgs } from './admin-password';
const args=cliArgs();
const email=z.email().parse(args.email).toLowerCase();
const role=z.enum(['administrator','curator']).parse(args.role || 'administrator');
const actor_type=z.enum(['human','automated']).parse(args['actor-type'] || 'automated');
const password=await readPassword();
if(password.length<14||password.length>128)throw new Error('Use de 14 a 128 caracteres.');
const hash=await hashPassword(password);
const id=randomUUID();const client=await pool.connect();
try{
  await client.query('BEGIN');
  await client.query('INSERT INTO "user"(id,name,email,"emailVerified") VALUES($1,$2,$3,true)',[id,(args.name || email.split('@')[0]).slice(0,120),email]);
  await client.query('INSERT INTO account(id,"accountId","providerId","userId",password) VALUES($1,$2,\'credential\',$2,$3)',[randomUUID(),id,hash]);
  await client.query('INSERT INTO admin_roles(user_id,role,actor_type) VALUES($1,$2,$3)',[id,role,actor_type]);
  await client.query('INSERT INTO audit_events(id,actor_id,actor_type,action,entity_type,entity_id,reason) VALUES($1,\'local-admin-cli\',\'automated\',\'create_account\',\'administrator\',$2,$3)',[randomUUID(),id,`Conta local criada; papel ${role}; identidade declarada ${actor_type}.`]);
  await client.query('COMMIT');
  console.log(JSON.stringify({event:'admin_created',id,role,actor_type,password:'not_disclosed'}));
}catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();await pool.end();}
