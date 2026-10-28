import { headers } from 'next/headers';
import { requireActor, AdminError } from '../../admin/auth';
import { AdminConsole } from './ui';
export const dynamic='force-dynamic';
export default async function Administration() {
  let authenticated=false;
  try{await requireActor(await headers());authenticated=true;}catch(error){if(!(error instanceof AdminError))console.error(JSON.stringify({event:'admin_session_unavailable'}));}
  return <main id="conteudo" className="admin-shell"><p className="eyebrow">CURADORIA • ACESSO RESTRITO</p><h1>Administração</h1><p>Revisões preservam a publicação original, o tipo real do ator e as evidências documentais.</p><AdminConsole authenticated={authenticated}/></main>;
}
