"""Independent whole-page native code-like scan for exact authority scope."""
from pathlib import Path
import collections,hashlib,json,re
import pymupdf
ROOT=Path.cwd();PRIVATE=ROOT/'var/private-evidence/se-ifa-peer'
def main():
 primary=json.loads((PRIVATE/'source-only-census.json').read_text());doc=pymupdf.open(ROOT/primary['source_path']);found=[];unexpected=[]
 for page in primary['page_scope']:
  for word in doc[page-1].get_text('words'):
   for match in re.finditer(r'(?<![A-Z0-9])E[MFI][A-Z0-9]+(?:[.-][A-Z0-9]+)*',word[4]):
    code=match.group()
    if not re.search(r'\d',code):continue
    occurrence={'page':page,'literal':code,'word':word[4],'bbox':list(word[:4])};found.append(occurrence)
    if re.fullmatch(r'EMIF[A-Z]+\d{2}',code)is None:unexpected.append(occurrence)
 result={'actor_type':'automated','source_id':primary['source_id'],'source_sha256':primary['source_sha256'],'method':'Whole40page primary native words scanned for broad EM/EF/EI uppercase identifier-like tokens with digits, independently of candidate and its cells.','code_like_occurrences':len(found),'unexpected_non_IFA_tokens':unexpected,'passed':len(found)==305 and not unexpected};(PRIVATE/'authority-code-scope.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(result)
if __name__=='__main__':main()
