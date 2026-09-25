from __future__ import annotations
import re
DASHES='-‐‑‒–—−'
CAS_PATTERN=re.compile(rf'(?<!\d)(\d{{2,7}})\s*[{re.escape(DASHES)}]\s*(\d{{2}})\s*[{re.escape(DASHES)}]\s*(\d)(?!\d)')
DIGITS_ONLY_PATTERN=re.compile(r'(?<!\d)(\d{5,10})(?!\d)')

def canonicalize_groups(a,b,c): return f'{a}-{b}-{c}'
def normalize_cas(value,*,allow_digits_only=False):
    if not value:return None
    m=CAS_PATTERN.search(str(value))
    if m:return canonicalize_groups(*m.groups())
    if allow_digits_only:
        token=re.sub(r'\D','',str(value))
        if 5<=len(token)<=10:return f'{token[:-3]}-{token[-3:-1]}-{token[-1]}'
    return None

def is_valid_cas(value):
    cas=normalize_cas(value,allow_digits_only=True)
    if not cas:return False
    a,b,c=cas.split('-'); digits=a+b
    return sum(int(d)*w for w,d in enumerate(reversed(digits),1))%10==int(c)

def extract_cas_candidates(text):
    out=[]
    for m in CAS_PATTERN.finditer(text or ''):
        cas=canonicalize_groups(*m.groups())
        if cas not in out:out.append(cas)
    return out

def extract_valid_cas(text):return [x for x in extract_cas_candidates(text) if is_valid_cas(x)]
def parse_manual_cas(text):
    valid=[]; invalid=[]; spans=[]
    for m in CAS_PATTERN.finditer(text or ''):
        cas=canonicalize_groups(*m.groups()); spans.append(m.span()); target=valid if is_valid_cas(cas) else invalid
        if cas not in target:target.append(cas)
    for m in DIGITS_ONLY_PATTERN.finditer(text or ''):
        if any(m.start()>=a and m.end()<=b for a,b in spans):continue
        t=m.group(); cas=f'{t[:-3]}-{t[-3:-1]}-{t[-1]}'; target=valid if is_valid_cas(cas) else invalid
        if cas not in target:target.append(cas)
    return valid,invalid
