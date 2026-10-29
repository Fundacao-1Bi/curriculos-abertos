'use client';
import Link from 'next/link';
import {useMemo,useState} from 'react';
export interface HierarchyNode {id:string;parent_id:string|null;code:string|null;text:string;kind:string;child_count:number;learning_child_count:number;source_number?:string|number|null;source_order?:string|number|null;evidence?:{page:number|null;bbox?:number[]}[];}
const normalize=(s:string)=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR');
const names:Record<string,string>={competencia_geral:'Competência geral',competencia_especifica:'Competência específica',direito_aprendizagem:'Direito de aprendizagem',campo_experiencia:'Campo de experiências',area_conhecimento:'Área',componente_curricular:'Componente',grupo_etario:'Grupo etário',unidade_tematica:'Unidade temática',objeto_conhecimento:'Objeto de conhecimento',campo_atuacao:'Campo de atuação',pratica_linguagem:'Prática de linguagem',eixo:'Eixo',etapa:'Etapa'};
export function HierarchyExplorer({nodes,publication,curriculum}:{nodes:HierarchyNode[];publication:string;curriculum:string}){
 const [query,setQuery]=useState('');
 const structure=useMemo(()=>{
  const index=new Map(nodes.map(node=>[node.id,node]));const children=new Map<string,HierarchyNode[]>();
  for(const node of nodes){const parent=node.parent_id&&index.has(node.parent_id)?node.parent_id:'';const group=children.get(parent)??[];group.push(node);children.set(parent,group);}
  const physical=(node:HierarchyNode)=>[Number(node.evidence?.[0]?.page??Number.MAX_SAFE_INTEGER),Number(node.evidence?.[0]?.bbox?.[1]??0),Number(node.evidence?.[0]?.bbox?.[0]??0)];
  const compare=(a:HierarchyNode,b:HierarchyNode)=>{const ao=Number(a.source_order??a.source_number),bo=Number(b.source_order??b.source_number);if(a.source_order!=null&&b.source_order!=null&&Number.isFinite(ao)&&Number.isFinite(bo)&&ao!==bo)return ao-bo;if(a.parent_id===b.parent_id&&a.source_number!=null&&b.source_number!=null&&Number.isFinite(ao)&&Number.isFinite(bo)&&ao!==bo)return ao-bo;const aa=physical(a),bb=physical(b);return aa[0]-bb[0]||aa[1]-bb[1]||aa[2]-bb[2]||a.id.localeCompare(b.id);};
  for(const group of children.values())group.sort(compare);
  const needle=normalize(query.trim());const matches=new Set(nodes.filter(node=>!needle||normalize([node.code,node.kind,node.text].join(' ')).includes(needle)).map(node=>node.id));
  const visible=new Set(matches);
  for(const id of matches){const visited=new Set<string>();let parent=index.get(id)?.parent_id;while(parent&&index.has(parent)&&!visited.has(parent)){visited.add(parent);visible.add(parent);parent=index.get(parent)?.parent_id;}}
  return{children,matches,visible,roots:children.get('')??[]};
 },[nodes,query]);
 function branch(node:HierarchyNode,path:Set<string>,depth=0):React.ReactNode{
  if(!structure.visible.has(node.id))return null;
  if(path.has(node.id)||depth>32)return <li key={node.id}><p role="alert">Hierarquia inconsistente. Confira a fonte e relate este registro.</p></li>;
  const next=new Set(path);next.add(node.id);const children=structure.children.get(node.id)??[];
  const params=new URLSearchParams({publication,curriculum,parent_id:node.id});
  return <li key={node.id}><details open={query.trim()?true:undefined}><summary><span className="hierarchy-kind">{names[node.kind]??node.kind.replaceAll('_',' ')}{node.source_number!=null?' '+String(node.source_number):''}</span> {node.code?<code>{node.code} · </code>:null}{node.text}</summary><div className="hierarchy-actions"><Link href={'/aprendizagens/'+encodeURIComponent(node.id)+'?'+new URLSearchParams({publication})}>Conferir texto e evidência ↗</Link>{node.child_count>0?<Link href={'/buscar?'+params}>Consultar {node.child_count.toLocaleString('pt-BR')} filho(s) direto(s) →</Link>:null}</div>{children.length?<ul>{children.map(child=>branch(child,next,depth+1))}</ul>:null}</details></li>;
 }
 return <section className="document-hierarchy" aria-labelledby="hierarquia-documental"><h3 id="hierarquia-documental">Organização original estruturada</h3><p id="hierarchy-help" className="muted">Abra os níveis do documento ou busque um trecho. Vínculos de hierarquia preservam a organização documental; não representam pré-requisitos inferidos.</p><label>Buscar na estrutura<input type="search" value={query} onChange={e=>setQuery(e.target.value)} aria-describedby="hierarchy-help" placeholder="Ex.: competência, números, leitura"/></label><p role="status">{structure.matches.size.toLocaleString('pt-BR')} de {nodes.length.toLocaleString('pt-BR')} nós estruturais no recorte.</p>{structure.roots.length?<ul>{structure.roots.map(node=>branch(node,new Set()))}</ul>:<p role="alert">A hierarquia não possui raiz navegável. Confira as evidências antes de utilizar este recorte.</p>}</section>;
}
