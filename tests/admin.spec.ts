import { test,expect,type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdir,readFile,writeFile } from 'node:fs/promises';
import { join } from 'node:path';

test.use({trace:'off',video:'off',screenshot:'off'});
type State={run_id:string;actor_id:string;publication:string;item:{id:string;text:string;source_id:string;evidence:unknown[]};draft_id?:string;draft_title?:string;contribution_id?:string};
function credentials(){const email=process.env.QA_ADMIN_EMAIL,password=process.env.QA_ADMIN_PASSWORD,wrong=process.env.QA_ADMIN_WRONG_PASSWORD;if(!email||!password||!wrong||!process.env.QA_ADMIN_STATE_FILE)throw new Error('Execute pelo harness scripts/qa-admin-browser.ts; não há credencial padrão.');return{email,password,wrong,statePath:process.env.QA_ADMIN_STATE_FILE};}
async function state(path:string):Promise<State>{return JSON.parse(await readFile(path,'utf8'));}
async function saveState(path:string,value:State){await writeFile(path,JSON.stringify(value),{mode:0o600});}
function section(page:Page,name:string){return page.locator('section').filter({has:page.getByRole('heading',{name,exact:true})});}
function responseFor(page:Page,path:string,method='POST'){return page.waitForResponse(response=>new URL(response.url()).pathname===path&&response.request().method()===method,{timeout:180000});}
async function checkAxe(page:Page,path:string){
 const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
 const violations=result.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,targets:v.nodes.map(n=>n.target)}));
 await writeFile(path,JSON.stringify({url:new URL(page.url()).pathname,violations,passes:result.passes.length},null,2),{mode:0o600});expect(violations).toEqual([]);
}
async function safeScreenshot(page:Page,path:string){
 // Initial/error login captures mask inputs; authenticated captures contain no auth form.
 await page.screenshot({path,fullPage:false,mask:[page.locator('input[type="password"],input[type="email"]')]});
}

test('administração real: login, fontes, registro fixado, curadoria segura, teclado e acessibilidade',async({page,request},testInfo)=>{
 const auth=credentials();let saved=await state(auth.statePath);const desktop=testInfo.project.name==='admin-desktop';
 const evidence=join('docs/evidence/admin-browser',saved.run_id);await mkdir(evidence,{recursive:true});
 const prefix=join(evidence,testInfo.project.name),pageErrors:string[]=[];
 page.on('pageerror',error=>pageErrors.push(error.message));
 testInfo.annotations.push({type:'publication',description:saved.publication},{type:'actor_type',description:'automated'},{type:'scope',description:desktop?'rascunho idêntico + validação técnica, sem preparar/publicar':'navegação, inspeção, seleção e acessibilidade; sem duplicar snapshot'});
 await page.goto('/admin');await expect(page.getByRole('heading',{name:'Administração',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Entrar na curadoria',exact:true})).toBeVisible();
 await checkAxe(page,prefix+'-login-axe.json');await safeScreenshot(page,prefix+'-login.png');
 await page.getByLabel('E-mail',{exact:true}).focus();await page.keyboard.press('Tab');await expect(page.getByLabel('Senha',{exact:true})).toBeFocused();
 expect(await page.getByLabel('Senha',{exact:true}).evaluate(element=>getComputedStyle(element).outlineStyle)).not.toBe('none');
 if(desktop){
  await page.getByLabel('E-mail',{exact:true}).fill(auth.email);await page.getByLabel('Senha',{exact:true}).fill(auth.wrong);
  const rejected=responseFor(page,'/api/auth/sign-in/email');await page.getByRole('button',{name:'Entrar na curadoria',exact:true}).click();expect((await rejected).status()).toBe(401);
  await expect(page.locator('.admin-status')).toContainText('Confira as credenciais');
  await page.getByLabel('E-mail',{exact:true}).fill('');await page.getByLabel('Senha',{exact:true}).fill('');await safeScreenshot(page,prefix+'-login-error.png');
 }
 await page.getByLabel('E-mail',{exact:true}).fill(auth.email);await page.getByLabel('Senha',{exact:true}).fill(auth.password);
 const accepted=responseFor(page,'/api/auth/sign-in/email'),overviewResponse=responseFor(page,'/api/admin/overview','GET');
 await page.getByRole('button',{name:'Entrar na curadoria',exact:true}).click();expect((await accepted).status()).toBe(200);
 const overview=await overviewResponse;expect(overview.status()).toBe(200);const overviewData=await overview.json();
 expect(overviewData.data.actor.actor_type).toBe('automated');expect(overviewData.data.actor.id).toBe(saved.actor_id);
 await expect(page.getByRole('button',{name:'Sair',exact:true})).toBeVisible();await expect(page.locator('.admin-toolbar').first()).toContainText('automated');
 await expect(page.getByRole('heading',{name:'Fontes e registros',exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Candidatos de ingestão',exact:true})).toBeVisible();
 await expect(page.getByRole('combobox',{name:'Candidato ingerido',exact:true})).toBeVisible();
 await checkAxe(page,prefix+'-overview-axe.json');await page.evaluate(()=>scrollTo(0,0));await safeScreenshot(page,prefix+'-overview.png');
 const inspector=section(page,'Fontes e registros');await inspector.getByRole('combobox',{name:'Publicação consultada',exact:true}).selectOption(saved.publication);
 await inspector.getByLabel('ID canônico do registro',{exact:true}).fill('qa-browser-registro-inexistente');
 const missing=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/v1/aprendizagens/qa-browser-registro-inexistente');await inspector.getByRole('button',{name:'Conferir fonte e transcrição',exact:true}).click();expect((await missing).status()).toBe(404);await expect(page.locator('.admin-status')).toContainText('Registro não encontrado');
 await inspector.getByLabel('ID canônico do registro',{exact:true}).fill(saved.item.id);
 const inspected=page.waitForResponse(response=>new URL(response.url()).pathname==='/api/v1/aprendizagens/'+encodeURIComponent(saved.item.id)&&response.request().method()==='GET');
 await inspector.getByRole('button',{name:'Conferir fonte e transcrição',exact:true}).click();const inspectedResponse=await inspected;expect(inspectedResponse.status()).toBe(200);expect(new URL(inspectedResponse.url()).searchParams.get('publication')).toBe(saved.publication);
 const actual=await inspectedResponse.json();expect(actual.publication).toBe(saved.publication);expect(actual.data.text).toBe(saved.item.text);expect(actual.data.evidence).toEqual(saved.item.evidence);
 await expect(page.getByRole('heading',{name:'Registro extraído',exact:true})).toBeVisible();await expect(page.locator('.admin-record')).toContainText(saved.item.id);
 await page.locator('.admin-record').screenshot({path:prefix+'-record.png'});
 const sources=await request.get('/api/v1/fontes/'+encodeURIComponent(saved.item.source_id)+'?publication='+encodeURIComponent(saved.publication));expect(sources.ok()).toBeTruthy();const sourceData=await sources.json();expect(sourceData.publication).toBe(saved.publication);expect(sourceData.data.id).toBe(saved.item.source_id);
 const sourcePage=await page.context().newPage();await sourcePage.goto('/fontes?publication='+encodeURIComponent(saved.publication)+'&uf='+encodeURIComponent(sourceData.data.uf)+'#'+encodeURIComponent(saved.item.source_id));await expect(sourcePage.locator('main')).toContainText(sourceData.data.title);await sourcePage.close();
 const drafts=section(page,'Rascunhos e publicações');
 if(desktop){
  await drafts.getByRole('combobox',{name:'Publicação base',exact:true}).selectOption(saved.publication);saved.draft_title='Verificação de navegador '+saved.run_id;
  await drafts.getByLabel('Título',{exact:true}).fill(saved.draft_title);const created=responseFor(page,'/api/admin/drafts');await drafts.getByRole('button',{name:'Criar rascunho',exact:true}).click();const createdResponse=await created;expect(createdResponse.status()).toBe(200);saved.draft_id=(await createdResponse.json()).data.id;await saveState(auth.statePath,saved);
  await drafts.getByRole('combobox',{name:'Rascunho selecionado',exact:true}).selectOption(saved.draft_id!);
  const correction=drafts.locator('form').filter({has:page.getByRole('heading',{name:'Corrigir transcrição',exact:true})});
  await correction.getByLabel('ID do item',{exact:true}).fill(saved.item.id);await correction.getByLabel('Texto corrigido',{exact:true}).fill(saved.item.text);await correction.getByLabel('Justificativa e evidência',{exact:true}).fill('Verificação automatizada de interface; redação oficial e evidências preservadas integralmente.');
  const staged=responseFor(page,`/api/admin/drafts/${saved.draft_id}/changes`);await correction.getByRole('button',{name:'Adicionar correção ao rascunho',exact:true}).click();expect((await staged).status()).toBe(200);
  const validating=responseFor(page,`/api/admin/drafts/${saved.draft_id}/validate`);await drafts.getByRole('button',{name:'Validar tecnicamente',exact:true}).click();await expect(page.locator('.admin-status')).toContainText('Processando');await expect(drafts.getByRole('button',{name:'Preparar snapshot',exact:true})).toBeDisabled();
  const validated=await validating;expect(validated.status()).toBe(200);const validation=await validated.json();expect(validation.data.valid).toBe(true);expect(validation.data.human_pedagogical_approval).toBe(false);
  const validationRow=drafts.getByRole('row').filter({hasText:saved.draft_title});await expect(validationRow).toContainText('validated');await expect(validationRow).toContainText('Não preparado');
  const receipt=await request.post('/api/v1/contribuicoes',{headers:{Origin:new URL(page.url()).origin},data:{kind:'error',record_id:saved.item.id,record_url:'/aprendizagens/'+encodeURIComponent(saved.item.id)+'?publication='+encodeURIComponent(saved.publication),description:'Verificação automatizada de contribuição pela interface administrativa; sem dados pessoais.'}});expect(receipt.status()).toBe(201);saved.contribution_id=(await receipt.json()).data.id;await saveState(auth.statePath,saved);
  const refreshed=responseFor(page,'/api/admin/overview','GET');await page.getByRole('button',{name:'Atualizar',exact:true}).click();expect((await refreshed).status()).toBe(200);
  const card=section(page,'Contribuições públicas').locator('article').filter({hasText:saved.contribution_id!});await card.getByRole('combobox',{name:'Decisão',exact:true}).selectOption('needs_information');await card.getByLabel('Justificativa',{exact:true}).fill('Ensaio automatizado: solicitar evidência adicional sem alterar o corpus publicado.');
  const decided=responseFor(page,`/api/admin/contributions/${saved.contribution_id}/decide`);await card.getByRole('button',{name:'Registrar decisão',exact:true}).click();const decision=await decided;expect(decision.status()).toBe(200);expect((await decision.json()).data.status).toBe('needs_information');
 }else{
  saved=await state(auth.statePath);if(saved.draft_id)await drafts.getByRole('combobox',{name:'Rascunho selecionado',exact:true}).selectOption(saved.draft_id);
 }
 await checkAxe(page,prefix+'-curation-axe.json');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'Tabelas devem rolar no contêiner sem quebrar toda a tela').toBe(true);
 await drafts.scrollIntoViewIfNeeded();await safeScreenshot(page,prefix+'-curation.png');
 const signedOut=responseFor(page,'/api/auth/sign-out');await page.getByRole('button',{name:'Sair',exact:true}).click();expect((await signedOut).status()).toBe(200);await expect(page.getByRole('button',{name:'Entrar na curadoria',exact:true})).toBeVisible();
 const denied=await request.get('/api/admin/overview');expect(denied.status()).toBe(401);expect(pageErrors).toEqual([]);
});
