import {test} from 'node:test';
import assert from 'node:assert/strict';
import {hasPendingPrintedCode,hasPendingOcrCode,learningCodeLabel} from '../src/shared/learning-code';
test('unresolved printed codes are never presented as originally uncoded or guessed from an OCR candidate',()=>{
 const unresolved={code:null,official_code_present_in_source:true,candidate_code:'OCR-UNCONFIRMED'};
 assert.equal(hasPendingPrintedCode(unresolved),true);assert.match(learningCodeLabel(unresolved),/pendente/);assert.doesNotMatch(learningCodeLabel(unresolved),/sem código|OCR-UNCONFIRMED/);
 assert.match(learningCodeLabel({code:null,official_code_present_in_source:false}),/sem código na fonte/);
 assert.equal(hasPendingPrintedCode({code:'EF05CO011',official_code_present_in_source:true}),false);assert.equal(learningCodeLabel({code:'EF05CO011'}),'EF05CO011');
 assert.equal(learningCodeLabel({code:null}),'Código não informado');
});
test('OCR code-like token remains an unconfirmed observation, without asserting official presence',()=>{
 const possible={code:null,code_like_token_recognized_by_OCR:true,official_code_presence_validation:'pending_source_glyph_verification',candidate_code:'UNVERIFIED'};
 assert.equal(hasPendingOcrCode(possible),true);assert.equal(hasPendingPrintedCode(possible),false);
 assert.match(learningCodeLabel(possible),/Possível código/);assert.doesNotMatch(learningCodeLabel(possible),/impresso|sem código|UNVERIFIED/);
 assert.equal(hasPendingOcrCode({...possible,official_code_present_in_source:false}),false);
 assert.equal(hasPendingOcrCode({...possible,code:'EI01EO01'}),false);
});
