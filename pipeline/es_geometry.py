"""Exact-artifact ES physical table geometry and narrowly scoped native reading.

Remove nested, same-color text-line background fills only from table detection
input. Keep original full-cell fills and all border/rule paths. No PDF pixels,
source characters, spelling, code suffixes or source bytes are rewritten.

Evidence: docs/evidence/source-audit-southeast-fidelity/. These technical rules
are automated extraction, not human pedagogical review or completeness approval.
"""
from __future__ import annotations
import math
import re

SOURCE_ARTIFACTS = {
 'es-curr-culo-es-2019-vol-02-ensino-fundamental-anos-iniciais-rea-de-ci-ncias-da-natureza-e-matem-tica-m': 'b989ff3253f2346b3de8dbe5548f47608e8a35d302e43c956ed38ca3e1a7e9f5',
 'es-curr-culo-es-2019-vol-03-ensino-fundamental-anos-iniciais-rea-de-ci-ncias-humanas-e-ensino-religioso': 'cba0bfc2bda6e2985e91794eb990a1e4b2a7286d11117fb9db5ac82dd9ab1a0e',
 'es-curr-culo-es-2019-vol-04-ensino-fundamental-anos-iniciais-rea-de-linguagens-arte-e-educa-o-f-sica-mi': '682dea442ac105bf3be3d49d8c4d70b2f2b024e97dc3007207b357bc52309925',
 'es-curr-culo-es-2019-vol-05-ensino-fundamental-anos-iniciais-rea-de-linguagens-l-ngua-portuguesa-miolo': 'e0ab216989ee5c743722d00e5526629e44f7d8aa192e614ff6e37de7928857c2',
 'es-curr-culo-es-2020-vol-06-ensino-fundamental-anos-finais-rea-de-ci-ncias-da-natureza-e-matem-tica-mio': '04cf2e73e969a862e1fb8f7e439844d6a7914c2e4a6501a4d32480b29377d149',
 'es-curr-culo-es-2020-vol-07-ensino-fundamental-anos-finais-rea-de-ci-ncias-humanas-e-ensino-religioso-m': '0cea37413af8c794f4527e2ff0317dc0a93502111bb6e266bd99794414cf2142',
 'es-curr-culo-es-2020-vol-08-ensino-fundamental-anos-finais-rea-de-linguagens-arte-educa-o-f-sica-e-l-ng': '9609375a9630bc434f56f0c5ee3de908f1238b2b2c9d7e288f0f9d79264d7eee',
 'es-curr-culo-es-2020-vol-09-ensino-fundamental-anos-finais-rea-de-linguagens-l-ngua-portuguesa-miolo': '6bc96909d0199bd9e59d0ce4d8076eea069077ccd47f7a6a43b9f2064d2d9871',
 'es-em-l-ngua-portuguesa': 'b3405b1e5ffeb82df9d2817e86e8949199c3ae14c9cd59daf69b69bac48773d8',
 'es-em-ci-ncias-da-natureza': 'ed9771b0dd051602a41e3706f3453a6301f8c48fd20911b9b821e96256daa1ac',
 'es-em-ci-ncias-humanas': 'de0a2853b8ff2346830f9f1b0f29616912ca7ac4237b6ce050f91781afb486f6',
 'es-ifa-lingchsa-6-1': 'd5ac69230fe71ac97de5c6fe0953a6a627da35bb3348fe1738c907c4ed3161cf',
 'es-curriculoem-aprofundamento-da-area-de-chsa': 'a5f9bc957d202514209462c4f8a76e1b3b3270fe9818d01fadd7cc09c827de80',
 'es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22': '23223e7993fd20bf59642c94a5503e909b311aec739255dcf4d362ea21edf6f1',
 'es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22': '0abd9718b7b02fd6b5e49e5f0e722a7eb4af8f18872c3caa4a652daca3c1a662',
}
PADDING_PAGES = {'es-curriculoem-aprofundamento-da-area-de-chsa': {35,42,49}, 'es-curriculo-em-aprofundamento-entreareas-chsa-e-cn-alterado-20-04-22': {31,36}}
PHYSICAL_BASELINE_PAGES = {'es-curriculo-em-aprofundamento-entreareas-cn-chsa-mat-e-linguagens-alterado-20-04-22': {47}}

def _enabled(source):
 return SOURCE_ARTIFACTS.get(source.get('id')) == source.get('sha256') and source.get('id') in SOURCE_ARTIFACTS

def filtered_table_paths(page,max_nested_height=22):
 """Return table-detection paths and every removed fill with its physical parent."""
 paths=page.get_drawings();fills=[]
 for index,path in enumerate(paths):
  if path.get('type')!='f' or path.get('fill_opacity')!=1 or path.get('fill') is None:continue
  for item in path['items']:
   if item[0]=='re':fills.append((index,item[1],tuple(path['fill'])))
 removed=[]
 for index,rect,color in fills:
  if len(paths[index]['items'])!=1 or not (3<rect.height<max_nested_height and rect.width>30):continue
  parent=next(((j,box) for j,box,parent_color in fills if j!=index and parent_color==color and box.x0<=rect.x0+.1 and box.y0<=rect.y0+.1 and box.x1>=rect.x1-.1 and box.y1>=rect.y1-.1 and ((box.width-rect.width>=4 and box.height-rect.height>=2) or (box.width-rect.width>=-.2 and box.height-rect.height>=40))),None)
  if parent:
   removed.append({'index':index,'seqno':paths[index]['seqno'],'bbox':list(rect),'color':list(color),'parent_index':parent[0],'parent_bbox':list(parent[1]),'reason':'Same-color opaque text-line fill nested in a larger full-cell background; original source drawings remain unchanged.'})
 indices={record['index'] for record in removed}
 return [path for index,path in enumerate(paths) if index not in indices],removed

def table_detection_configuration(source,page,pn):
 if not _enabled(source):return {},None
 max_height=64 if source['id']=='es-ifa-lingchsa-6-1' else 22
 paths,removed=filtered_table_paths(page,max_nested_height=max_height)
 if not removed:return {},None
 return {'paths':paths},{'method':'es-nested-text-background-table-paths-v1','source_id':source['id'],'artifact_sha256':source['sha256'],'page':pn,'excluded_text_backgrounds':removed,'max_nested_fill_height':max_height,'source_bytes_modified':False,'rule_paths_removed':False}

def _physical_text(page,bbox):
 from ms_glyphs import rendered_glyph_runs
 rows=[]
 for run in rendered_glyph_runs(page,bbox):
  row=next((candidate for candidate in reversed(rows) if abs(candidate[0]['baseline']-run['baseline'])<=.75),None)
  if row is None:rows.append([run])
  else:row.append(run)
 lines=[]
 for row in rows:
  row.sort(key=lambda run:run['bbox'][0]);text='';prior=None
  for run in row:
   if prior and text and not text[-1].isspace() and not run['text'][0].isspace() and run['bbox'][0]-prior['bbox'][2]>1:text+=' '
   text+=run['text'];prior=run
  lines.append(re.sub(r'\s+',' ',text).strip())
 return '\n'.join(lines)

def cell_text(source,page,pn,bbox):
 """Return an exact-source override only for the six documented pages.

 Five cell right edges exclude printed commas by <1pt; read the physical 1pt
 margin. Energias47 has letters with .48pt baseline displacement inside words;
 join visible runs within .75pt (source lines are10.56pt apart), no dictionary.
 """
 if not _enabled(source) or bbox is None:return None
 if len(bbox)!=4 or not all(isinstance(n,(int,float)) and math.isfinite(n) for n in bbox):raise ValueError('Invalid ES source cell bbox')
 if pn in PHYSICAL_BASELINE_PAGES.get(source['id'],set()):return _physical_text(page,bbox)
 if pn in PADDING_PAGES.get(source['id'],set()):
  from native_glyphs import NativeGlyphText
  box=[bbox[0]-1,bbox[1]-1,bbox[2]+1,bbox[3]+1]
  return NativeGlyphText(page).text(box)
 return None

# Complete physical continuation census for this exact IFA artifact.
IFA_CONTINUATIONS = ({'code': 'EMIFALGG102', 'start_page': 52, 'code_bbox': [238.4600067138672, 458.2008056640625, 330.2256774902344, 471.5812683105469], 'start_bbox': [230.18000520978654, 448.847998046875, 925.2694509405839, 488.15999603271484], 'continuation_page': 53, 'continuation_bbox': [230.06000518798828, 61.82148742675781, 925.6199951171875, 445.0559997558594], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'bac07b38282082e047eedfc68fdf2fa6a0d8932946bdeb0ca6d5ff224db2110b'}, {'code': 'EMIFALGG604', 'start_page': 70, 'code_bbox': [236.05999755859375, 434.32080078125, 332.2293701171875, 447.7012939453125], 'start_bbox': [226.8527235551314, 322.9915008544922, 931.9753840519832, 464.9759979248047], 'continuation_page': 71, 'continuation_bbox': [226.53199462890626, 62.0360107421875, 932.2000122070312, 110.0615005493164], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '1e95bbcb757ed848ecb491cf420352fa555eb2dc589589bcd0a0f584839f20d6'}, {'code': 'EMIFALGG103', 'start_page': 104, 'code_bbox': [240.6199951171875, 381.884765625, 331.3056640625, 395.2652587890625], 'start_bbox': [231.49555997495298, 290.95249938964844, 926.4694952713816, 399.5800018310547], 'continuation_page': 105, 'continuation_bbox': [231.33200073242188, 62.0360107421875, 926.9200032552084, 110.06000518798828], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'ccb683e06dd52831ad36614a251cbf4635a0ad8eb47e92f046309077f25a27de'}, {'code': 'EMIFALGG501', 'start_page': 148, 'code_bbox': [239.89999389648438, 405.7647705078125, 342.4656677246094, 419.145263671875], 'start_bbox': [231.05600179036458, 388.2090072631836, 926.1899948120117, 463.38600158691406], 'continuation_page': 149, 'continuation_bbox': [231.02000045776367, 60.86250305175781, 926.6799926757812, 189.6490020751953], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'aa191ac2abe376ee417b3d60f840d57a989f0f333746049bf23c91cee2a5266b'}, {'code': 'EMIFACHS301', 'start_page': 155, 'code_bbox': [172.22000122070312, 454.00079345703125, 262.99566650390625, 467.38128662109375], 'start_bbox': [163.09555957935476, 335.1114959716797, 930.0694869192023, 473.67599868774414], 'continuation_page': 156, 'continuation_bbox': [162.9800033569336, 64.22251892089844, 930.280019124349, 222.73899459838867], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'c79ac436f34376486a75530f6c63bac9fead3d54873d0352f5cb5bef773f5218'}, {'code': 'EMIFACHS301', 'start_page': 171, 'code_bbox': [172.4600067138672, 446.4407958984375, 263.23565673828125, 459.8212890625], 'start_bbox': [163.09555957935476, 327.67150115966797, 930.3726324784128, 466.9860076904297], 'continuation_page': 172, 'continuation_bbox': [162.9800033569336, 64.2225112915039, 930.52001953125, 197.5689926147461], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'c79ac436f34376486a75530f6c63bac9fead3d54873d0352f5cb5bef773f5218'}, {'code': 'EMIFACHS304', 'start_page': 179, 'code_bbox': [179.66000366210938, 441.040771484375, 269.23565673828125, 454.4212646484375], 'start_bbox': [166.69555692319517, 293.5014953613281, 930.0694869192023, 457.14600372314453], 'continuation_page': 180, 'continuation_bbox': [166.5320068359375, 51.596014404296874, 930.280029296875, 88.46150970458984], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '39172275e6a06ea5882467153abe2c886101cd9a3b28227964f36c6661c1bbca'}, {'code': 'EMIFACHS404', 'start_page': 195, 'code_bbox': [179.66000366210938, 440.080810546875, 269.23565673828125, 453.4612731933594], 'start_bbox': [168.25555250379773, 329.9814987182617, 930.0694869192023, 456.54600524902344], 'continuation_page': 196, 'continuation_bbox': [168.02000045776367, 51.470001220703125, 930.1199951171875, 138.83000946044922], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '6c72028d0b77b3b1220f38b67f09909dfaf1359eab688e0ca7ef31744e3fcc0a'}, {'code': 'EMIFACHS203', 'start_page': 204, 'code_bbox': [177.02000427246094, 415.12481689453125, 277.75567626953125, 428.5052795410156], 'start_bbox': [167.46888930709272, 336.3115005493164, 929.8926520096628, 447.8159942626953], 'continuation_page': 205, 'continuation_bbox': [167.29999923706055, 51.50251007080078, 930.1599934895834, 178.03899383544922], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '78ef873fa062b21389e7abaee9b1f0e9bb7bf4f3bd12ad5c38f875ccd3a461e3'}, {'code': 'EMIFACHS303', 'start_page': 216, 'code_bbox': [173.66000366210938, 454.00079345703125, 265.5156555175781, 467.38128662109375], 'start_bbox': [166.69555692319517, 306.31150817871094, 930.0694869192023, 469.89601135253906], 'continuation_page': 217, 'continuation_bbox': [166.5320068359375, 64.316015625, 930.280029296875, 117.14149475097656], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '22059f313964f194d2be672cdcc842f08080bb58b8437bd804c79d3ae323a91a'}, {'code': 'EMIFACHS404', 'start_page': 229, 'code_bbox': [174.3800048828125, 460.36077880859375, 265.0356750488281, 473.74127197265625], 'start_bbox': [167.46888930709272, 321.67150115966797, 933.7326435289884, 476.37599182128906], 'continuation_page': 230, 'continuation_bbox': [167.29999923706055, 64.22251892089844, 934.1199951171875, 208.36900329589844], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': '6c72028d0b77b3b1220f38b67f09909dfaf1359eab688e0ca7ef31744e3fcc0a'}, {'code': 'EMIFACHS301', 'start_page': 241, 'code_bbox': [172.4600067138672, 452.080810546875, 263.11566162109375, 465.4612731933594], 'start_bbox': [162.85556058530454, 341.47149658203125, 929.8294966848273, 468.3360137939453], 'continuation_page': 242, 'continuation_bbox': [162.7400016784668, 64.22000885009766, 930.4000244140625, 132.50150299072266], 'continuation_locator': 'table:0/row:0/cell:1', 'expected_continuation_sha256': 'c79ac436f34376486a75530f6c63bac9fead3d54873d0352f5cb5bef773f5218'})

CONTEXT_REFERENCE_RULES = ({'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG102', 'code_bbox': [235.33999633789062, 161.27479553222656, 431.1360778808594, 174.6552734375], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG103', 'code_bbox': [235.33999633789062, 161.27479553222656, 431.1360778808594, 174.6552734375], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG501', 'code_bbox': [415.25, 214.67478942871094, 866.1860961914062, 228.05526733398438], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG502', 'code_bbox': [415.25, 214.67478942871094, 866.1860961914062, 228.05526733398438], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG503', 'code_bbox': [415.25, 214.67478942871094, 866.1860961914062, 228.05526733398438], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG303', 'code_bbox': [235.33999633789062, 268.33477783203125, 506.7560729980469, 281.71527099609375], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG304', 'code_bbox': [235.33999633789062, 268.33477783203125, 506.7560729980469, 281.71527099609375], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG501', 'code_bbox': [235.33999633789062, 321.73480224609375, 593.51611328125, 335.11529541015625], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG502', 'code_bbox': [235.33999633789062, 321.73480224609375, 593.51611328125, 335.11529541015625], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 54, 'code': 'EMIFALGG503', 'code_bbox': [235.33999633789062, 321.73480224609375, 593.51611328125, 335.11529541015625], 'field_bbox': [230.02571977887834, 133.94248962402344, 925.5299987792969, 430.7303894042969], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 71, 'code': 'EMIFALGG501', 'code_bbox': [233.17999267578125, 458.32080078125, 762.6260986328125, 471.7012939453125], 'field_bbox': [226.53199462890626, 110.0615005493164, 932.2000122070312, 478.53599548339844], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 71, 'code': 'EMIFALGG601', 'code_bbox': [233.17999267578125, 458.32080078125, 762.6260986328125, 471.7012939453125], 'field_bbox': [226.53199462890626, 110.0615005493164, 932.2000122070312, 478.53599548339844], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 71, 'code': 'EMIFALGG604', 'code_bbox': [233.17999267578125, 458.32080078125, 762.6260986328125, 471.7012939453125], 'field_bbox': [226.53199462890626, 110.0615005493164, 932.2000122070312, 478.53599548339844], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 105, 'code': 'EMIFALGG101', 'code_bbox': [237.74000549316406, 117.68479919433594, 328.4256591796875, 131.06527709960938], 'field_bbox': [231.33200073242188, 110.06000518798828, 926.9200032552084, 486.69000244140625], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 105, 'code': 'EMIFALGG103', 'code_bbox': [237.74000549316406, 392.5648193359375, 328.4256591796875, 405.9452819824219], 'field_bbox': [231.33200073242188, 110.06000518798828, 926.9200032552084, 486.69000244140625], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 115, 'code': 'EMIFALGG201', 'code_bbox': [237.25999450683594, 352.8148193359375, 327.9456787109375, 366.1952819824219], 'field_bbox': [231.02000045776367, 351.3415069580078, 926.6399917602539, 482.46600341796875], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 116, 'code': 'EMIFALGG202', 'code_bbox': [237.25999450683594, 63.32481384277344, 327.9456787109375, 76.70529174804688], 'field_bbox': [231.02000045776367, 61.94151306152344, 926.7599945068359, 480.5760040283203], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 116, 'code': 'EMIFALGG203', 'code_bbox': [237.25999450683594, 373.12481689453125, 327.9456787109375, 386.5052795410156], 'field_bbox': [231.02000045776367, 61.94151306152344, 926.7599945068359, 480.5760040283203], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 127, 'code': 'EMIFALGG503', 'code_bbox': [236.3000030517578, 285.61480712890625, 326.98565673828125, 298.99530029296875], 'field_bbox': [229.82000350952148, 284.38001251220703, 926.6799926757812, 487.1999969482422], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 128, 'code': 'EMIFALGG304', 'code_bbox': [236.3000030517578, 112.52479553222656, 326.98565673828125, 125.9052734375], 'field_bbox': [229.77200317382812, 61.94251251220703, 926.6799926757812, 425.4743896484375], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-ifa-lingchsa-6-1', 'page': 128, 'code': 'EMIFALGG402', 'code_bbox': [236.3000030517578, 215.15480041503906, 326.98565673828125, 228.5352783203125], 'field_bbox': [229.77200317382812, 61.94251251220703, 926.6799926757812, 425.4743896484375], 'reason': 'Code cited in an explicitly labelled Objetos de Conhecimento field, including its physically continuous top cell; not a new definition.'}, {'source_id': 'es-curr-culo-es-2019-vol-03-ensino-fundamental-anos-iniciais-rea-de-ci-ncias-humanas-e-ensino-religioso', 'page': 79, 'code': 'EF01GE05/ES', 'code_bbox': [102.23999876134536, 137.4000015258789, 357.4799975226907, 239.9314226422991], 'field_bbox': [102.23999876134536, 137.4000015258789, 357.4799975226907, 239.9314226422991], 'reason': 'The source repeats the full p78 skill inside its Competências Específicas mapping column. Keep this occurrence as documentary context, not another learning definition.'})

def rewrite_page(source,pn,page,tables,items,code_re,make_item,clean_text):
 """Complete all twelve independently proved IFA source-cell continuations.

 Existing anchor IDs/locators survive. The single omitted code-only anchor104
 is created at its actual cell. Text is read again from the original PDF; this
 is not a transcription constant or a general permission to borrow later prose.
 The caller must avoid appending an already resolved continuation a second time.
 """
 if not _enabled(source):return items,None
 rules=[rule for rule in IFA_CONTINUATIONS if source['id']=='es-ifa-lingchsa-6-1' and rule['start_page']==pn]
 references=[rule for rule in CONTEXT_REFERENCE_RULES if rule['source_id']==source['id'] and rule['page']==pn]
 if not rules and not references:return items,None
 from geometry import normalize_native_page
 from native_glyphs import NativeGlyphText
 report={'method':'es-ifa-complete-physical-continuation-census-v1','source_id':source['id'],'artifact_sha256':source['sha256'],'page':pn,'actor_type':'automated','checks':[],'reference_checks':[]}
 from native_glyphs import NativeGlyphText
 for reference in references:
  literal=NativeGlyphText(page).text(reference['code_bbox'])
  if re.sub(r'\s+','',reference['code']) not in re.sub(r'\s+','',literal):raise ValueError('ES contextual reference code not proved in its source field')
  field=reference['field_bbox'];matched=[]
  for item in items:
   if item.get('code')!=reference['code'] or not item.get('evidence') or item['evidence'][0].get('page')!=pn:continue
   box=item['evidence'][0].get('bbox')
   if not box:continue
   x,y=(box[0]+box[2])/2,(box[1]+box[3])/2
   if not(field[0]<=x<=field[2] and field[1]<=y<=field[3]):continue
   item['kind']='referencia_no_documento';item['positions']=[];item['position_unknown_reason']=reference['reason']
   item.setdefault('source_context',{})['explicit_contextual_code_role']={'method':'es-complete-context-field-census-v1','field_bbox':field,'original_code_bbox':reference['code_bbox'],'reason':reference['reason'],'actor_type':'automated','human_review':False}
   matched.append(item['id'])
  report['reference_checks'].append({'code':reference['code'],'source_field_bbox':field,'matched_item_ids':matched})
 for rule in rules:
  # Match the full source cell, not a nearby paragraph or a source code elsewhere.
  expected=rule['start_bbox'];located=[]
  for ti,table in enumerate(tables):
   for ri,row in enumerate(table.rows):
    for ci,box in enumerate(row.cells):
     if box and max(abs(a-b) for a,b in zip(box,expected))<.15:located.append((ti,ri,ci,list(box)))
  if not located:raise ValueError(f'IFA continuation start cell changed: page{pn} {rule["code"]}')
  ti,ri,ci,box=located[0];locator=f'table:{ti}/row:{ri}/cell:{ci}'
  reader=NativeGlyphText(page);proof=reader.text(rule['code_bbox'])
  if re.sub(r'\s+','',rule['code']) not in re.sub(r'\s+','',proof):raise ValueError('IFA continuation code anchor not proved')
  raw=reader.text(box);matches=list(code_re.finditer(raw))
  if not matches or matches[-1].group()!=rule['code']:raise ValueError('IFA continuation is not the final code in its original cell')
  first=clean_text(re.sub(r'^[\s():;\-–—]+','',raw[matches[-1].end():]))
  following=page.parent[rule['continuation_page']-1];normalization=normalize_native_page(following)
  if normalization['original_rotation'] or normalization['native_body_rotation_applied']:raise ValueError('Unexpected rotation on exact IFA continuation source')
  tail=NativeGlyphText(following).text(rule['continuation_bbox']);next_code=code_re.search(tail)
  if next_code:tail=tail[:next_code.start()].rstrip().rstrip('(')
  tail=clean_text(tail)
  if __import__('hashlib').sha256(tail.encode()).hexdigest()!=rule['expected_continuation_sha256']:raise ValueError(f'IFA continuation differs from proved source prose: {pn} {rule["code"]}')
  full=(first+' '+tail).strip();candidates=[item for item in items if item.get('code')==rule['code'] and item.get('evidence') and item['evidence'][0].get('page')==pn and item['evidence'][0].get('locator')==locator]
  if len(candidates)>1:raise ValueError('Ambiguous IFA continuation anchor')
  created=not candidates
  if candidates:item=candidates[0]
  else:
   if first:raise ValueError('A nonempty IFA starting definition disappeared unexpectedly')
   item=make_item(source,rule['code'],full,pn,'es-ifa-physical-cell-continuation-v1',locator,context='Habilidade do IFA com continuação na célula física seguinte',quality='source_cell_continuation_proved')
   items.append(item)
  item['text']=full
  item['normalized_text']=make_item(source,rule['code'],full,pn,'es-ifa-physical-cell-continuation-v1',locator)['normalized_text']
  # Preserve existing source geometry/context and record the exact new proof.
  first_evidence=dict(item['evidence'][0]);first_evidence.update(excerpt=first if first else rule['code'],bbox=box if first else rule['code_bbox'])
  if not first:first_evidence['evidence_role']='code_locator'
  continuation={'source_id':source['id'],'page':rule['continuation_page'],'printed_page':None,'section':'Continuação da mesma célula de Habilidades do IFA','excerpt':tail,'locator':rule['continuation_locator'],'bbox':rule['continuation_bbox'],'method':'es-ifa-physical-cell-continuation-v1','coordinate_space':'display_pdf_after_remove_rotation','actor_type':'automated'}
  item['evidence']=[first_evidence,continuation];item['cross_page_continuation']=True
  item['resolved_source_continuation_pages']=[rule['continuation_page']]
  item['extraction_flags']=[flag for flag in item.get('extraction_flags',[]) if flag not in ('possible_page_continuation','code_only_waiting_page_continuation')]
  item.setdefault('source_context',{})['physical_continuation']={'method':report['method'],'start_page':pn,'continuation_page':rule['continuation_page'],'start_cell_bbox':box,'continuation_cell_bbox':rule['continuation_bbox'],'original_code_anchor_bbox':rule['code_bbox'],'actor_type':'automated','human_review':False}
  report['checks'].append({'code':rule['code'],'locator':locator,'created_missing_code_only_anchor':created,'start_text_nonempty':bool(first),'continuation_page':rule['continuation_page'],'text_sha256':__import__('hashlib').sha256(full.encode()).hexdigest()})
 return items,report
