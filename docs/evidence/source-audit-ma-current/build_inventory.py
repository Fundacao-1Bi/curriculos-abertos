#!/usr/bin/env python3
"""Inventory exact indexed catalogue labels without inferring PDF identity or dates."""
from pathlib import Path
from datetime import datetime,timezone
import json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'docs/evidence/source-audit-ma-current'
COMP='https://sites.google.com/edu.ma.gov.br/sugeda/ensino-m%C3%A9dio/componentes-curriculares';EM='https://sites.google.com/edu.ma.gov.br/sugeda/ensino-m%C3%A9dio'
GROUPS=[
('Guias da Prática Docente','curricular_reference_candidate',[
'GPD 2026 - LINGUAGENS E SUAS TECNOLOGIAS.pdf','GPD 2026 - MATEMÁTICA E SUAS TECNOLOGIAS.pdf','GPD 2026 - CIÊNCIAS HUMANAS E SOCIAIS APLICADAS.pdf','GPD 2026 - CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS.pdf']),
('Parte Diversificada do Currículo / Educação Digital','typology_pending',[
'Moderna-Plus-Educacao-Digital-1 (2).pdf','Orientações Curriculares - Educação Digital.pdf','Cidadania Digital.pdf']),
('Parte Diversificada do Currículo / Eletivas de Base','curricular_reference_candidate',['CADERNO DE ELETIVAS DE BASE.pdf']),
('Identidade e Protagonismo','curricular_reference_candidate',[
'1ª SÉRIE - Identidade e Protagonismo - 22-JAN-26.pdf','2ª SÉRIE - Identidade e Protagonismo - 22-JAN-26.pdf','3ª SÉRIE - Identidade e Protagonismo - 22-JAN-26.pdf']),
('Materiais Complementares / Letramento','teaching_support_candidate',[
'Letramento P Professor COMPLETO.pdf','Letramento P Estudante COMPLETO.pdf','Letramento M Professor COMPLETO.pdf','Letramento M Estudante COMPLETO.pdf']),
('Aprofundamento de Itinerários Formativos Integrados','curricular_reference_candidate',['Fascículo AIFI.pdf','AIFI - 3ª SÉRIE.pdf']),
('Ensino Médio / Materiais Complementares','curricular_reference_candidate',[
'CADERNO DE ORIENTAÇÕES CURRICULARES PARA A REDE ESTADUAL (2).pdf','DCTMA - ENSINO MÉDIO.pdf','CADERNO DE MATRIZES 2026.pdf','Guia do Estudante 2026.pdf'])]
def main():
 entries=[]
 for group,typology,titles in GROUPS:
  for title in titles:
   entry={'key':f'catalogue-{len(entries)+1:02}','group_label':group,'file_label':title,'landing_url':EM if group.startswith('Ensino Médio') else COMP,'observation_method':'web_search_index_visible_catalogue_text','direct_http_status':'authentication_redirect_stopped','artifact_url':None,'artifact_sha256':None,'edition':None,'document_date':None,'application_period':None,'classification':typology,'mandatory_status':'not_established_from_label','identity_status':'PDF bytes and embedded file ID not obtained','actor_type':'automated'}
   if title=='DCTMA - ENSINO MÉDIO.pdf':entry.update(existing_source_candidate='ma-dctm-em-vol2',dedup_note='Catalogue identifies volumeII; no second PDF acquired or byte-equivalence inferred.')
   if title=='Guia do Estudante 2026.pdf':entry['classification']='orientation_support_candidate'
   if title=='Orientações Curriculares - Educação Digital.pdf':entry['scope_note']='EM catalogue resource; identity with the separate Basic Education complement approved by Resolution211 is NOT established.'
   entries.append(entry)
 assert len(entries)==21
 data={'at':datetime.now(timezone.utc).isoformat(),'actor_type':'automated','actor_id':'agent:rs_adapter:ma-current-inventory','denominator_definition':'Distinct visible PDF labels in indexed SUGEDA EM/components catalogue, grouped before acquisition. No codes or learning extraction used as denominator.','total_catalogue_labels':21,'new_candidate_labels':20,'existing_source_candidates':1,'matrix_duplicate_in_management_page':'CADERNO DE MATRIZES 2026.pdf also appears at gestão-escolar; treated as same catalogue label, PDF identity unverified.','entries':entries,'scope_limit':'A label in a search index does not prove current public access, file identity, official adoption, editorial date, revocation, or structured-learning completeness.'}
 (OUT/'indexed-catalogue-inventory.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'labels':21,'new_candidates':20,'existing_candidates':1}))
if __name__=='__main__':main()
