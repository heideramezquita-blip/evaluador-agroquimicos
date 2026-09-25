import unittest
from pathlib import Path
from unittest.mock import patch
from src.engine import analyze
from src.models import PdfDocument,PdfPage
from src.rules import STATUS_NO_USE,STATUS_REVIEW,STATUS_NO_MATCH
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'

def doc(text,name='test.pdf'):
 return PdfDocument(name,[PdfPage(1,text)],1,len(text),1 if text else 0,bool(text and len(text)>=50),[] if text else ['sin texto'])
def run_text(text):
 with patch('src.engine.read_pdf',return_value=doc(text)):
  return analyze([('test.pdf',b'x')],master_path=MASTER)

class ProhibitedEngineTests(unittest.TestCase):
 def test_engeo_tiametoxam_active_is_no_use(self):
  r=run_text('COMPOSICIÓN GARANTIZADA\nIngredientes Activos:\nLambda-cihalotrina\nTiametoxam\nCAS 153719-23-4\nConcentración 141 g/L')
  self.assertEqual(r['evaluation'].status,STATUS_NO_USE)
 def test_mesamate_arsenical_never_silent_negative(self):
  r=run_text('SECCIÓN 3 COMPOSICIÓN\nIngrediente activo: metilarsonato de sodio CAS 2163-80-6\nGrupo químico: Herbicida Arsenical')
  self.assertEqual(r['evaluation'].status,STATUS_REVIEW)
  self.assertTrue(any(h.entry.ingredient=='Arsénico y sus compuestos' for h in r['all_hits']))
 def test_scanned_pdf_is_review(self):
  with patch('src.engine.read_pdf',return_value=PdfDocument('scan.pdf',[PdfPage(1,'')],1,0,0,False,['sin texto'])):
   r=analyze([('scan.pdf',b'x')],master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_REVIEW)
 def test_manual_prohibited_without_active_confirmation_is_review(self):
  r=analyze([],manual_cas_text='153719-23-4',manual_active_confirmed=False,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_REVIEW)
 def test_manual_prohibited_with_active_confirmation_is_no_use(self):
  r=analyze([],manual_cas_text='153719234',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_USE)
 def test_only_prohibited_affects_decision(self):
  r=analyze([],manual_cas_text='52918-63-5',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
