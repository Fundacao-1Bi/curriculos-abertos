/** Manual import guards for the immutable published Evidence contract.
 * Omitted optional fields remain omitted; this predicate never normalizes data.
 */
export function validEvidence(value:unknown,sources:ReadonlySet<string>):boolean {
 if(!value||typeof value!=='object'||Array.isArray(value))return false;
 const e=value as Record<string,unknown>;
 if(typeof e.source_id!=='string'||!sources.has(e.source_id)||typeof e.excerpt!=='string'||!e.excerpt.length)return false;
 if(e.page!==null&&(!Number.isInteger(e.page)||Number(e.page)<1))return false;
 if(e.page===null&&(typeof e.section!=='string'||!e.section.length))return false;
 for(const field of ['printed_page','section'])if(e[field]!==undefined&&e[field]!==null&&typeof e[field]!=='string')return false;
 if(e.bbox!==undefined&&e.bbox!==null&&(!Array.isArray(e.bbox)||e.bbox.length!==4||e.bbox.some(n=>typeof n!=='number'||!Number.isFinite(n))))return false;
 return true;
}
