import unittest
from pathlib import Path
from unittest.mock import patch
from src.engine import analyze
from src.models import PdfDocument,PdfPage,PdfTextBlock,ProhibitedEntry
from src.prohibited_database import ProhibitedDatabase
from src.rules import standard_scope
from src.rules import STATUS_NO_USE,STATUS_NO_USE_RSPO,STATUS_RA_PROHIBITED,STATUS_MITIGATION,STATUS_OBSOLETE,STATUS_PROHIBITED_REVIEW,STATUS_OBSOLETE_REVIEW,STATUS_MITIGATION_REVIEW,STATUS_MATCH_REVIEW,STATUS_DOCUMENT_REVIEW,STATUS_IDENTITY_REVIEW,STATUS_NO_MATCH
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
 def test_kadabra_keeps_mitigation_evidence_visible_beside_prohibited_hit(self):
  r=run_text(
   'Ingrediente activo:\n'
   'Bifentrina 360 g/L\n'
   'Fipronil 120 g/L\n'
   'Producto insecticida de uso agrícola.'
  )
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
  visible={(h.entry.source_list,h.entry.ingredient) for h in r['display_hits']}
  self.assertIn(('PROHIBITED','Fipronil'),visible)
  self.assertIn(('MITIGATE_RISK','Bifentrina'),visible)

 def test_single_component_atrazine_sds_is_decisive_ra_prohibited(self):
  text=(
   'SECCIÓN 1. Identificación de la sustancia o la mezcla y de la sociedad o la empresa\n'
   '1.1. Identificador del producto\n'
   'Nombre comercial\nAtrazine\nNúmero CAS\n1912-24-9\n'
   'SECCIÓN 3. Composición/información sobre los componentes\n'
   '3.2. Mezclas\n'
   'Nombre químico Nº CAS Concentración Clasificación\n'
   'atrazina (ISO) 1912-24-9 100% Skin Sens. 1, Aquatic Acute 1\n'
   'SECCIÓN 14. Información relativa al transporte\n'
   'IATA\n9\nPeligro para el medio ambiente\n'
  )
  r=run_text(text)
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
  self.assertEqual(len(r['active_ingredients']),1)
  self.assertEqual(r['active_ingredients'][0].cas,'1912-24-9')
  self.assertTrue(any(
   h.entry.ingredient=='Atrazina'
   and h.channel in {'CAS','NAME'}
   and h.context_class in {'PRODUCT_IDENTITY','COMPOSITION'}
   for h in r['display_hits']
  ))

 def test_specific_prohibited_cas_uncertain_keeps_prohibited_severity(self):
  r=run_text('Ficha de seguridad de sustancia química. Identificador CAS 153719-23-4. Información general del producto y propiedades.')
  self.assertEqual(r['evaluation'].status,STATUS_PROHIBITED_REVIEW)
 def test_specific_prohibited_cas_incidental_still_stops_for_review(self):
  r=run_text('Productos de descomposición peligrosos: Tiametoxam CAS 153719-23-4. Evitar inhalación de humos.')
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
 def test_mesamate_arsenical_never_silent_negative(self):
  r=run_text('SECCIÓN 3 COMPOSICIÓN\nIngrediente activo: metilarsonato de sodio CAS 2163-80-6\nGrupo químico: Herbicida Arsenical')
  self.assertEqual(r['evaluation'].status,STATUS_PROHIBITED_REVIEW)
  self.assertTrue(any(h.entry.ingredient=='Arsénico y sus compuestos' for h in r['all_hits']))
  self.assertFalse(any(h.strength=='validated_cas' and h.entry.ingredient=='Arsénico y sus compuestos' for h in r['all_hits']))
 def test_nondeterministic_arsenic_group_cannot_become_no_use_from_wording(self):
  r=run_text('COMPOSICIÓN GARANTIZADA\nIngrediente activo: MSMA metilarsonato de sodio 720 g/L\nCAS 2163-80-6\nHerbicida arsenical. Arsénico. Arsenato. Información del ingrediente activo.')
  self.assertEqual(r['evaluation'].status,STATUS_PROHIBITED_REVIEW)
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
 def test_readable_pdf_without_list_match_reports_targeted_no_match(self):
  r=run_text('Documento técnico legible sobre almacenamiento, transporte y recomendaciones generales del producto. No presenta una sección de composición ni identificadores químicos utilizables.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('búsqueda dirigida',r['evaluation'].message)
  self.assertIn('contenido extraíble',r['evaluation'].message)
 def test_panzer_k_narrative_identity_supports_clean_no_match(self):
  r=run_text(
   'FICHA TÉCNICA\n'
   'Panzer K SL es un herbicida que tiene como ingrediente activo '
   'glifosato en forma de sal potasio en una concentración de 443 g/L '
   'equivalente a 360 g/L del ácido.\n'
   'Contenido de Glifosato (sal potasio): 420.85-465.15 g/L'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(len(r['active_ingredients']),1)
  self.assertEqual(
   r['active_ingredients'][0].name.casefold(),
   'glifosato en forma de sal potasio',
  )

 def test_active_ingredient_section_without_list_match_is_clean_no_match(self):
  r=run_text('FICHA TÉCNICA DEL PRODUCTO\nIngrediente activo: Sustancia experimental XYZ 400 g/L.\nDescripción agronómica, dosis de aplicación y recomendaciones de uso para el cultivo.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('búsqueda dirigida',r['evaluation'].message)
 def test_contextual_valid_cas_without_list_match_is_clean_no_match(self):
  r=run_text('COMPOSICIÓN DEL PRODUCTO\nIngrediente activo: sustancia experimental. CAS 7732-18-5. Concentración 500 g/L. Información adicional de formulación y uso.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('búsqueda dirigida',r['evaluation'].message)
 def test_clean_no_match_exposes_exact_identity_used_for_screening(self):
  r=run_text(
   'FICHA TÉCNICA DEL PRODUCTO\n'
   'Ingrediente activo:\n'
   'Sustancia experimental\n'
   'CAS 7732-18-5\n'
   'Concentración 500 g/L\n'
   'MODO DE ACCIÓN\n'
   'Descripción técnica suficientemente extensa del producto y su uso agrícola.'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(r['screening_identity']['document_cas'],['7732-18-5'])
  self.assertEqual(
   [(item['name'],item['cas']) for item in r['screening_identity']['active_ingredients']],
   [('Sustancia experimental','7732-18-5')],
  )

 def test_coragen_combustion_name_does_not_override_composition_cas_identity(self):
  page3_text=(
   'SECCIÓN 3. Composición/información sobre los componentes\n'
   '3.2 Mezclas\n'
   'Componentes\nNombre químico\nNo. CAS\nNo. CE\nNo. Indice\n'
   'Número de registro\nClasificación\nConcentración (% w/w)\n'
   'Clorantraniliprol\n500008-45-7\n>= 10 - < 20\n'
   'Masa de reacción de 5-cloro-2-metil-2H-isotiazol-3-ona y '
   '2-metil-2H-isotiazol-3-ona (3:1)\n'
   '55965-84-9\n613-167-00-5\n>= 0,0002 - < 0,0015\n'
  )
  page5_text=(
   'SECCIÓN 5. Medidas de lucha contra incendios\n'
   '5.2 Peligros específicos derivados de la sustancia o la mezcla\n'
   'Productos de combustión peligrosos\n'
   'El fuego puede producir gases irritantes, corrosivos y/o tóxicos.\n'
   'Óxidos de nitrógeno (NOx)\n'
   'Óxidos de carbono\n'
   'Compuestos de bromo\n'
   'Cianuro de hidrógeno\n'
   'Cloruro de hidrógeno\n'
   'Compuestos clorados\n'
  )
  page3=PdfPage(
   page=3,
   text=page3_text,
   blocks=[
    PdfTextBlock(
     92.2,372.4,340.0,430.4,
     'Componentes\nNombre químico\nNo. CAS\nNo. CE\n'
     'No. Indice\nNúmero de registro\n',
    ),
    PdfTextBlock(357.9,384.8,531.5,395.9,'Clasificación\nConcentración\n'),
    PdfTextBlock(478.8,396.3,517.1,407.4,'(% w/w)\n'),
    PdfTextBlock(92.2,431.6,311.2,465.6,'Clorantraniliprol\n500008-45-7\n'),
    PdfTextBlock(357.9,431.6,453.0,546.1,'Aquatic Acute 1;\nH400\nAquatic Chronic 1;\nH410\n'),
    PdfTextBlock(469.4,431.6,526.4,442.7,'>= 10 - < 20\n'),
    PdfTextBlock(
     92.2,547.0,241.6,581.2,
     'Masa de reacción de 5-cloro-2-\nmetil-2H-isotiazol-3-ona y '
     '2-metil-\n2H-isotiazol-3-ona (3:1)\n',
    ),
    PdfTextBlock(251.7,547.0,314.5,592.7,'55965-84-9\n\n613-167-00-5\n'),
    PdfTextBlock(357.9,547.0,454.1,776.7,'Acute Tox. 3; H301\nSkin Corr. 1C; H314\n'),
    PdfTextBlock(466.8,547.0,529.2,558.1,'>= 0,0002 - <\n'),
    PdfTextBlock(481.3,558.5,514.7,569.6,'0,0015\n'),
   ],
  )
  page5=PdfPage(page=5,text=page5_text)
  coragen=PdfDocument(
   '07. HS Coragen 20 SC.pdf',
   [page3,page5],
   2,
   len(page3_text)+len(page5_text),
   2,
   True,
   [],
  )
  with patch('src.engine.read_pdf',return_value=coragen):
   r=analyze([('07. HS Coragen 20 SC.pdf',b'x')],master_path=MASTER)

  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   r['screening_identity']['document_cas'],
   ['500008-45-7','55965-84-9'],
  )
  cyanide=[
   h for h in r['all_hits']
   if h.entry.ingredient=='Cianuro de hidrógeno'
  ]
  self.assertTrue(cyanide)
  self.assertTrue(all(
   h.context_class=='DECOMPOSITION_COMBUSTION'
   for h in cyanide
  ))

 def test_incidental_unlisted_cas_does_not_block_targeted_no_match(self):
  r=run_text('INFORMACIÓN TOXICOLÓGICA Y LÍMITES DE EXPOSICIÓN. Sustancia de referencia CAS 7732-18-5. Este dato se incluye únicamente como referencia técnica y no describe la composición del producto.')
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertIn('búsqueda dirigida',r['evaluation'].message)
 def test_manual_prohibited_without_active_confirmation_is_review(self):
  r=analyze([],manual_cas_text='153719-23-4',manual_active_confirmed=False,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_PROHIBITED_REVIEW)
 def test_manual_prohibited_with_active_confirmation_is_no_use(self):
  r=analyze([],manual_cas_text='153719234',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
 def test_uncertain_mitigation_cas_uses_mitigation_review_tier(self):
  r=analyze([],manual_cas_text='82657-04-3',manual_active_confirmed=False,master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_MITIGATION_REVIEW)
  self.assertIn('MITIGACIÓN DE RIESGOS',r['evaluation'].message)

 def test_kunfu_sds_correlated_bifenthrin_identity_is_decisive_mitigation(self):
  r=run_text(
   '1. IDENTIFICACIÓN DEL PRODUCTO Y DE LA COMPAÑÍA\n'
   '1.1 Identificador SGA del producto: KUNFU 100 EC\n'
   '1.2 Otros medios de identificación: bifentrina.\n'
   '1.3 Uso recomendado del producto químico y restricciones: '
   'insecticida para uso agrícola, prohibido el uso doméstico.\n'
   '9. PROPIEDADES FISICOQUIMICAS\n'
   'Caracterización del producto\n'
   'Concentración: 100g/L de bifentrina.\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_MITIGATION)
  self.assertEqual(
   [(item.name.casefold(),item.concentration) for item in r['active_ingredients']],
   [('bifentrina','100g/L')],
  )
  self.assertTrue(any(
   h.entry.ingredient=='Bifentrina'
   and h.channel=='NAME'
   and h.context_class=='PRODUCT_IDENTITY'
   for h in r['display_hits']
  ))

 def test_rimon_screens_novaluron_not_wrapped_iupac_fragment(self):
  r=run_text(
   '2. COMPOSICIÓN / INFORMACIÓN SOBRE LOS COMPONENTES\n'
   'Ingrediente activo\n'
   'Novaluron: 1-[3-cloro-4-(1,1,2-trifluoro-2-trifluorometoxietoxi)\n'
   'fenil]-3- (2,6-difluorobenzoil) urea.\n'
   'N° CAS del i.a. :\n'
   '116714-46-6\n'
   '9. PROPIEDADES FÍSICAS Y QUÍMICAS.\n'
   'Concentración: 100 g/l Novaluron.\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_MITIGATION)
  self.assertEqual(
   [(item.name,item.cas,item.concentration) for item in r['active_ingredients']],
   [('Novaluron','116714-46-6','100 g/l')],
  )
  self.assertTrue(any(
   h.entry.cas=='116714-46-6'
   and h.context_class=='ACTIVE'
   for h in r['display_hits']
  ))

 def test_thiamethoxam_pure_sds_is_decisive_ra_prohibited_with_correct_identity(self):
  r=run_text(
   '1. PRODUCT AND COMPANY IDENTIFICATION\n'
   'Product name : Thiamethoxam\n'
   'CAS-No. : 153719-23-4\n'
   '3. COMPOSITION/INFORMATION ON INGREDIENTS\n'
   '3.1 Substances\n'
   'CAS-No. : 153719-23-4\n'
   'Hazardous components\n'
   'Component Classification Concentration\n'
   'Thiamethoxam\n'
   'Acute Tox. 4; Aquatic Acute 1; Aquatic Chronic 1; H302, H410\n'
   '<= 100 %\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
  self.assertEqual(
   [(item.name,item.cas,item.concentration) for item in r['active_ingredients']],
   [('Thiamethoxam','153719-23-4','<= 100 %')],
  )
  self.assertTrue(any(
   h.entry.ingredient=='Tiametoxam'
   and h.channel in {'CAS','NAME'}
   and h.context_class in {'PRODUCT_IDENTITY','COMPOSITION'}
   for h in r['display_hits']
  ))

 def test_inex_screens_three_declared_actives_not_generic_ingredient_label(self):
  r=run_text(
   'Ingredientes\n'
   'Activos\n'
   'Alquil polieter alcohol etoxilado\n'
   'Alquil poliglicol\n'
   'Aril polietoxietanol\n'
   '26.37%\n'
   'Ingrediente\n'
   'Aditivo\n'
   'Agua\n'
   '73.63%\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   [item.name for item in r['active_ingredients']],
   [
    'Alquil polieter alcohol etoxilado',
    'Alquil poliglicol',
    'Aril polietoxietanol',
   ],
  )
  self.assertNotIn('Ingrediente',[item.name for item in r['active_ingredients']])

 def test_fossile_footnote_pr_is_not_screening_identity(self):
  r=run_text(
   'Ingrediente Activo: Fosetyl-aluminium\n'
   'Nombre IUPAC I.A: aluminium tris (ethyl phosphonate)\n'
   'Grupo Químico: Organofosforado\n'
   'Uso: Fungicida de uso agrícola\n'
   'Concentración: 800 g/Kg\n'
   'P.C.: Periodo de Carencia.\n'
   'ingrediente activo en el producto agrícola sea menor o igual al LMR aceptado.\n'
   'P.R.: Periodo de Reentrada.\n'
   'N.A.: No aplica.\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   [item.name for item in r['active_ingredients']],
   ['Fosetyl-aluminium'],
  )
  self.assertNotIn('P.R',[item.name for item in r['active_ingredients']])

 def test_credit_screens_only_glyphosate_not_equivalence_or_target_weeds(self):
  r=run_text(
   'Ingrediente Activo:\n'
   'Glifosato 680 g/kg\n'
   'N - (phosphonomethyl) glycine, equivalente a 747 g/kg de Glyphosate\n'
   'Monoammonium salt, de formulacion a 20ºC,\n'
   'Ingredientes Aditivos: c.s.p. 1 kg\n'
   'INGREDIENTE ACTIVO:\n'
   'GLIFOSATO\n'
   'Liendre puerco Echinochloa colonum,\n'
   'Falsa caminadora Ischaemum rugosum,\n'
   '3.0 Kg/ha\n'
   'RECOMENDACIONES DE USO - REGISTROS\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   [(item.name.casefold(),item.concentration) for item in r['active_ingredients']],
   [('glifosato','680 g/kg')],
  )
  self.assertFalse(any(
   'echinochloa' in item.name.casefold()
   or 'monoammonium' in item.name.casefold()
   or 'equivalente' in item.name.casefold()
   for item in r['active_ingredients']
  ))

 def test_mayoral_ft_screens_imazapic_and_imazapyr_as_two_actives(self):
  r=run_text(
   'MAYORAL 350 SL\n'
   'Ingrediente activo: IMAZAPIC+IMAZAPYR.\n'
   'Concentración:\n'
   '262.5 + 87.5 g/L.\n'
   'Categoría Toxicológica: III – Ligeramente peligroso.\n'
   'Modo de acción. El imazapic y el imazapyr son ingredientes activos.\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   [(item.name,item.concentration) for item in r['active_ingredients']],
   [('IMAZAPIC','262.5 g/L'),('IMAZAPYR','87.5 g/L')],
  )
  self.assertEqual(
   [item['name'] for item in r['screening_identity']['active_ingredients']],
   ['IMAZAPIC','IMAZAPYR'],
  )

 def test_mayoral_structured_composition_supports_clean_no_match(self):
  page=PdfPage(
   2,
   (
    'SECCIÓN 3: Composición/información sobre los componentes\n'
    'Mezcla\nNombre químico Nº CAS % en peso Nº CE INTERNATIONAL GHS CLASSIFICATION Factor M\n'
    'Imazapic 104098-48-\n8\n21-27\n'
    'Isopropylamine 75-31-0 6-10\n'
    'Imazapyr 81334-34-1 6-10\n'
    'SECCIÓN 4: Primeros auxilios\n'
   ),
   [
    PdfTextBlock(96.7,327.0,495.1,337.0,'Nombre químico\nNº CAS\n% en peso\nNº CE\nINTERNATIONAL GHS\n'),
    PdfTextBlock(114.2,348.2,259.4,358.2,'Imazapic\n104098-48-\n'),
    PdfTextBlock(233.9,358.5,241.4,368.6,'8\n'),
    PdfTextBlock(277.0,348.2,494.2,368.6,'21-27\nEye Irrit. 2 (H319)\nAquatic Acute 1 (H400)\n'),
    PdfTextBlock(101.7,380.0,487.6,421.1,'Isopropylamine\n75-31-0\n6-10\n200-860-9\nFlam. Liq. 1 (H224)\n'),
    PdfTextBlock(113.7,463.5,497.9,483.9,'Imazapyr\n81334-34-1\n6-10\nEye Irrit. 2 (H319)\n'),
    PdfTextBlock(54.7,496.2,229.8,509.6,'SECCIÓN 4: Primeros auxilios\n'),
   ],
  )
  mayoral=PdfDocument('HS Mayoral.PDF',[page],1,len(page.text),1,True,[])
  with patch('src.engine.read_pdf',return_value=mayoral):
   r=analyze([('HS Mayoral.PDF',b'x')],master_path=MASTER)
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   r['screening_identity']['document_cas'],
   ['104098-48-8','75-31-0','81334-34-1'],
  )
  self.assertEqual(
   [(x['name'],x['cas']) for x in r['screening_identity']['composition_components']],
   [('Imazapic','104098-48-8'),('Isopropylamine','75-31-0'),('Imazapyr','81334-34-1')],
  )
  self.assertIn('búsqueda dirigida',r['evaluation'].message)

 def test_explicit_lufenuron_identity_triggers_mitigation_not_review(self):
  r=run_text(
   'FICHA TÉCNICA\n'
   'COMPOSICIÓN GARANTIZADA:\n'
   'Ingrediente activo:\n'
   'Lufenuron\n'
   'Ingredientes aditivos\n'
   '50 g/L\n'
   'Insecticida agrícola.'
  )
  self.assertEqual(r['evaluation'].status,STATUS_MITIGATION)
  self.assertIn('Lufenurón',r['evaluation'].message)
  self.assertTrue(any(
   h.entry.source_list=='MITIGATE_RISK'
   and h.entry.ingredient=='Lufenurón'
   and h.context_class=='ACTIVE'
   for h in r['display_hits']
  ))

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


 def test_glifosol_incidental_paraquat_does_not_drive_regulatory_result(self):
  r=run_text(
   'HERBICIDA\n'
   'GLIFOSOL SL\n'
   'Ingrediente Activo:\n'
   'Glifosato\n'
   'Concentración:\n'
   '480 g/L\n'
   'COMPATIBILIDAD Y FITOTOXICIDAD\n'
   'GLIFOSOL SL por ser un herbicida no selectivo se recomienda no '
   'mezclarlo con otros herbicidas. Mezclas en tanque con herbicidas '
   'residuales o con herbicidas como paraquat, phenoxy u otros herbicidas '
   'de tipo auxinas, pueden reducir la eficacia del glifosato.\n'
  )
  self.assertEqual(r['evaluation'].status,STATUS_NO_MATCH)
  self.assertEqual(
   [(item.name,item.concentration) for item in r['active_ingredients']],
   [('Glifosato','480 g/L')],
  )
  paraquat=[
   h for h in r['all_hits']
   if h.entry.ingredient.casefold()=='paraquat'
  ]
  self.assertTrue(paraquat)
  self.assertTrue(all(h.context_class=='INCIDENTAL' for h in paraquat))
  self.assertFalse(any(
   h.entry.ingredient.casefold()=='paraquat'
   for h in r['display_hits']
  ))

 def test_targeted_match_is_not_suppressed_by_different_active_identity(self):
  r=run_text(
   'FICHA TÉCNICA\n'
   'Ingrediente activo: Glifosato 480 g/L.\n'
   'SECCIÓN 3. COMPOSICIÓN/INFORMACIÓN SOBRE LOS COMPONENTES\n'
   'Nombre químico Nº CAS Concentración\n'
   'Fipronil 120068-37-3 5 %.\n'
   'Información adicional de formulación y uso agrícola.'
  )
  self.assertEqual(r['evaluation'].status,STATUS_RA_PROHIBITED)
  self.assertTrue(any(
   h.entry.ingredient=='Fipronil'
   and h.channel in {'CAS','NAME'}
   and h.context_class=='COMPOSITION'
   for h in r['all_hits']
  ))
  self.assertFalse(any(
   h.channel=='ACTIVE_IDENTITY'
   for h in r['all_hits']
  ))

 def test_reference_list_surfaces_every_unique_prohibited_identity_without_product_claim(self):
  database=ProhibitedDatabase(MASTER)
  expected={entry.ingredient for entry in database.prohibited}
  self.assertEqual(len(expected),163)

  rows=[
   'MANEJO DE PLAGUICIDAS',
   'Anexo 1. Listado de plaguicidas prohibidos',
   'No. PLAGUICIDAS PROHIBIDOS Ingrediente activo o grupo Número CAS',
  ]
  rows.extend(
   f'{index}. {entry.ingredient} {entry.cas or "varios"}'
   for index,entry in enumerate(database.prohibited,start=1)
  )
  r=run_text('\n'.join(rows))

  detected={
   item['ingredient']
   for item in r['detected_identities']
   if item['source_list']=='PROHIBITED'
  }
  self.assertEqual(detected,expected)
  self.assertEqual(r['evaluation'].status,STATUS_MATCH_REVIEW)
  self.assertEqual(r['display_hits'],[])
  self.assertEqual(r['active_ingredients'],[])
  self.assertEqual(r['composition_components'],[])
  self.assertTrue(all(
   item['contexts']==['REFERENCE_LIST']
   for item in r['detected_identities']
  ))
  self.assertEqual(
   r['targeted_screening']['matched_identities'],
   len(r['detected_identities']),
  )


class ResultContractTests(unittest.TestCase):
 def test_status_labels_remain_stable(self):
  self.assertEqual(STATUS_NO_USE,'NO UTILIZAR — RSPO E ISCC')
  self.assertEqual(STATUS_NO_USE_RSPO,'NO UTILIZAR — RSPO')
  self.assertEqual(STATUS_RA_PROHIBITED,'ATENCIÓN — PROHIBIDO EN RA; REVISAR RSPO / ISCC')
  self.assertEqual(STATUS_MITIGATION,'ATENCIÓN — MITIGACIÓN DE RIESGOS SEGÚN RA')
  self.assertEqual(STATUS_OBSOLETE,'ATENCIÓN — PLAGUICIDA OBSOLETO SEGÚN RA')
  self.assertEqual(STATUS_PROHIBITED_REVIEW,'POSIBLE PROHIBICIÓN EN RA — REVISAR IDENTIDAD')
  self.assertEqual(STATUS_OBSOLETE_REVIEW,'POSIBLE PLAGUICIDA OBSOLETO SEGÚN RA — REVISAR IDENTIDAD')
  self.assertEqual(STATUS_MITIGATION_REVIEW,'MITIGACIÓN DE RIESGOS — REVISAR IDENTIDAD')
  self.assertEqual(STATUS_MATCH_REVIEW,'COINCIDENCIA NORMATIVA — REVISAR')
  self.assertEqual(STATUS_DOCUMENT_REVIEW,'REVISIÓN DOCUMENTAL')
  self.assertEqual(STATUS_IDENTITY_REVIEW,'REVISIÓN — IDENTIDAD QUÍMICA NO CONFIRMADA')
  self.assertEqual(STATUS_NO_MATCH,'SIN COINCIDENCIAS DETECTADAS')

 def test_ra_prohibited_message_remains_stable(self):
  r=analyze([],manual_cas_text='34256-82-1',manual_active_confirmed=True,master_path=MASTER)
  self.assertEqual(
   r['evaluation'].message,
   'Rainforest Alliance incluye la(s) sustancia(s) detectada(s) en su lista PROHIBIDOS: Acetoclor. El criterio detectado no se trata como equivalencia automática de prohibición en RSPO o ISCC; revise el requisito aplicable antes de decidir su uso.'
  )
