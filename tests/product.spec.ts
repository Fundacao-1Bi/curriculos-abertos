import {test,expect} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import {mkdir} from 'node:fs/promises';

const pinned=(path:string)=>process.env.TEST_PUBLICATION?path+(path.includes('?')?'&':'?')+'publication='+encodeURIComponent(process.env.TEST_PUBLICATION):path;

test('consulta integrada, fontes, 27 UFs, filtros, comparação e acessibilidade',async({page,request},testInfo)=>{
 const response=await request.get(pinned('/api/v1/aprendizagens?limit=2'));expect(response.ok()).toBeTruthy();const found=await response.json();test.info().annotations.push({type:'data-publication',description:found.publication});
 expect(found.data.length,'Jornada exige dados reais carregados').toBeGreaterThan(0);const item=found.data[0];
 const publications=await request.get('/api/v1/publicacoes?publication='+encodeURIComponent(found.publication));expect(publications.ok()).toBeTruthy();
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('/?publication='+encodeURIComponent(found.publication));await expect(page.locator('h1')).toBeVisible();
 await expect(page.locator('.uf-card')).toHaveCount(27);
 await page.getByLabel('Código, trecho ou tema',{exact:true}).fill(item.code??item.text.slice(0,25));
 await page.getByRole('button',{name:/Explorar/}).click();
 await expect(page).toHaveURL(/buscar.*publication=/);await expect(page.locator('.learning-list')).toBeVisible();
 const searchUrl=page.url();await page.locator('.learning-list a').first().click();
 await expect(page).toHaveURL(/\/aprendizagens\//);
 await expect(page.locator('h1')).toBeVisible();await expect(page.getByText(item.text,{exact:false}).first()).toBeVisible();
 await page.goBack();await expect(page).toHaveURL(searchUrl);
 await page.goto('/fontes?publication='+encodeURIComponent(found.publication));await expect(page.locator('main')).toContainText(/Fonte|fonte/);
 await page.goto('/comparar?uf=SP&publication='+encodeURIComponent(found.publication));
 await expect(page.locator('h1')).toBeVisible();
 await page.getByRole('combobox',{name:'UF 1',exact:true}).selectOption('SP');
 await page.getByRole('combobox',{name:'UF 2',exact:true}).selectOption('MG');
 await page.getByRole('button',{name:/Comparar currículos/}).click();
 await expect(page.locator('.compare-column')).toHaveCount(2);
 await expect(page).toHaveURL(new RegExp('publication='+found.publication));
 await page.getByRole('combobox',{name:'Terceira UF (opcional)',exact:true}).selectOption('PR');
 await page.getByRole('button',{name:/Comparar currículos/}).click();
 await expect(page.locator('.compare-column')).toHaveCount(3);
 await page.goto('/analises?publication='+encodeURIComponent(found.publication));await expect(page.locator('main')).toContainText(/denominador|Denominador|universo/);
 for(const path of ['/downloads','/publicacoes','/desenvolvedores','/contribuir']){
  await page.goto(path+'?publication='+encodeURIComponent(found.publication));await expect(page.locator('h1')).toBeVisible();await expect(page.locator('body')).not.toContainText('Application error');
 }
 await page.goto('/buscar?uf=SP&stage=EF&publication='+encodeURIComponent(found.publication));
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'Sem overflow horizontal global').toBeTruthy();
 const a11y=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
 expect(a11y.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>n.target)}))).toEqual([]);
 await page.goto('/?publication='+encodeURIComponent(found.publication));await expect(page.locator('.uf-card')).toHaveCount(27);
 await page.keyboard.press('Tab');expect(await page.evaluate(()=>document.activeElement?.tagName)).toBe('A');
 await page.getByRole('heading',{level:1}).click();
 expect(errors).toEqual([]);
 await mkdir('docs/evidence/screenshots',{recursive:true});await page.screenshot({path:`docs/evidence/screenshots/home-${testInfo.project.name}.png`,fullPage:true});
});

test('busca vazia, código local, panorama nacional e contribuição persistida',async({page,request})=>{
 const data=await(await request.get(pinned('/api/v1/aprendizagens?limit=1'))).json();test.info().annotations.push({type:'data-publication',description:data.publication});
 const item=data.data[0];expect(item?.id).toBeTruthy();
 await page.goto('/buscar?q=zzzzzzzznaolocalizado&publication='+encodeURIComponent(data.publication));
 await expect(page.locator('main')).toContainText(/Nenhum|nenhum|0 resultado/);
 await page.goto('/aprendizagens/'+encodeURIComponent(item.id)+'?publication='+encodeURIComponent(data.publication));
 await expect(page.locator('main')).toContainText(item.code??item.text.slice(0,25));
 const bncc=await(await request.get('/api/v1/aprendizagens?uf=BR&limit=1&publication='+encodeURIComponent(data.publication))).json();
 expect(bncc.data.length,'Referência BNCC real necessária').toBeGreaterThan(0);
 await page.goto('/panorama/'+encodeURIComponent(bncc.data[0].id)+'?publication='+encodeURIComponent(data.publication));
 await expect(page.locator('main')).toContainText(/27/);
 const contribution=await request.post('/api/v1/contribuicoes',{headers:{Origin:new URL(page.url()).origin},data:{record_url:page.url(),description:'Verificação automatizada da fila pública; não altera dados curriculares.',kind:'error'}});
 expect(contribution.status()).toBe(201);const receipt=await contribution.json();expect(JSON.stringify(receipt)).toMatch(/[a-f0-9-]{36}/);
});


test('J01 nacional: cada UF expõe registros reais e fontes na mesma publicação',async({page,request})=>{
 test.setTimeout(180000);
 const catalog=await(await request.get(pinned('/api/v1/ufs'))).json();test.info().annotations.push({type:'data-publication',description:catalog.publication});expect(catalog.data).toHaveLength(27);
 for(const uf of catalog.data){
  const response=await request.get('/api/v1/aprendizagens?uf='+uf.uf+'&limit=1&publication='+encodeURIComponent(catalog.publication));
  expect(response.ok()).toBeTruthy();const result=await response.json();
  expect(result.data.length,uf.uf+' precisa registros reais, não apenas cadastro').toBeGreaterThan(0);
  const item=result.data[0];expect(item.evidence.length).toBeGreaterThan(0);expect(item.uf).toBe(uf.uf);
  await page.goto('/ufs/'+uf.uf+'?publication='+encodeURIComponent(catalog.publication));
  await expect(page.locator('main')).toContainText(uf.name);
  await page.goto('/aprendizagens/'+encodeURIComponent(item.id)+'?publication='+encodeURIComponent(catalog.publication));
  await expect(page.locator('.detail-text')).toHaveText(item.text);
  await expect(page.locator('main')).toContainText('Confira a evidência');
 }
});

test('J01 estrutura documental: navegar até filhos e evidência sem conhecer código',async({page,request})=>{
 const response=await request.get(pinned('/api/v1/curriculos?uf=BR'));expect(response.ok()).toBeTruthy();
 const catalog=await response.json();test.info().annotations.push({type:'data-publication',description:catalog.publication});
 expect(catalog.data.length,'Referência nacional estruturada necessária').toBeGreaterThan(0);
 let selected:{curriculum:string;node:{id:string;text:string;child_count:number}}|undefined;
 for(const curriculum of catalog.data){
  const result=await request.get('/api/v1/curriculos/'+encodeURIComponent(curriculum.id)+'/estrutura?publication='+encodeURIComponent(catalog.publication));expect(result.ok()).toBeTruthy();
  const structure=await result.json();const node=structure.hierarchy.nodes.find((value:{child_count:number;code:string|null})=>value.child_count>0&&!value.code);
  if(node){selected={curriculum:curriculum.id,node};break;}
 }
 expect(selected,'Hierarquia original com nós sem código e filhos documentados necessária').toBeDefined();
 const {curriculum,node}=selected!;
 await page.goto('/curriculos/'+encodeURIComponent(curriculum)+'?publication='+encodeURIComponent(catalog.publication));
 await page.getByRole('searchbox',{name:'Buscar na estrutura'}).fill(node.text);
 const entry=page.locator('details').filter({has:page.locator('summary').filter({hasText:node.text})}).last();
 await expect(entry.locator('summary').first()).toContainText(node.text);
 await expect(entry).toHaveAttribute('open','');
 await entry.getByRole('link',{name:/Consultar .*filho/}).first().click();
 await expect(page).toHaveURL(/parent_id=/);await expect(page.locator('.learning-list')).toBeVisible();
 await page.getByRole('button',{name:'Aplicar filtros'}).click();
 await expect(page).toHaveURL(new RegExp('parent_id='+encodeURIComponent(node.id)));
 await expect(page.locator('.learning-list')).toBeVisible();
 await page.locator('.learning-list a').first().click();
 await expect(page).toHaveURL(/\/aprendizagens\//);
 await expect(page.locator('.detail-text')).not.toBeEmpty();await expect(page.locator('main')).toContainText('Confira a evidência');
});

test('J02 ficha preserva relações ao chegar de uma página posterior da busca',async({page,request})=>{
 const response=await request.get(pinned('/api/v1/correspondencias?limit=1'));expect(response.ok()).toBeTruthy();
 const result=await response.json();test.info().annotations.push({type:'data-publication',description:result.publication});
 expect(result.data.length,'Publicação integrada precisa vínculos reais verificáveis').toBeGreaterThan(0);
 const relation=result.data[0];expect(relation.members.length).toBeGreaterThan(1);
 const item=relation.members[0],other=relation.members.find((member:{item_id:string})=>member.item_id!==item.item_id);expect(other).toBeDefined();
 await page.goto('/aprendizagens/'+encodeURIComponent(item.item_id)+'?'+new URLSearchParams({publication:result.publication,page:'2'}));
 const section=page.locator('.detail-block').filter({has:page.getByRole('heading',{name:'Relações curriculares',exact:true})});
 await expect(section.getByRole('link',{name:other.item_id,exact:true}).first()).toBeVisible();
 await expect(section).toContainText(relation.method);
 await page.getByRole('link',{name:'← Voltar aos resultados com os filtros',exact:true}).click();
 await expect(page).toHaveURL(/\/buscar\?/);expect(new URL(page.url()).searchParams.get('page')).toBe('2');
});
