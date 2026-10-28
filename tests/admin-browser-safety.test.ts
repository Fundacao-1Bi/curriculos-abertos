import { test } from 'node:test';
import assert from 'node:assert/strict';
import { redactAdminBrowser } from '../scripts/qa-admin-browser-reporter';
import config from '../scripts/qa-admin-browser.config';

test('reporter administrativo remove segredos de falhas sem perder contexto acionável',()=>{
 const originalPassword=process.env.QA_ADMIN_PASSWORD,originalWrong=process.env.QA_ADMIN_WRONG_PASSWORD;
 process.env.QA_ADMIN_PASSWORD='isolated-test-password-never-production';process.env.QA_ADMIN_WRONG_PASSWORD='isolated-wrong-password-never-production';
 try{
  const raw='Falha ao preencher Senha: isolated-test-password-never-production; tentativa isolated-wrong-password-never-production; postgresql://isolated:credential@localhost/test; better-auth.session_token=isolated-token; Contexto da falha preservado.';
  const redacted=redactAdminBrowser(raw);for(const secret of ['isolated-test-password-never-production','isolated-wrong-password-never-production','isolated:credential','isolated-token'])assert.ok(!redacted.includes(secret));assert.ok(redacted.includes('Contexto da falha preservado.'));assert.ok(redacted.includes('[REDACTED]'));
 }finally{if(originalPassword===undefined)delete process.env.QA_ADMIN_PASSWORD;else process.env.QA_ADMIN_PASSWORD=originalPassword;if(originalWrong===undefined)delete process.env.QA_ADMIN_WRONG_PASSWORD;else process.env.QA_ADMIN_WRONG_PASSWORD=originalWrong;}
});
test('suite administrativa tem desktop/mobile e não herda trace/video/screenshot de autenticação',()=>{
 assert.equal(config.testMatch,'admin.spec.ts');assert.equal(config.use?.trace,'off');assert.equal(config.use?.video,'off');assert.equal(config.use?.screenshot,'off');assert.deepEqual(config.projects?.map(project=>project.name),['admin-desktop','admin-mobile']);assert.equal(config.workers,1);assert.equal(config.retries,0);
});
