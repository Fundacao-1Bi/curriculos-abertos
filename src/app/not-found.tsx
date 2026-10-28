import Link from 'next/link';
export default function NotFound(){return <div className="error-message"><span className="eyebrow">Registro não localizado</span><h1>Este endereço não foi encontrado.</h1><p>Confira o identificador e a publicação consultada ou procure pelo código e pelo texto da aprendizagem.</p><Link className="button" href="/buscar">Ir para a busca ↗</Link></div>}
