from __future__ import annotations
from pathlib import Path
from .cas_extractor import extract_document_cas,merge_cas_records
from .cas_utils import parse_manual_cas
from .models import CasOccurrence,CasRecord
from .pdf_reader import read_pdf
from .prohibited_database import ProhibitedDatabase
from .prohibited_detector import detect_candidates
from .rules import evaluate_prohibited

def analyze(files,*,manual_cas_text='',manual_active_confirmed=False,master_path=None):
    if master_path is None:master_path=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'
    db=ProhibitedDatabase(master_path); documents=[]; groups=[]; invalid=[]; warnings=[]
    for name,payload in files:
        try:doc=read_pdf(payload,name)
        except Exception as e:
            warnings.append(f'No fue posible leer {name}: {e}'); continue
        documents.append(doc); warnings.extend(doc.warnings); recs,bad=extract_document_cas(doc); groups.append(recs); invalid.extend(bad)
    manual_valid,manual_invalid=parse_manual_cas(manual_cas_text)
    manual_records=[]
    for cas in manual_valid:
        role='active_explicit' if manual_active_confirmed else 'unknown'
        manual_records.append(CasRecord(cas,[CasOccurrence(cas,'Entrada manual',None,'manual',role,'CAS introducido manualmente.')]))
    groups.append(manual_records); records=merge_cas_records(groups)
    hits=detect_candidates(documents,records,db)
    for h in hits:
        if h.channel=='CAS' and h.source_file=='Entrada manual' and manual_active_confirmed:h.context_class='ACTIVE'
    unprocessables=sum(not d.processable for d in documents)
    if manual_valid and not documents:
        warnings.append('La entrada manual de CAS solo puede descartar coincidencias por CAS específico; no excluye los registros de PROHIBIDOS definidos como grupos con CAS varios.')
    evaluation=evaluate_prohibited(records,hits,warnings,unprocessables)
    return {'evaluation':evaluation,'documents':documents,'invalid_candidates':invalid,'manual_valid':manual_valid,'manual_invalid':manual_invalid,'all_hits':hits,'prohibited_specific_count':len(db.specific),'prohibited_group_count':len(db.groups)}
