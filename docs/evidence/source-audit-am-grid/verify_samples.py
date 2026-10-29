#!/usr/bin/env python3
"""Real-page positive and negative regressions for the raster/TSV adapter."""
import hashlib
import json
import sys
from pathlib import Path
import pymupdf

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from am_ocr_grid import REVISION,extract_grid_items
from ingest import clean_text,make_item
from ocr import ocr_page

sources=json.loads((ROOT/'data/manifests/north.json').read_text())
checks=[]
for source_id,page_number in [('am-rca-em',40),('am-rca-ef-af',106),('am-rca-ei',69),('am-rca-ef-ai',120)]:
    source=next(s for s in sources if s['id']==source_id)
    with pymupdf.open(ROOT/source['local_path'])as document:
        page=document[page_number-1];page.remove_rotation();ocr=ocr_page(page,source,page_number)
        items,report=extract_grid_items(source,page,page_number,ocr,make_item,clean_text)
    bycode={item.get('code')or item.get('candidate_code'):item for item in items}
    if source_id=='am-rca-em':
        actual=bycode['EM13LGG101']['text']
        expected='Compreender e analisar processos de produção e circulação de discursos, nas diferentes linguagens, para fazer escolhas fundamentadas em função de interesses pessoais e coletivos.'
        assertions={'full_primary_skill':actual==expected,'next_skill_words_excluded':'preconceitos'not in actual,'nine_primary_rows':len(items)==9,'printed_footer_excluded':bycode['EM13LGG204']['text'].endswith('Direitos Humanos.')}
    elif source_id=='am-rca-ef-af':
        actual=bycode['EF67LP03']['text']
        expected='Comparar informações sobre um mes- mo fato divulgadas em diferentes veículos e mídias, analisando e avaliando a confiabilidade.'
        candidate=bycode['EF67LP07']
        assertions={'full_primary_skill':actual==expected,'object_column_excluded':'Relação entre textos'not in actual,'detail_column_excluded':'contexto amazônico'not in actual,'five_primary_skills':len(items)==5,'ambiguous_code_not_official':candidate['code']is None and candidate['ocr_source_code_token']=='EFG7LPO7'}
    elif source_id=='am-rca-ei':
        actual=bycode['EI01EO01']['text'];expected='Perceber que suas ações têm efeitos nas outras crianças e nos adultos.'
        assertions={'first_primary_objective':actual==expected,'three_physical_columns':len(report['grid']['columns'])==3,'five_printed_code_occurrences':len(items)==5,'no_silent_code_repairs':all(item['code']is None for item in items),'neighbor_age_text_excluded':'solidarieda'not in actual and'empatia'not in actual,'separate_local_code_preserved':'EI01EO01-AM'in bycode}
    else:
        actual=bycode['EF12LP03']['text'];expected='Copiar textos breves, mantendo suas características e voltando para o texto sempre que tiver dúvidas sobre sua distribuição gráfica espaçamento entre as palavras, escrita das palavras e pontuação.'
        assertions={'full_primary_skill':actual==expected,'object_column_excluded':'Construção do sistema alfabético'not in actual,'teacher_guidance_excluded':'Semelhanças e diferenças'not in actual,'one_primary_skill':len(items)==1}
    checks.append({'source_id':source_id,'artifact_sha256':source['sha256'],'page':page_number,'assertions':assertions,'passed':all(assertions.values()),'raw_OCR_sha256':ocr['result_sha256'],'raster_sha256':report['grid']['raster_sha256'],'canonical_excerpt':actual,'expected_excerpt':expected,'visual_source':'Original page rendered and inspected by automated agent; no human review claimed.'})

report={'revision':REVISION,'helper_sha256':hashlib.sha256((ROOT/'pipeline/am_ocr_grid.py').read_bytes()).hexdigest(),'passed':all(check['passed']for check in checks),'checks':checks,'scope':'Primary visual samples for each scanned AM document plus negative column/next-row/footer/code-repair assertions. This does not assert full OCR character accuracy on every page.'}
(Path(__file__).parent/'real-sample-regressions.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'checks':sum(len(check['assertions'])for check in checks),'source_pages':len(checks)},ensure_ascii=False))
raise SystemExit(0 if report['passed']else 1)
