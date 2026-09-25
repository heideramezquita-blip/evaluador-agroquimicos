from __future__ import annotations
import csv,re,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.engine import analyze
MASTER=ROOT/'data'/'master_restrictions.csv'
def pid(name):
 m=re.match(r'^(\d+(?:\.\d+)?)(?:\.|\s)',name);return m.group(1) if m else None
def eval_files(items):
 r=analyze([(p.name,p.read_bytes()) for p in items],master_path=MASTER);e=r['evaluation']
 return r,e
def one_doc(p):
 r,e=eval_files([p]);return {'file':str(p),'status':e.status,'processable':all(d.processable for d in r['documents']),'valid_cas':';'.join(x.cas for x in e.cas_records),'hits':' || '.join(f'{h.entry.ingredient}|{h.channel}|{h.context_class}|p{h.page}' for h in r['all_hits'])}
def pair_specs(corpus):
 out=[]
 for a,b,suite in [('FT','HS','principal'),('SFT','SHS','suplementario')]:
  fa={pid(p.name):p for p in (corpus/a).iterdir() if p.is_file() and p.suffix.lower()=='.pdf' and pid(p.name)};fb={pid(p.name):p for p in (corpus/b).iterdir() if p.is_file() and p.suffix.lower()=='.pdf' and pid(p.name)}
  for k in sorted(set(fa)&set(fb),key=lambda x:tuple(map(int,x.split('.')))):out.append((suite,k,fa[k],fb[k]))
 return out
def one_pair(spec):
 suite,k,ft,hs=spec;r,e=eval_files([ft,hs]);return {'suite':suite,'product_id':k,'ft':ft.name,'hs':hs.name,'status':e.status,'unprocessables':sum(not d.processable for d in r['documents']),'hits':' || '.join(f'{h.entry.ingredient}|{h.channel}|{h.context_class}|{h.source_file}|p{h.page}' for h in r['all_hits']),'decision_hits':' || '.join(f'{h.entry.ingredient}|{h.channel}|{h.context_class}|{h.source_file}|p{h.page}' for h in e.hits)}
def write(path,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
def main():
 corpus=Path(sys.argv[1]);pdfs=sorted(p for p in corpus.rglob('*') if p.is_file() and p.suffix.lower()=='.pdf');pairs=pair_specs(corpus)
 mode=sys.argv[2] if len(sys.argv)>2 else 'all'
 from collections import Counter
 if mode in ('docs','all'):
  with ProcessPoolExecutor(max_workers=12) as ex: docs=list(ex.map(one_doc,pdfs))
  write(ROOT/'validation_corpus_documents.csv',docs);print('PDF',len(docs),Counter(x['status'] for x in docs))
 if mode in ('pairs','all'):
  with ProcessPoolExecutor(max_workers=12) as ex: prs=list(ex.map(one_pair,pairs))
  write(ROOT/'validation_corpus_pairs.csv',prs);print('PARES',len(prs),Counter(x['status'] for x in prs))
if __name__=='__main__':main()
