from __future__ import annotations
import csv,re
from pathlib import Path
from .cas_utils import is_valid_cas
from .models import ProhibitedEntry
from .text_utils import normalize_text,match_key

GROUP_RULES={
 'arsenico y sus compuestos': {'terms':['arsenico','arsenical','arsenato','arsenito','arsonato','arseniato'], 'deterministic':False},
 'borax sales de borato': {'terms':['borax','borato','boratos','borate'], 'deterministic':True},
 'dnoc y sus sales': {'terms':['dnoc','dinitro orto cresol','dinitro-ortho-cresol'], 'deterministic':True},
 'formula en polvo dispersable que contiene una combinacion de benomilo 7 carbofurano 10 tiram 15': {'terms':['benomilo','carbofurano','tiram'], 'all_terms':True, 'deterministic':False},
 'sales e isomeros de glufosinato de amonio': {'terms':['glufosinato de amonio','glufosinato amonico','ammonium glufosinate','glufosinate ammonium'], 'deterministic':True},
 'mercurio y sus compuestos': {'terms':['mercurio','mercurico','mercuriosa','mercurioso','mercury'], 'deterministic':False},
 'aceites de parafina con un contenido de dmso 3': {'terms':['aceite de parafina','aceites de parafina','paraffin oil','paraffin oils'], 'deterministic':False},
 'compuestos de tributilestano': {'terms':['tributilestano','tributil estaño','tributyltin'], 'deterministic':True},
}

def _aliases(name:str)->list[str]:
    values=[]
    for part in re.split(r';',name):
        part=re.sub(r'\*+$','',part).strip()
        if part and len(normalize_text(part))>=4: values.append(part)
        stripped=re.sub(r'\([^)]*\)',' ',part).strip(' ,')
        if stripped and stripped!=part and len(normalize_text(stripped))>=4: values.append(stripped)
    out=[]
    for x in values:
        if normalize_text(x) not in {normalize_text(y) for y in out}:out.append(x)
    return out

class ProhibitedDatabase:
    LIST_FILES=('master_restrictions.csv','obsolete.csv','risk_mitigation.csv')
    def __init__(self,csv_path:str|Path):
        self.path=Path(csv_path); self.entries=[]; self.by_cas={}; self.specific=[]; self.groups=[]
        self.prohibited=[]; self.obsolete=[]; self.mitigation=[]
        paths=[self.path]
        for name in self.LIST_FILES[1:]:
            p=self.path.parent/name
            if p.exists(): paths.append(p)
        for path in paths:
            with path.open(encoding='utf-8-sig',newline='') as f:
                for row in csv.DictReader(f):
                    source_list=(row.get('source_list') or '').strip()
                    if source_list not in {'PROHIBITED','OBSOLETE','MITIGATE_RISK'}:continue
                    cas=(row.get('cas') or '').strip()
                    action=(row.get('action') or row.get('decision') or '').strip()
                    e=ProhibitedEntry(
                        (row.get('ingredient') or '').strip(),cas,(row.get('usage') or '').strip(),
                        (row.get('criteria') or '').strip(),(row.get('source_code') or '').strip(),
                        (row.get('source_version') or '').strip(),(row.get('source_date') or '').strip(),
                        not bool(cas),source_list,action
                    )
                    self.entries.append(e)
                    {'PROHIBITED':self.prohibited,'OBSOLETE':self.obsolete,'MITIGATE_RISK':self.mitigation}[source_list].append(e)
                    if cas:
                        if not is_valid_cas(cas):raise ValueError(f'CAS inválido en {source_list}: {cas}')
                        self.specific.append(e); self.by_cas.setdefault(cas,[]).append(e)
                    else:self.groups.append(e)
    def aliases(self,entry):return _aliases(entry.ingredient)
    def group_rule(self,entry):
        key=match_key(entry.ingredient)
        if entry.source_list=='PROHIBITED':
            return GROUP_RULES.get(key,{'terms':self.aliases(entry),'deterministic':False})
        return {'terms':self.aliases(entry),'deterministic':False}
