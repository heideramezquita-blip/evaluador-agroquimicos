from __future__ import annotations
from collections import OrderedDict
from .cas_utils import CAS_PATTERN,canonicalize_groups,is_valid_cas
from .models import CasOccurrence,CasRecord,PdfDocument
from .text_utils import normalize_text

def _local_context(text,start,end,radius=350):
    return recompact(text[max(0,start-radius):min(len(text),end+radius)])
def recompact(s):return ' | '.join(x.strip() for x in s.splitlines() if x.strip())
def _role(context):
    n=normalize_text(context)
    return 'active_explicit' if any(x in n for x in ('ingrediente activo','ingredientes activos','active ingredient')) else 'unknown'

def extract_document_cas(document:PdfDocument):
    by=OrderedDict(); invalid=[]
    for page in document.pages:
        text=page.text or ''
        for m in CAS_PATTERN.finditer(text):
            cas=canonicalize_groups(*m.groups()); context=_local_context(text,m.start(),m.end())
            if not is_valid_cas(cas):
                invalid.append({'candidate':cas,'source_file':document.file_name,'page':page.page,'context':context}); continue
            occ=CasOccurrence(cas,document.file_name,page.page,'document',_role(context),context)
            by.setdefault(cas,CasRecord(cas)).occurrences.append(occ)
    return list(by.values()),invalid

def merge_cas_records(groups):
    by=OrderedDict()
    for records in groups:
        for r in records:
            target=by.setdefault(r.cas,CasRecord(r.cas))
            for o in r.occurrences:
                if not any((x.source_file,x.page,x.context,x.source)==(o.source_file,o.page,o.context,o.source) for x in target.occurrences):target.occurrences.append(o)
    return list(by.values())
