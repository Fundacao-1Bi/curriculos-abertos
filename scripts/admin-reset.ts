import { randomUUID } from 'node:crypto';
import { hashPassword } from 'better-auth/crypto';
import { z } from 'zod';
import { pool } from '../src/db/client';
import { readPassword,cliArgs } from './admin-password';
const args=cliArgs();const email=z.email().parse(args.email).toLowerCase();
const password=await readPassword();if(password.length<14||password.length>128)throw new Error('Use de 14 a 128 caracteres.');
const hash=await hashPassword(password);const client=await pool.connect();
try{
  await client.query('BEGIN');
  const result=await client.query('SELECT u.id FROM "user" u JOIN admin_roles r ON r.user_id=u.id WHERE u.email=$1 FOR UPDATE',[email]);
  const id=result.rows[0]?.id;if(!id)throw new Error('Conta administrativa não encontrada.');
  await client.query('UPDATE account SET password=$2,"updatedAt"=now() WHERE "userId"=$1 AND "providerId"=\'credential\'',[id,hash]);
  await client.query('DELETE FROM session WHERE "userId"=$1',[id]);
  await client.query('INSERT INTO audit_events(id,actor_id,actor_type,action,entity_type,entity_id,reason) VALUES($1,\'local-admin-cli\',\'automated\',\'rotate_password\',\'administrator\',$2,\'Rotação local de senha com revogação de sessões.\')',[randomUUID(),id]);
  await client.query('COMMIT');console.log(JSON.stringify({event:'admin_password_rotated',id,sessions_revoked:true}));
}catch(error){await client.query('ROLLBACK');throw error;}finally{client.release();await pool.end();}
