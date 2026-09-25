from __future__ import annotations
from .context_classifier import classify_context
from .models import EvidenceHit,PdfDocument
from .text_utils import normalize_text,phrase_present,match_key

def _line_context(text:str,needle:str,radius_lines=8):
    lines=text.splitlines(); nn=match_key(needle)
    tokens=[t for t in nn.split() if len(t)>=4]
    for i,line in enumerate(lines):
        lk=match_key(line)
        if nn and (nn in lk or (tokens and tokens[0] in lk)):
            context=' | '.join(x.strip() for x in lines[max(0,i-radius_lines):min(len(lines),i+radius_lines+1)] if x.strip())
            if phrase_present(context,needle):
                return context
    return text[:700]

def _name_hits(document:PdfDocument,db):
    hits=[]
    for page in document.pages:
        if not page.text:continue
        for entry in db.specific:
            for alias in db.aliases(entry):
                if phrase_present(page.text,alias):
                    context=_line_context(page.text,alias); cls=classify_context(context,alias)
                    hits.append(EvidenceHit(entry,'NAME',alias,document.file_name,page.page,context,cls,'exact_name','Coincidencia nominal exacta/normalizada con PROHIBIDOS.'))
                    break
        for entry in db.groups:
            rule=db.group_rule(entry); terms=rule['terms']
            if rule.get('all_terms'):
                present=all(phrase_present(page.text,t) for t in terms)
                if not present:continue
                alias=' + '.join(terms); context=page.text[:1200]
            else:
                alias=next((t for t in terms if phrase_present(page.text,t)),None)
                if not alias:continue
                context=_line_context(page.text,alias)
            cls=classify_context(context,alias)
            strength='group_deterministic' if rule.get('deterministic') else 'group_candidate'
            hits.append(EvidenceHit(entry,'GROUP_NAME',alias,document.file_name,page.page,context,cls,strength,'Coincidencia dirigida con un registro de grupo/familia de PROHIBIDOS.'))
    return hits

def detect_candidates(documents,cas_records,db):
    hits=[]
    for record in cas_records:
        for entry in db.by_cas.get(record.cas,[]):
            for occ in record.occurrences:
                cls=classify_context(occ.context,record.cas)
                hits.append(EvidenceHit(entry,'CAS',record.cas,occ.source_file,occ.page,occ.context,cls,'validated_cas','CAS válido por checksum e incluido en PROHIBIDOS.'))
    for doc in documents:hits.extend(_name_hits(doc,db))
    unique=[]; seen=set()
    for h in hits:
        k=(h.entry.ingredient,h.channel,h.matched_value,h.source_file,h.page,h.context_class)
        if k not in seen:seen.add(k);unique.append(h)
    return unique
