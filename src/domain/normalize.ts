export const normalize = (text:string) => text.normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase().replace(/\s+/g,' ').trim();
export function csvCell(value:unknown):string {
 let text=typeof value==='string'?value:JSON.stringify(value??null);
 if(/^[\s]*[=+\-@\t\r]/u.test(text)) text="'"+text;
 return '"'+text.replace(/"/g,'""')+'"';
}
