type CodeRecord={code?:unknown;official_code_present_in_source?:unknown;code_like_token_recognized_by_OCR?:unknown;official_code_presence_validation?:unknown};
export function hasPendingPrintedCode(item:CodeRecord):boolean{return item.official_code_present_in_source===true&&!(typeof item.code==='string'&&item.code.length>0);}
export function hasPendingOcrCode(item:CodeRecord):boolean{return !(typeof item.code==='string'&&item.code.length>0)&&item.official_code_present_in_source!==false&&!hasPendingPrintedCode(item)&&item.code_like_token_recognized_by_OCR===true&&item.official_code_presence_validation==='pending_source_glyph_verification';}
export function learningCodeLabel(item:CodeRecord):string{
 if(typeof item.code==='string'&&item.code.length)return item.code;
 if(hasPendingPrintedCode(item))return 'Código impresso pendente de leitura';
 if(hasPendingOcrCode(item))return 'Possível código aguardando conferência';
 return item.official_code_present_in_source===false?'Item sem código na fonte':'Código não informado';
}
