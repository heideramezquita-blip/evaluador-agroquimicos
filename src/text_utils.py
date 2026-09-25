from __future__ import annotations
import re, unicodedata

def normalize_text(value:str)->str:
    value=unicodedata.normalize('NFKD',value or '')
    value=''.join(c for c in value if not unicodedata.combining(c)).lower()
    value=value.translate(str.maketrans({'‐':'-','‑':'-','‒':'-','–':'-','—':'-','−':'-','\u00a0':' '}))
    value=re.sub(r'[^a-z0-9%+./-]+',' ',value)
    return re.sub(r'\s+',' ',value).strip()

def compact_context(lines):return ' | '.join(x.strip() for x in lines if x.strip())
def match_key(value:str)->str:
    return re.sub(r'[^a-z0-9]+',' ',normalize_text(value)).strip()

def phrase_present(text:str, phrase:str)->bool:
    t=' '+match_key(text)+' '; p=match_key(phrase)
    return bool(p) and (' '+p+' ') in t
