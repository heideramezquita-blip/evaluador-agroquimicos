import unittest
from pathlib import Path
from unittest.mock import patch
from src.engine import analyze
from src.models import PdfDocument,PdfPage,ProhibitedEntry
from src.rules import standard_scope
from src.rules import STATUS_NO_USE,STATUS_NO_USE_RSPO,STATUS_RA_PROHIBITED,STATUS_MITIGATION,STATUS_OBSOLETE,STATUS_MATCH_REVIEW,STATUS_DOCUMENT_REVIEW,STATUS_IDENTITY_REVIEW,STATUS_NO_MATCH
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'

def doc(text,name='test.pdf'):
 return PdfDocument(name,[PdfPage(1,text)],1,len(text),1 if text else 0,bool(text and len(text)>=50),[] if text else ['sin texto'])
def run_text(text):
 with patch('src.engine.read_pdf',return_value=doc(text)):
  return analyze([('test.pdf',b'x')],master_path=MASTER)

class ProhibitedEngineTests(unittest.TestCase):
 def test_engeo_tiametoxam_ra_severe_requires_cross_standard_review(self):
  r=run_text('COMPOSICIÓN GARANTIZADA\nIngredientes Activos:\nLambda-cihalotrina\nTiametoxam\nCAS 153719-23-4\nConcentración 141 g/L')
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_specific_prohibited_cas_uncertain_is_orange_review(self):
  r=run_text('Ficha de seguridad de sustancia química. Identificador CAS 153719-23-4. Información general del producto y propiedades.')
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_specific_prohibited_cas_incidental_still_stops_for_review(self):
  r=run_text('Productos de descomposición peligrosos: Tiametoxam CAS 153719-23-4. Evitar inhalación de humos.')
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_mesamate_arsenical_never_silent_negative(self):
  r=run_text('SECCIÓN 3 COMPOSICIÓN\nIngrediente activo: metilarsonato de sodio CAS 2163-80-6\nGrupo químico: Herbicida Arsenical')
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
  self.assertTrue(any(h.entry.ingredient=='Arsénico y sus compuestos' for h in r['all_hits']))
  self.assertFalse(any(h.strength=='validated_cas' and h.entry.ingredient=='Arsénico y sus compuestos' for h in r['all_hits']))
 def test_nondeterministic_arsenic_group_cannot_become_no_use_from_wording(self):
  r=run_text('COMPOSICIÓN GARANTIZADA\nIngrediente activo: MSMA metilarsonato de sodio 720 g/L\nCAS 2163-80-6\nHerbicida arsenical. Arsénico. Arsenato. Información del ingrediente activo.')
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
  arsenic=[h for h in r['all_hits'] if h.entry.ingredient=='Arsénico y sus compuestos']
  self.assertTrue(arsenic)
  self.assertTrue(all(h.strength=='group_candidate' for h in arsenic))
 def test_scanned_pdf_is_document_review(self):
  with patch('src.engine.read_pdf',return_value=PdfDocument('scan.pdf',[PdfPage(1,'')],1,0,0,False,['sin texto'])):
   r=analyze([('scan.pdf',b'x')],master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_DOCUMENT_REVIEW)
 def test_pdf_read_failure_is_document_review(self):
  with patch('src.engine.read_pdf',side_effect=ValueError('archivo dañado')):
   r=analyze([('broken.pdf',b'x')],master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_DOCUMENT_REVIEW)
  self.assertTrue(any('No fue posible leer broken.pdf' in warning for warning in r['evaluation'].warnings))
 def test_readable_pdf_without_chemical_identity_requires_identity_review(self):
  r=run_text('Documento técnico legible sobre almacenamiento, transporte y recomendaciones generales del producto. No presenta una sección de composición ni identificadores químicos utilizables.')
  self.assertEqual(r['evaluation'].status,STATUS_IDENTITY_REVIEW)
  self.assertIn('No es válido interpretar este resultado como ausencia de coincidencias',r['evaluation'].message)
 def test_active_ingredient_section_without_list_match_is_clean_no_match(self):
  r=run_text('FICHA TÉCNICA DEL PRODUCTO\nIngrediente activo: Sustancia experimental XYZ 400 g/L.\nDescripción agronómica, dosis de aplicación y recomendaciones de uso para el cultivo.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('referencia explícita a ingrediente activo',r['evaluation'].message)
 def test_contextual_valid_cas_without_list_match_is_clean_no_match(self):
  r=run_text('COMPOSICIÓN DEL PRODUCTO\nIngrediente activo: sustancia experimental. CAS 7732-18-5. Concentración 500 g/L. Información adicional de formulación y uso.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('CAS válido en contexto de ingrediente activo/composición',r['evaluation'].message)
 def test_incidental_cas_alone_does_not_support_clean_no_match(self):
  r=run_text('INFORMACIÓN TOXICOLÓGICA Y LÍMITES DE EXPOSICIÓN. Sustancia de referencia CAS 7732-18-5. Este dato se incluye únicamente como referencia técnica y no describe la composición del producto.')
  self.assertEqual(r['evaluation'].status,STATUS_IDENTITY_REVIEW)
 def test_manual_prohibited_without_active_confirmation_is_review(self):
  r=analyze([],manual_cas_text='153719-23-4',manual_active_confirmed=False,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_manual_prohibited_with_active_confirmation_is_no_use(self):
  r=analyze([],manual_cas_text='153719234',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_mitigation_list_triggers_attention(self):
  r=analyze([],manual_cas_text='52918-63-5',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_MITIGATION)
 def test_obsolete_list_triggers_no_use(self):
  r=analyze([],manual_cas_text='309-00-2',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_OBSOLETE)
 def test_shared_who_rotterdam_criterion_is_no_use_rspo_iscc(self):
  r=analyze([],manual_cas_text='1563-66-2',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_USE)
 def test_cmr_only_maps_to_rspo_not_iscc(self):
  r=analyze([],manual_cas_text='61-82-5',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_USE_RSPO)
 def test_paraquat_maps_explicitly_to_rspo(self):
  r=analyze([],manual_cas_text='4685-14-7',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_USE_RSPO)
 def test_sga_cmr_category_2_does_not_map_to_rspo(self):
  entry=ProhibitedEntry('Sustancia de prueba','123-45-6','', 'Carcinogenicidad: SGA 2','test','1','2026')
  scope=standard_scope(entry)
  self.assertFalse(scope['rspo'])
  self.assertFalse(scope['iscc'])
 def test_rspo_scope_names_each_documented_sga_class(self):
  entry=ProhibitedEntry('Sustancia de prueba','123-45-6','', 'Carcinogenicidad: ✓; Toxicidad reproductiva: ✓','test','1','2026')
  scope=standard_scope(entry)
  self.assertTrue(scope['rspo'])
  self.assertIn('SGA · Carcinogenicidad 1A/1B',scope['rspo_basis'])
  self.assertIn('SGA · Toxicidad reproductiva 1A/1B',scope['rspo_basis'])
 def test_ra_severe_only_does_not_auto_map_to_rspo_or_iscc(self):
  r=analyze([],manual_cas_text='34256-82-1',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)


class ResultContractTests(unittest.TestCase):
 def test_status_labels_remain_stable(self):
  self.assertEqual(STATUS_NO_USE,'NO UTILIZAR — RSPO E ISCC')
  self.assertEqual(STATUS_NO_USE_RSPO,'NO UTILIZAR — RSPO')
  self.assertEqual(STATUS_RA_PROHIBITED,'ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC')
  self.assertEqual(STATUS_MITIGATION,'ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA')
  self.assertEqual(STATUS_OBSOLETE,'ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA')
  self.assertEqual(STATUS_MATCH_REVIEW,'COINCIDENCIA NORMATIVA — REVISAR')
  self.assertEqual(STATUS_DOCUMENT_REVIEW,'REVISIÓN DOCUMENTAL')
  self.assertEqual(STATUS_IDENTITY_REVIEW,'REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA')
  self.assertEqual(STATUS_NO_MATCH,'SIN COINCIDENCIAS DETECTADAS')

 def test_ra_prohibited_message_remains_stable(self):
  r=analyze([],manual_cas_text='34256-82-1',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(
   r['evaluation'].message,
   'Rainforest Alliance incluye el/los ingrediente(s) en su lista PROHIBIDOS: Acetoclor. El criterio detectado no se trata como equivalencia automática de prohibición en RSPO o ISCC; revise el requisito aplicable antes de decidir su uso.'
  )
