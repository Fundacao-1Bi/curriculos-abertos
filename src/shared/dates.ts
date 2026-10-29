/** Preserve a source's calendar precision. Only timestamps are converted to the project's timezone. */
export function sourceDate(value:unknown):string{
 if(value===null||value===undefined||value==='')return 'Data não informada';
 const raw=String(value);
 if(/^\d{4}$/.test(raw))return raw;
 const partial=/^(\d{4})-(\d{2})$/.exec(raw);
 if(partial)return Number(partial[2])>=1&&Number(partial[2])<=12?`${partial[2]}/${partial[1]}`:raw;
 const full=/^(\d{4})-(\d{2})-(\d{2})$/.exec(raw);
 if(full){
  const year=Number(full[1]),month=Number(full[2]),day=Number(full[3]);const check=new Date(0);check.setUTCHours(0,0,0,0);check.setUTCFullYear(year,month-1,day);
  return check.getUTCFullYear()===year&&check.getUTCMonth()===month-1&&check.getUTCDate()===day?`${full[3]}/${full[2]}/${full[1]}`:raw;
 }
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})$/.test(raw))return raw;
 const instant=new Date(raw);return Number.isFinite(instant.valueOf())?instant.toLocaleDateString('pt-BR',{timeZone:'America/Sao_Paulo'}):raw;
}
