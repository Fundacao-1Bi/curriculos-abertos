import {DomainError} from './errors';
/** Inclusive months explicitly documented by the source; never inferred from labels or codes. */
export const MAX_DOCUMENTED_AGE_MONTHS=1800;
export function parseAgeMonths(value:unknown):{min:number;max:number} {
 if(typeof value!=='string'||!/^\d{1,4}(-\d{1,4})?$/.test(value))throw new DomainError(400,'INVALID_AGE_MONTHS','Idade em meses deve ser inteiro ou faixa inclusiva, como 0-6.');
 const [min,end]=value.split('-').map(Number),max=end??min;
 if(min>max||max>MAX_DOCUMENTED_AGE_MONTHS)throw new DomainError(400,'INVALID_AGE_MONTHS','Faixa de idade em meses inválida (0 a 1800).');
 return{min,max};
}
export function validatePositionAge(position:Record<string,unknown>,sourceId?:string):void {
 if(position.age_label!==undefined&&position.age_label!==null&&(typeof position.age_label!=='string'||!position.age_label.trim()||position.age_label.length>500))throw new DomainError(422,'INVALID_POSITION_AGE','Rótulo etário deve preservar texto não vazio da fonte.');
 if(position.age_unknown_reason!==undefined&&position.age_unknown_reason!==null&&(typeof position.age_unknown_reason!=='string'||!position.age_unknown_reason.trim()))throw new DomainError(422,'INVALID_POSITION_AGE','Motivo de idade desconhecida deve ser texto não vazio.');
 const min=position.age_min_months,max=position.age_max_months;
 if(min==null&&max==null)return;
 if(!Number.isInteger(min)||!Number.isInteger(max)||Number(min)<0||Number(max)>MAX_DOCUMENTED_AGE_MONTHS||Number(min)>Number(max))throw new DomainError(422,'INVALID_POSITION_AGE','Limites etários devem ser dois inteiros inclusivos coerentes de 0 a 1800 meses.');
 const evidence=position.age_evidence;
 if(!Array.isArray(evidence)||!evidence.length)throw new DomainError(422,'MISSING_AGE_EVIDENCE','Limites etários exigem evidências explícitas da fonte.');
 for(const e of evidence){if(!e||typeof e!=='object'||Array.isArray(e)||typeof e.source_id!=='string'||!e.source_id||(sourceId&&e.source_id!==sourceId)||typeof e.excerpt!=='string'||!e.excerpt.trim()||!((Number.isInteger(e.page)&&Number(e.page)>0)||(typeof e.section==='string'&&e.section.trim())))throw new DomainError(422,'INVALID_AGE_EVIDENCE','Evidência etária exige fonte compatível, trecho literal e página ou seção.');}
 if(position.age_interval_origin!==undefined&&position.age_interval_origin!=='explicit_source_header_units_to_months')throw new DomainError(422,'INVALID_POSITION_AGE','Origem dos limites etários deve identificar o cabeçalho e unidade explícitos da fonte.');
}
