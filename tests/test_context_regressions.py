import unittest
from pathlib import Path
from unittest.mock import patch
from src.engine import analyze
from src.models import PdfDocument,PdfPage
from src.rules import STATUS_NO_USE
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'

def evaluate(text):
 d=PdfDocument('fixture.pdf',[PdfPage(1,text)],1,len(text),1,True,[])
 with patch('src.engine.read_pdf',return_value=d):return analyze([('fixture.pdf',b'x')],master_path=MASTER)

class RealFalsePositiveRegressions(unittest.TestCase):
 def assert_not_no_use(self,text):self.assertNotEqual(evaluate(text)['evaluation'].status,STATUS_NO_USE)
 def test_inex_ethylene_oxide_precursor(self):self.assert_not_no_use('Ingredientes activos: alcoholes etoxilados. Sus ingredientes activos son obtenidos mediante la condensación del óxido de etileno con alcoholes lineales.')
 def test_cumbre_chlordane_incompatibility(self):self.assert_not_no_use('INCOMPATIBILIDADES: no es compatible con Clordano ni productos fuertemente alcalinos.')
 def test_fosetyl_phosphine_decomposition(self):self.assert_not_no_use('PRODUCTOS DE DESCOMPOSICIÓN PELIGROSOS: bajo condiciones de fuego puede formarse fosfina.')
 def test_coragen_hcn_combustion(self):self.assert_not_no_use('Productos peligrosos de combustión: monóxido de carbono y cianuro de hidrógeno.')
 def test_deltapoint_hcn_thermal_decomposition(self):self.assert_not_no_use('La descomposición térmica puede producir cianuro de hidrógeno.')
 def test_metsulfuron_hcn_decomposition(self):self.assert_not_no_use('Productos de descomposición peligrosos: cianuro de hidrógeno.')
 def test_prevalor_hcn_fire(self):self.assert_not_no_use('En caso de incendio pueden desprenderse gases, incluyendo cianuro de hidrógeno.')
 def test_activo_boric_acid_exposure_limit(self):self.assert_not_no_use('SECCIÓN 8 CONTROLES DE EXPOSICIÓN. Límite de exposición ocupacional: Ácido bórico ACGIH TLV TWA 2 mg/m3.')

class SyntheticFixtures(unittest.TestCase):
 def test_prohibited_cas_active(self):self.assertEqual(evaluate('Ingrediente activo: Tiametoxam CAS 153719-23-4. Formulación.')['evaluation'].status,STATUS_NO_USE)
 def test_prohibited_cas_decomposition(self):self.assertNotEqual(evaluate('Productos de descomposición: Tiametoxam CAS 153719-23-4.')['evaluation'].status,STATUS_NO_USE)
 def test_negation(self):self.assertNotEqual(evaluate('Este producto no contiene Tiametoxam 153719-23-4.')['evaluation'].status,STATUS_NO_USE)
 def test_reference(self):self.assertNotEqual(evaluate('Referencia bibliográfica: Tiametoxam CAS 153719-23-4.')['evaluation'].status,STATUS_NO_USE)
 def test_name_only_active(self):self.assertEqual(evaluate('COMPOSICIÓN GARANTIZADA. Ingrediente activo: Tiametoxam 20%. Sin número CAS.')['evaluation'].status,STATUS_NO_USE)
 def test_split_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719-\n23-4.')['evaluation'].status,STATUS_NO_USE)
 def test_spaced_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719 - 23 - 4.')['evaluation'].status,STATUS_NO_USE)
 def test_unicode_dash_cas(self):self.assertEqual(evaluate('Ingrediente activo Tiametoxam CAS 153719–23–4.')['evaluation'].status,STATUS_NO_USE)
