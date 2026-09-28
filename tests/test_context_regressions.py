import unittest
from pathlib import Path
from unittest.mock import patch
from src.engine import analyze
from src.models import PdfDocument,PdfPage
from src.context_classifier import COMPOSITION, classify_context
from src.rules import STATUS_NO_USE,STATUS_NO_USE_RSPO,STATUS_RA_PROHIBITED,STATUS_MATCH_REVIEW,STATUS_NO_MATCH
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'

def evaluate(text):
 d=PdfDocument('fixture.pdf',[PdfPage(1,text)],1,len(text),1,True,[])
 with patch('src.engine.read_pdf',return_value=d):return analyze([('fixture.pdf',b'x')],master_path=MASTER)

class RealFalsePositiveRegressions(unittest.TestCase):
 def assert_not_no_use(self,text):self.assertNotIn(evaluate(text)['evaluation'].status,(STATUS_NO_USE,STATUS_NO_USE_RSPO))
 def test_inex_ethylene_oxide_precursor(self):self.assert_not_no_use('Ingredientes activos: alcoholes etoxilados. Sus ingredientes activos son obtenidos mediante la condensación del óxido de etileno con alcoholes lineales.')
 def test_cumbre_chlordane_incompatibility(self):self.assert_not_no_use('INCOMPATIBILIDADES: no es compatible con Clordano ni productos fuertemente alcalinos.')
 def test_fosetyl_phosphine_decomposition(self):self.assert_not_no_use('PRODUCTOS DE DESCOMPOSICIÓN PELIGROSOS: bajo condiciones de fuego puede formarse fosfina.')
 def test_coragen_hcn_combustion(self):self.assert_not_no_use('Productos peligrosos de combustión: monóxido de carbono y cianuro de hidrógeno.')
 def test_deltapoint_hcn_thermal_decomposition(self):self.assert_not_no_use('La descomposición térmica puede producir cianuro de hidrógeno.')
 def test_metsulfuron_hcn_decomposition(self):self.assert_not_no_use('Productos de descomposición peligrosos: cianuro de hidrógeno.')
 def test_prevalor_hcn_fire(self):self.assert_not_no_use('En caso de incendio pueden desprenderse gases, incluyendo cianuro de hidrógeno.')
 def test_activo_boric_acid_exposure_limit(self):self.assert_not_no_use('SECCIÓN 8 CONTROLES DE EXPOSICIÓN. Límite de exposición ocupacional: Ácido bórico ACGIH TLV TWA 2 mg/m3.')

class SyntheticFixtures(unittest.TestCase):
 def test_prohibited_cas_active(self):self.assertEqual(evaluate('Ingrediente activo: Tiametoxam CAS 153719-23-4. Formulación.')['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_prohibited_cas_decomposition(self):self.assertEqual(evaluate('Productos de descomposición: Tiametoxam CAS 153719-23-4.')['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_negation(self):self.assertEqual(evaluate('Este producto no contiene Tiametoxam 153719-23-4.')['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_reference(self):self.assertEqual(evaluate('Referencia bibliográfica: Tiametoxam CAS 153719-23-4.')['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_name_only_active(self):self.assertEqual(evaluate('COMPOSICIÓN GARANTIZADA. Ingrediente activo: Tiametoxam 20%. Sin número CAS.')['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_split_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719-\n23-4.')['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_spaced_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719 - 23 - 4.')['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_unicode_dash_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719–23–4.')['evaluation'].status,STATUS_RA_PROHIBITED)


class CompositionHeadingRegressions(unittest.TestCase):
 def test_composition_heading_tolerates_spacing_around_slash(self):
  variants=(
   '3. COMPOSICIÓN /INFORMACIÓN SOBRE LOS COMPONENTES\nNombre CAS TLV Composición\nFosetil Aluminio 39148-24-8 800 g/kg',
   '3. COMPOSICIÓN/ INFORMACIÓN SOBRE LOS COMPONENTES\nNombre CAS TLV Composición\nFosetil Aluminio 39148-24-8 800 g/kg',
   '3. COMPOSICIÓN / INFORMACIÓN SOBRE LOS COMPONENTES\nNombre CAS TLV Composición\nFosetil Aluminio 39148-24-8 800 g/kg',
   '3. COMPOSICIÓN/INFORMACIÓN SOBRE LOS COMPONENTES\nNombre CAS TLV Composición\nFosetil Aluminio 39148-24-8 800 g/kg',
  )
  for text in variants:
   with self.subTest(text=text.splitlines()[0]):
    self.assertEqual(classify_context(text,'39148-24-8'),COMPOSITION)

 def test_fosetyl_sds_composition_supports_clean_no_match(self):
  text=('Ficha de Datos de Seguridad\n'
        '3. COMPOSICIÓN /INFORMACIÓN SOBRE LOS COMPONENTES\n'
        'Nombre CAS TLV Composición\n'
        'Fosetil Aluminio 39148-24-8 800 g/kg\n'
        'Dióxido de silicio 14808-60-7 25 g/kg\n'
        'Información adicional de manejo y almacenamiento del producto.')
  result=evaluate(text)
  self.assertEqual(result['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual({record.cas for record in result['evaluation'].cas_records},{'39148-24-8','14808-60-7'})
  self.assertIn('CAS válido en contexto de ingrediente activo/composición',result['evaluation'].message)
