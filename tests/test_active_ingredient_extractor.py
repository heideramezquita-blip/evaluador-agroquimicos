import unittest

from src.active_ingredient_extractor import extract_active_ingredients
from src.models import PdfDocument, PdfPage, PdfTextBlock
from src.text_utils import match_key


def document(text, name="test.pdf"):
    return PdfDocument(
        file_name=name,
        pages=[PdfPage(page=1, text=text)],
        page_count=1,
        character_count=len(text),
        pages_with_text=1,
        processable=True,
        warnings=[],
    )


class ActiveIngredientExtractorTests(unittest.TestCase):
    def test_becano_style_label_extracts_name_without_cas(self):
        text = (
            "FICHA TÉCNICA\n"
            "COMPOSICIÓN GARANTIZADA:\n"
            "Ingredientes activos:\n"
            "Indaziﬂam (formulación a 20ºC) / 500g/litro\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 litro"
        )
        items = extract_active_ingredients(document(text, "FT Becano.pdf"))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Indaziflam")
        self.assertEqual(items[0].concentration, "500g/litro")
        self.assertEqual(items[0].cas, "")
        self.assertEqual(items[0].source_file, "FT Becano.pdf")
        self.assertEqual(items[0].page, 1)

    def test_inline_active_ingredient_can_keep_concentration_and_cas(self):
        text = (
            "Ingrediente activo: Deltametrina 2.5% CAS 52918-63-5\n"
            "Uso agrícola"
        )
        items = extract_active_ingredients(document(text))

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Deltametrina")
        self.assertEqual(items[0].concentration, "2.5%")
        self.assertEqual(items[0].cas, "52918-63-5")

    def test_multiple_explicit_actives_are_reported_separately(self):
        text = (
            "COMPOSICIÓN GARANTIZADA\n"
            "Ingredientes Activos:\n"
            "Lambda-cihalotrina 106 g/L\n"
            "Tiametoxam 141 g/L\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 L"
        )
        items = extract_active_ingredients(document(text))

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [
                ("Lambda-cihalotrina", "106 g/L"),
                ("Tiametoxam", "141 g/L"),
            ],
        )

    def test_two_column_kadabra_layout_uses_aligned_identity_blocks_only(self):
        page = PdfPage(
            page=1,
            text=(
                "Modo de Acción:                         Ingrediente activo:\n"
                "Bifentrina: Insecticida...             Bifentrina (360 g/L) +\n"
                "Fipronil: Insecticida...               Fipronil (120 g/L)\n"
                "Generalidades: KADABRA es un insecticida a base de los "
                "ingredientes activos Bifentrina y Fipronil."
            ),
            blocks=[
                PdfTextBlock(452, 428, 555, 442, "Ingrediente activo:\n"),
                PdfTextBlock(67, 449, 158, 463, "Modo de Acción:\n"),
                PdfTextBlock(
                    452,
                    445,
                    538,
                    467,
                    "Bifentrina (360 g/L) +\nFipronil (120 g/L)\n",
                ),
                PdfTextBlock(
                    67,
                    465,
                    428,
                    521,
                    "Bifentrina: Insecticida de contacto con acción estomacal.\n"
                    "Fipronil: Insecticida que actúa por contacto e ingestión.\n",
                ),
                PdfTextBlock(
                    452,
                    482,
                    529,
                    531,
                    "Categoría toxicológica:\nII – Moderadamente Peligroso.\n",
                ),
                PdfTextBlock(
                    67,
                    626,
                    429,
                    717,
                    "Generalidades:\nKADABRA 480 SC es un insecticida a base de los "
                    "ingredientes activos Bifentrina y Fipronil.\n"
                    "Bifentrina es un piretroide de cuarta generación.\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Kadabra.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Bifentrina", "360 g/L"), ("Fipronil", "120 g/L")],
        )

    def test_iata_transport_label_is_not_treated_as_ia_active_label(self):
        page = PdfPage(
            page=11,
            text=(
                "14.3. Clase(s) de peligro para el transporte\n"
                "IATA\n"
                "9\n"
                "Peligro para el medio ambiente\n"
            ),
            blocks=[
                PdfTextBlock(78, 507, 100, 517, "IATA\n"),
                PdfTextBlock(100, 584, 278, 594, "9\nPeligro para el medio ambiente\n"),
            ],
        )
        doc = PdfDocument(
            file_name="HS Atrazine.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )
        self.assertEqual(extract_active_ingredients(doc), [])

    def test_rimon_wrapped_systematic_name_keeps_novaluron_as_active(self):
        block_text = (
            "2. COMPOSICIÓN / INFORMACIÓN SOBRE LOS COMPONENTES\n"
            "Ingrediente activo\n"
            "Novaluron: 1-[3-cloro-4-(1,1,2-trifluoro-2-trifluorometoxietoxi)\n"
            "fenil]-3- (2,6-difluorobenzoil) urea.\n"
            "N° CAS del i.a. :\n"
            "116714-46-6\n"
            "Número de N.U. del i.a. :\n"
            "2902\n"
        )
        page = PdfPage(
            page=1,
            text=block_text,
            blocks=[PdfTextBlock(85.1, 257.7, 526.1, 702.7, block_text)],
        )
        page3_text = (
            "9. PROPIEDADES FÍSICAS Y QUÍMICAS.\n"
            "Concentración: 100 g/l Novaluron.\n"
        )
        page3 = PdfPage(page=3, text=page3_text)
        doc = PdfDocument(
            file_name="26. HS Rimon.pdf",
            pages=[page, page3],
            page_count=2,
            character_count=len(block_text) + len(page3_text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [("Novaluron", "116714-46-6", "100 g/l")],
        )
        self.assertFalse(any("difluorobenzoil" in item.name.casefold() for item in items))

    def test_thiamethoxam_pure_sds_uses_product_name_not_hazard_classification(self):
        p1_text = (
            "1. PRODUCT AND COMPANY IDENTIFICATION\n"
            "1.1 Product identifiers\n"
            "Product name : Thiamethoxam\n"
            "Product Number : 37924\n"
            "CAS-No. : 153719-23-4\n"
        )
        p2_text = (
            "3. COMPOSITION/INFORMATION ON INGREDIENTS\n"
            "3.1 Substances\n"
            "Formula : C8H10ClN5O3S\n"
            "Molecular weight : 291.71 g/mol\n"
            "CAS-No. : 153719-23-4\n"
            "Hazardous components\n"
            "Component Classification Concentration\n"
            "Thiamethoxam\n"
            "Acute Tox. 4; Aquatic Acute 1; Aquatic Chronic 1; H302, H410\n"
            "<= 100 %\n"
        )
        page1 = PdfPage(
            page=1,
            text=p1_text,
            blocks=[
                PdfTextBlock(35.0,174.5,298.6,199.9,"1.1\nProduct identifiers\nProduct name\n: Thiamethoxam\n"),
                PdfTextBlock(64.8,201.5,268.0,255.8,"Product Number\n:\n37924\nBrand\n:\nSigma-Aldrich\nCAS-No.\n:\n153719-23-4\n"),
            ],
        )
        page2 = PdfPage(
            page=2,
            text=p2_text,
            blocks=[
                PdfTextBlock(35.0,115.3,512.9,189.9,
                    "3.1\nSubstances\nFormula\n:\nC8H10ClN5O3S\nMolecular weight\n:\n291.71 g/mol\nCAS-No.\n:\n153719-23-4\nHazardous components\nComponent\nClassification\nConcentration\n"),
                PdfTextBlock(64.6,197.8,443.1,241.9,
                    "Thiamethoxam\nAcute Tox. 4; Aquatic Acute 1;\nAquatic Chronic 1; H302,\nH410\n"),
                PdfTextBlock(449.7,209.0,494.3,219.8,"<= 100 %\n"),
            ],
        )
        doc = PdfDocument(
            file_name="30. HS Thiamethozam.pdf",
            pages=[page1, page2],
            page_count=2,
            character_count=len(p1_text) + len(p2_text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [("Thiamethoxam", "153719-23-4", "<= 100 %")],
        )
        self.assertFalse(any("acute tox" in item.name.casefold() for item in items))

    def test_single_component_sds_100_percent_confirms_product_identity(self):
        p1 = PdfPage(
            page=1,
            text=(
                "SECCIÓN 1. Identificación de la sustancia o la mezcla y de la sociedad o la empresa\n"
                "1.1. Identificador del producto\n"
                "Nombre comercial\n"
                "Atrazine\n"
                "Número CAS\n"
                "1912-24-9\n"
            ),
        )
        p3 = PdfPage(
            page=3,
            text=(
                "SECCIÓN 3. Composición/información sobre los componentes\n"
                "3.2. Mezclas\n"
                "Nombre químico Nº CAS Concentración Clasificación\n"
                "atrazina (ISO) 1912-24-9 100% Skin Sens. 1, Aquatic Acute 1\n"
            ),
        )
        doc = PdfDocument(
            file_name="HS Atrazine.pdf",
            pages=[p1, p3],
            page_count=2,
            character_count=len(p1.text) + len(p3.text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "atrazina (ISO)")
        self.assertEqual(items[0].concentration, "100%")
        self.assertEqual(items[0].cas, "1912-24-9")
        self.assertEqual(items[0].page, 3)

    def test_nombre_iupac_ia_field_exposes_cane_identity_and_cas(self):
        text = (
            "1. IDENTIFICACIÓN DEL PRODUCTO Y DE LA EMPRESA\n"
            "Nombre del producto: CANE 500 SC\n"
            "Nombre IUPAC (I.A): Ametrina, N2-etil-N4-isopropil-6-metiltio-1,3,5-triazina-2,4-diamina\n"
            "No CAS: 834-12-8\n"
            "Fórmula molecular: C9H17N5S\n"
        )
        items = extract_active_ingredients(document(text, "HS Cane.pdf"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Ametrina")
        self.assertEqual(items[0].cas, "834-12-8")

    def test_nombre_iupac_ia_field_exposes_ruklen_identity_and_cas(self):
        text = (
            "1. IDENTIFICACIÓN DEL PRODUCTO Y DE LA EMPRESA\n"
            "Nombre del producto: RUKLEN 200 SC\n"
            "Nombre IUPAC (I.A):\n"
            "Chlorantraniliprole, 3-bromo-4'-chloro-1-(3-chloro-2-pyridyl)-\n"
            "2'-methyl-6'-(methylcarbamoyl)pyrazole-5-carboxanilide\n"
            "No CAS:\n500008-45-7\n"
        )
        items = extract_active_ingredients(document(text, "HS Ruklen.pdf"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Chlorantraniliprole")
        self.assertEqual(items[0].cas, "500008-45-7")

    def test_flumyzin_active_table_joins_name_cas_and_percent_cells(self):
        page = PdfPage(
            page=2,
            text=(
                "3. COMPOSICIÓN/INFORMACIÓN DE LOS COMPONENTES\n"
                "3.1 Sustancia\n"
                "INGREDIENTE ACTIVO - NOMBRE IDENTIFICADOR DEL PRODUCTO PORCENTAJE\n"
                "Flumioxazin (2-[7-fluoro-3,4-dihydro-3-oxo-4-(2-propynyl)-"
                "2H-1,4-benzoxazin-6-yl]-4,5,6,7-tetrahydro-1H-isoindole-1,3(2H)-dione) "
                "*(103361-09-7).\n"
                "103361-09-7 (CAS)\n"
                "51%p\n"
            ),
            blocks=[
                PdfTextBlock(
                    98.1, 271.4, 510.9, 283.3,
                    "INGREDIENTE ACTIVO - NOMBRE IDENTIFICADOR DEL PRODUCTO PORCENTAJE\n",
                ),
                PdfTextBlock(468.7, 289.8, 490.5, 301.3, "51%p\n"),
                PdfTextBlock(308.4, 293.8, 381.1, 317.3, "103361-09-7 (CAS)\n600-425-7 (EC)\n"),
                PdfTextBlock(
                    73.1, 291.8, 181.2, 375.3,
                    "Flumioxazin (2-[7-fluoro-3,4-dihydro-3-oxo-4-\n"
                    "(2-propynyl)-2H-1,4-benzoxazin-6-yl]-4,5,6,7-\n"
                    "tetrahydro-1H-isoindole-1,3(2H)-dione) *\n"
                    "(103361-09-7).\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="HS Flumyzin.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )
        items = extract_active_ingredients(doc)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Flumioxazin")
        self.assertEqual(items[0].concentration, "51%p")
        self.assertEqual(items[0].cas, "103361-09-7")

    def test_other_identification_accepts_only_short_chemical_salt_identity(self):
        text = (
            "1. IDENTIFICACIÓN DEL PRODUCTO Y DE LA COMPAÑÍA\n"
            "1.1 Identificador SGA del producto: Panzer 747 WG\n"
            "1.2 Otros medios de identificación: sal amonio de glifosato.\n"
            "1.3 Uso recomendado del producto químico y restricciones: herbicida no selectivo\n"
        )
        items = extract_active_ingredients(document(text, "HS Panzer.pdf"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "sal amonio de glifosato")
        self.assertEqual(items[0].cas, "")

    def test_other_identification_does_not_promote_generic_synonym_prose(self):
        text = (
            "1. IDENTIFICACIÓN DEL PRODUCTO\n"
            "1.2 Otros medios de identificación: mezcla comercial para investigación y desarrollo.\n"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])

    def test_carbofuran_single_component_table_can_have_cas_before_name_row(self):
        p1 = PdfPage(
            page=1,
            text=(
                "Section 1. Identification of the Substance/Mixture and of the Company/Undertaking\n"
                "Product Name: Carbofuran\n"
            ),
        )
        p2 = PdfPage(
            page=2,
            text=(
                "Section 3. Composition/Information on Ingredients\n"
                "CAS # / RTECS #\n"
                "Hazardous Components (Chemical Name)/ REACH Registration No.\n"
                "Concentration\n"
                "1563-66-2\n"
                "FB9450000\n"
                "Carbofuran 100.0 %\n"
                "216-353-0\n"
            ),
        )
        doc = PdfDocument(
            file_name="HS Cabofuran 2.pdf",
            pages=[p1, p2],
            page_count=2,
            character_count=len(p1.text) + len(p2.text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )
        items = extract_active_ingredients(doc)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Carbofuran")
        self.assertEqual(items[0].concentration, "100.0 %")
        self.assertEqual(items[0].cas, "1563-66-2")

    def test_poliniza_two_panel_table_prefers_concentration_bearing_identity_row(self):
        page = PdfPage(
            page=1,
            text=(
                "COMPOSICIÓN GARANTIZADA: PROPIEDADES DEL PRODUCTO FORMULADO:\n"
                "INGREDIENTE ACTIVO CONCENTRACIÓN (g/Kg)\n"
                "Aspecto: Polvo blanco\n"
                "Ácido 1-naftalenacético (ANA) 60 g/kg\n"
                "2-naphthalen-1-ylacetic acid\n"
                "Ingredientes aditivos c.s.p. 1 kg"
            ),
            blocks=[
                PdfTextBlock(
                    23.5, 416.8, 531.3, 460.9,
                    "COMPOSICIÓN GARANTIZADA:\n"
                    "PROPIEDADES DEL PRODUCTO\nFORMULADO:\n"
                    "INGREDIENTE ACTIVO\nCONCENTRACIÓN (g/Kg)\n",
                ),
                PdfTextBlock(447.0, 458.9, 502.5, 471.0, "Polvo blanco\n"),
                PdfTextBlock(353.6, 458.3, 362.2, 472.6, "o:\n"),
                PdfTextBlock(
                    26.6, 458.3, 353.8, 489.3,
                    "Aspect\nÁcido 1-naftalenacético (ANA)\n60 g/kg\n",
                ),
                PdfTextBlock(
                    26.6, 522.8, 150.5, 536.7,
                    "Ingredientes aditivos c.s.p.\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Poliniza.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Ácido 1-naftalenacético (ANA)", "60 g/kg")],
        )

    def test_sart_colon_identity_row_beats_additive_csp_block(self):
        page = PdfPage(
            page=1,
            text=(
                "COMPOSICIÓN GARANTIZADA:\n"
                "Ingredientes activos:\n"
                "Teflubenzuron: 150 g/L 1-(3,5-dichloro-2,4-difluorophenyl)-"
                "3-(2,6-difluorobenzoyl) urea, formulación a 20°C.\n"
                "C.s.p 1 L\nIngredientes aditivos:"
            ),
            blocks=[
                PdfTextBlock(67.9, 496.4, 256.7, 516.8, "COMPOSICIÓN GARANTIZADA:\n"),
                PdfTextBlock(67.9, 524.8, 176.6, 543.8, "Ingredientes activos:\n"),
                PdfTextBlock(
                    67.9, 542.8, 504.5, 558.0,
                    "Teflubenzuron: 150 g/L "
                    "1-(3,5-dichloro-2,4-difluorophenyl)-"
                    "3-(2,6-difluorobenzoyl) urea, formulación a 20°C.\n",
                ),
                PdfTextBlock(
                    67.9, 565.6, 179.9, 598.8,
                    "C.s.p 1 L\nIngredientes aditivos:\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Sart.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Teflubenzuron", "150 g/L")],
        )

    def test_touchdown_inline_identity_stops_before_warning_prose(self):
        page = PdfPage(
            page=2,
            text=(
                "Uso: Herbicida Agrícola\n"
                "Ingredientes activos: Glifosato Ácido 500 g/l\n"
                "Nombre Químico: N-(fosfonometil)glicina.\n"
                "LEA CUIDADOSAMENTE LA ETIQUETA Y LA HOJA INFORMATIVA "
                "ANTES DE USAR ESTE PRODUCTO"
            ),
            blocks=[
                PdfTextBlock(
                    95.6, 125.6, 315.1, 185.9,
                    "Uso: Herbicida Agrícola\n"
                    "Tipo de formulación: Concentrado Soluble (SL)\n"
                    "Registro Nacional ICA No.: 140\n"
                    "Ingredientes activos: Glifosato Ácido 500 g/l\n"
                    "Nombre Químico: N-(fosfonometil)glicina.\n",
                ),
                PdfTextBlock(
                    90.0, 183.6, 523.5, 255.4,
                    "LEA CUIDADOSAMENTE LA ETIQUETA Y LA HOJA INFORMATIVA "
                    "ANTES DE USAR ESTE\nPRODUCTO\n"
                    "PRECAUCIONES Y ADVERTENCIAS DE USO Y APLICACIÓN\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Touchdown.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Glifosato Ácido", "500 g/l")],
        )

    def test_vantacor_web_catalog_does_not_enter_active_identity(self):
        page = PdfPage(
            page=3,
            text=(
                "INSECTICIDAS\nPresipel\nPirestar 38 EC\n"
                "Ingrediente(s) Activo(s)\nChlorantraniliprole\n"
                "Concentración\n600 g/L\n"
                "Categoría Toxicológica\nIV Ligeramente Peligroso"
            ),
            blocks=[
                PdfTextBlock(
                    124.1, 615.1, 453.0, 633.1,
                    "Ingrediente(s) Activo(s)\nChlorantraniliprole\n",
                ),
                PdfTextBlock(378.9, 624.2, 435.5, 646.6, "Presipel\n"),
                PdfTextBlock(153.9, 623.9, 260.9, 648.7, "Pirestar® 38 EC\n"),
                PdfTextBlock(
                    147.7, 645.1, 424.0, 663.1,
                    "Concentración\n600 g/L\n",
                ),
                PdfTextBlock(
                    125.6, 705.1, 469.0, 723.1,
                    "Categoría Toxicológica\nIV Ligeramente Peligroso\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Vantacor.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Chlorantraniliprole", "600 g/L")],
        )

    def test_serok_two_column_layout_does_not_cross_into_application_mode(self):
        page = PdfPage(
            page=1,
            text=(
                "RECOMENDACIONES DE USO\n"
                "MODO DE APLICACIÓN\n"
                "INGREDIENTE ACTIVO\n"
                "Por aspersión.\n"
                "Nombre Común\n"
                "ACEFATO\n450 g/Kg\n"
                "IMIDACLOPRID\n250 g/Kg\n"
                "Nombre Químico\n"
                "ACEFATO:\n(RS)-O, S-dimethyl acetylphosphoramidothioate\n"
                "IMIDACLOPRID:\n(E)-1-(6-chloro-3-pyridylmethyl)-N-nitroimidazolidin-2-ylideneaine\n"
                "No. CAS\n"
                "ACEFATO: 30560-19-1\n"
                "IMIDACLOPRID: 138261-41-3\n"
                "FORMULACIÓN\nPOLVO MOJABLE (WP)\n"
            ),
            blocks=[
                PdfTextBlock(311.2, 125.9, 415.1, 135.9, "MODO DE APLICACIÓN\n"),
                PdfTextBlock(42.6, 146.1, 145.7, 156.1, "INGREDIENTE ACTIVO\n"),
                PdfTextBlock(311.2, 146.9, 371.8, 156.9, "Por aspersión.\n"),
                PdfTextBlock(
                    42.6, 166.7, 187.3, 197.7,
                    "Nombre Común\nACEFATO\n450 g/Kg\nIMIDACLOPRID\n250 g/Kg\n",
                ),
                PdfTextBlock(
                    42.6, 208.1, 236.3, 239.2,
                    "Nombre Químico\nACEFATO:\n"
                    "(RS)-O, S-dimethyl acetylphosphoramidothioate\n",
                ),
                PdfTextBlock(
                    42.6, 249.8, 255.9, 280.6,
                    "IMIDACLOPRID:\n"
                    "(E)-1-(6-chloro-3-pyridylmethyl)-N-nitroimidazolidin-2-\n"
                    "ylideneaine\n",
                ),
                PdfTextBlock(42.6, 290.9, 81.1, 301.0, "No. CAS\n"),
                PdfTextBlock(42.6, 311.9, 138.7, 322.0, "ACEFATO: 30560-19-1\n"),
                PdfTextBlock(
                    42.6, 332.6, 166.2, 342.6,
                    "IMIDACLOPRID: 138261-41-3\n",
                ),
                PdfTextBlock(42.6, 353.1, 112.6, 363.1, "FORMULACIÓN\n"),
            ],
        )
        doc = PdfDocument(
            file_name="28. FT Serok.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("ACEFATO", "450 g/Kg"), ("IMIDACLOPRID", "250 g/Kg")],
        )
        self.assertNotIn("Por aspersión", [item.name for item in items])

    def test_durmix_group_metadata_is_not_promoted_to_active_identity(self):
        text = (
            "SECCION 1 PRODUCTO E IDENTIFICACION DE LA COMPAÑIA\n"
            "Nombre del producto: DURMIX 48\n"
            "Clase: Insecticida\n"
            "Ingrediente Activo: Chlorpyrifos\n"
            "Grupo: Organofosforado\n"
            "Formulación: Concentrado Emulsionable\n"
            "CAS N°: 2921-88-2\n"
        )

        items = extract_active_ingredients(document(text, "HS Durmix.pdf"))

        self.assertEqual([item.name for item in items], ["Chlorpyrifos"])
        self.assertNotIn("Grupo", [item.name for item in items])
        self.assertNotIn("Organofosforado", [item.name for item in items])

    def test_inex_split_label_uses_right_value_cell_and_ignores_compatibility_row(self):
        page = PdfPage(
            page=1,
            text=(
                "Ingredientes\nActivos\n"
                "Alquil polieter alcohol\netoxilado\nAlquil poliglicol\n"
                "Aril polietoxietanol\n26.37%\n"
                "Ingrediente\nAditivo\nAgua\n73.63%\n"
                "Compatibilidad con\nIngredientes activos.\nCompatible\n"
                "Velocidad de Mezcla.\nRápida.\nAdherencia.\nExcelente.\n"
            ),
            blocks=[
                PdfTextBlock(
                    48.0, 206.6, 221.3, 224.3,
                    "Clasificación              Surfactante\n",
                ),
                PdfTextBlock(
                    48.0, 239.9, 537.1, 251.0,
                    "Descripción química\n"
                    "Mezcla de alcoholes etoxilados poliglicol y aril polietoxietanol. "
                    "De carácter no-iónico\n",
                ),
                PdfTextBlock(48.0, 277.8, 110.3, 300.5, "Ingredientes\nActivos\n"),
                PdfTextBlock(
                    163.6, 263.4, 260.7, 309.0,
                    "Alquil polieter alcohol\netoxilado\n"
                    "Alquil poliglicol\nAril polietoxietanol\n",
                ),
                PdfTextBlock(300.5, 283.6, 337.3, 294.7, "26.37%\n"),
                PdfTextBlock(
                    351.0, 263.4, 534.7, 309.0,
                    "Este tipo de material cumple con normas de Regulación EPA\n",
                ),
                PdfTextBlock(48.0, 315.8, 116.1, 329.2, "Ingrediente\n"),
                PdfTextBlock(
                    48.0, 330.6, 353.7, 349.8,
                    "Aditivo\nAgua\n73.63%\n",
                ),
                PdfTextBlock(
                    42.6, 625.2, 227.8, 679.0,
                    "Homogeneidad.\nExcelente\nPersistencia.\nNormal\n"
                    "Compatibilidad con\nIngredientes activos.\n",
                ),
                PdfTextBlock(181.1, 656.4, 234.5, 667.5, "Compatible\n"),
                PdfTextBlock(
                    42.6, 680.1, 230.6, 720.3,
                    "Velocidad de Mezcla.\nRápida.\nAdherencia.\nExcelente.\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT INEX A.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [item.name for item in items],
            [
                "Alquil polieter alcohol etoxilado",
                "Alquil poliglicol",
                "Aril polietoxietanol",
            ],
        )
        self.assertNotIn("Ingrediente", [item.name for item in items])
        self.assertNotIn("Agua", [item.name for item in items])
        self.assertNotIn("Velocidad de Mezcla", [item.name for item in items])
        self.assertNotIn("Excelente", [item.name for item in items])

    def test_fossile_footnote_does_not_promote_pr_as_active_identity(self):
        page1_text = (
            "3. OTRAS CARACTERÍSTICAS DEL PRODUCTO\n"
            "Ingrediente Activo: Fosetyl-aluminium\n"
            "Nombre IUPAC I.A: aluminium tris (ethyl phosphonate)\n"
            "Grupo Químico: Organofosforado\n"
            "Formulación: Polvo mojable (WP)\n"
            "Uso: Fungicida de uso agrícola\n"
            "Concentración: 800 g/Kg\n"
        )
        page2_text = (
            "6. RECOMENDACIONES DE USO\n"
            "P.C.: Periodo de Carencia: Período en días entre la última aplicación del PQUA "
            "y la cosecha.\n"
            "ingrediente activo en el producto agrícola sea menor o igual al LMR aceptado "
            "por la ANC para ese cultivo, basado en los estudios de residuos.\n"
            "P.R.: Periodo de Reentrada: Tiempo que debe transcurrir entre el tratamiento "
            "o aplicación de un plaguicida y el ingreso de personas o animales al área.\n"
            "N.A.: No aplica.\n"
        )
        doc = PdfDocument(
            file_name="24. FT Fossile 80 WP.pdf",
            pages=[
                PdfPage(
                    page=1,
                    text=page1_text,
                    blocks=[
                        PdfTextBlock(
                            90.7, 476.3, 481.1, 593.3,
                            page1_text,
                        )
                    ],
                ),
                PdfPage(
                    page=2,
                    text=page2_text,
                    blocks=[
                        PdfTextBlock(
                            85.1, 588.6, 523.3, 661.3,
                            page2_text,
                        )
                    ],
                ),
            ],
            page_count=2,
            character_count=len(page1_text) + len(page2_text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Fosetyl-aluminium", "800 g/Kg")],
        )
        self.assertFalse(any(match_key(item.name) == "p r" for item in items))

    def test_metsulfuron_split_name_number_and_unit_collapses_to_one_identity(self):
        page = PdfPage(
            page=1,
            text=(
                "GENERALIDADES\n"
                "Ingrediente Activo:\nMetsulfuron Metil\n"
                "Concentración:\n600 g/kg\n"
                "COMPOSICIÓN\nIngrediente activo:\n"
                "Metsulfuron\nMetil........................................600\n"
                "g/kg\n"
                "methyl 2-(4-methoxy-6-methyl-1,3,5-triazin-2-"
                "ylcarbamoylsulfamoyl)benzoate\n"
            ),
            blocks=[
                PdfTextBlock(
                    70.8, 333.9, 308.5, 345.9,
                    "Ingrediente Activo:\nMetsulfuron Metil\n",
                ),
                PdfTextBlock(
                    70.8, 358.9, 271.5, 370.9,
                    "Concentración:\n600 g/kg\n",
                ),
                PdfTextBlock(
                    71.0, 647.3, 541.2, 715.6,
                    "COMPOSICIÓN\nIngrediente activo:\nMetsulfuron\n \n"
                    "Metil........................................600\n"
                    "g/kg\n"
                    "methyl 2-(4-methoxy-6-methyl-1,3,5-triazin-2-"
                    "ylcarbamoylsulfamoyl)benzoate\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Metsulfuron.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Metsulfuron Metil", "600 g/kg")],
        )

    def test_paired_multi_active_shorthand_pairs_each_name_with_its_concentration(self):
        text = (
            "COMPOSICIÓN GARANTIZADA:\n"
            "Ingredientes activos:\n"
            "Fosetyl + Propamocarb / 310+530 g/L\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 litro\n"
        )

        items = extract_active_ingredients(document(text, "FT Prevalor SL.pdf"))

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [
                ("Fosetyl", "310 g/L"),
                ("Propamocarb", "530 g/L"),
            ],
        )

    def test_credit_keeps_glyphosate_and_rejects_equivalence_and_biological_target(self):
        page1_text = (
            "Ingrediente Activo:\n"
            "Glifosato 680 g/kg\n"
            "N - (phosphonomethyl) glycine, equivalente a 747 g/kg de Glyphosate\n"
            "Monoammonium salt, de formulacion a 20ºC,\n"
            "Ingredientes Aditivos: c.s.p. 1 kg\n"
        )
        page3_text = (
            "INGREDIENTE ACTIVO:\n"
            "GLIFOSATO\n"
            "Liendre puerco Echinochloa colonum,\n"
            "Falsa caminadora Ischaemum rugosum,\n"
            "Pata de gallina Eleusine indica\n"
            "3.0 Kg/ha\n"
            "Anexos: RECOMENDACIONES DE USO - REGISTROS\n"
            "PAÍS MARCA CULTIVO OBJETIVO BIOLÓGICO DOSIS\n"
        )
        doc = PdfDocument(
            file_name="FT Credit.pdf",
            pages=[
                PdfPage(
                    page=1,
                    text=page1_text,
                    blocks=[
                        PdfTextBlock(
                            54.7, 209.5, 292.1, 275.1,
                            "Ingrediente Activo:\n"
                            "Glifosato ……………………………………...………….680 g/kg\n"
                            "N - (phosphonomethyl) glycine, equivalente a 747 g/kg de Glyphosate\n"
                            "Monoammonium salt,  de formulacion a 20ºC,\n"
                            "Ingredientes Aditivos: …………………………….....…c.s.p. 1  kg\n",
                        ),
                    ],
                ),
                PdfPage(
                    page=3,
                    text=page3_text,
                    blocks=[
                        PdfTextBlock(467.9, 142.0, 554.5, 153.8, "INGREDIENTE ACTIVO:\n"),
                        PdfTextBlock(511.0, 152.0, 554.5, 163.8, "GLIFOSATO\n"),
                        PdfTextBlock(
                            76.4, 177.0, 472.9, 196.8,
                            "Anexos:\nRECOMENDACIONES DE USO - REGISTROS\n",
                        ),
                        PdfTextBlock(
                            99.2, 218.7, 524.7, 230.8,
                            "PAÍS\nMARCA\nCULTIVO\nOBJETIVO BIOLÓGICO\nDOSIS\n",
                        ),
                        PdfTextBlock(
                            312.8, 235.0, 462.8, 315.5,
                            "Liendre puerco   Echinochloa colonum,\n"
                            "Falsa caminadora Ischaemum rugosum,\n"
                            "Pata de gallina Eleusine indica\n",
                        ),
                        PdfTextBlock(
                            475.2, 235.2, 557.6, 315.5,
                            "3.0 Kg/ha\n"
                            "Realizar aplicaciones en post emergencia, con las malezas en crecimiento activo.\n",
                        ),
                    ],
                ),
            ],
            page_count=2,
            character_count=len(page1_text) + len(page3_text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name.casefold(), item.concentration) for item in items],
            [("glifosato", "680 g/kg")],
        )
        self.assertFalse(any("equivalente" in item.name.casefold() for item in items))
        self.assertFalse(any("monoammonium" in item.name.casefold() for item in items))
        self.assertFalse(any("echinochloa" in item.name.casefold() for item in items))
        self.assertFalse(any(item.concentration.casefold().endswith("kg/ha") for item in items))

    def test_touchdown_iupac_equivalence_is_not_promoted_to_active_identity(self):
        p1 = PdfPage(
            page=1,
            text=(
                "2. GENERALIDADES\n"
                "Ingredientes Activos: Glifosato Acido\n"
                "Nombre Químico:\n"
                "(IUPAC)*\n"
                "N-(fosfonometil)glicina,\n"
                "equivalente a 620 g/L de N-(fosfonometil)glicina sal de potasio\n"
                "Formulación: Concentrado soluble\n"
                "Concentración: 500 g/l\n"
                "Nombre Comercial: TOUCHDOWN IQ SL\n"
            ),
            blocks=[
                PdfTextBlock(
                    91.6, 305.2, 273.1, 319.5,
                    "Ingredientes Activos: Glifosato Acido\n",
                ),
                PdfTextBlock(
                    91.6, 327.5, 178.2, 353.2,
                    "Nombre Químico:\n(IUPAC)*\n",
                ),
                PdfTextBlock(
                    203.0, 327.7, 482.0, 352.7,
                    "N-(fosfonometil)glicina,\n"
                    "equivalente a 620 g/L de "
                    "N-(fosfonometil)glicina sal de potasio\n",
                ),
                PdfTextBlock(
                    91.6, 356.4, 297.5, 370.7,
                    "Formulación:\nConcentrado soluble\n",
                ),
                PdfTextBlock(
                    91.6, 376.7, 235.8, 391.0,
                    "Concentración:\n500 g/l\n",
                ),
            ],
        )
        p2 = PdfPage(
            page=2,
            text=(
                "Uso: Herbicida Agrícola\n"
                "Tipo de formulación: Concentrado Soluble (SL)\n"
                "Ingredientes activos: Glifosato Ácido 500 g/l\n"
                "Nombre Químico: N-(fosfonometil)glicina.\n"
            ),
        )
        doc = PdfDocument(
            file_name="FT Touchdown IQ SL.pdf",
            pages=[p1, p2],
            page_count=2,
            character_count=len(p1.text) + len(p2.text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Glifosato Acido")
        self.assertEqual(items[0].concentration, "500 g/l")
        self.assertNotIn("IUPAC", items[0].name)
        self.assertNotIn("equivalente", items[0].name.casefold())

    def test_touchdown_table_metadata_does_not_become_fake_ingredients(self):
        page = PdfPage(
            page=2,
            text=(
                "2. Composición: Información sobre los Ingredientes\n"
                "Ingrediente activo(s)\n"
                "Glifosato Potasio\n"
                "No. CAS\nNombre\nSímbolo de Peligro\n"
                "Riesgos Especiales\nConcentración\n"
                "39600-42-5 Glifosato Potasio\nN\nR51/53\n44.7% W/W"
            ),
            blocks=[
                PdfTextBlock(
                    72,
                    179,
                    306,
                    263,
                    "2. Composición: Información sobre los Ingredientes\n"
                    "Característica química\n"
                    "Tipo de formulación\nConcentrado soluble\n"
                    "Uso\nHerbicida\n"
                    "Ingrediente activo(s)\n"
                    "Glifosato Potasio\n",
                ),
                PdfTextBlock(
                    72,
                    263,
                    542,
                    437,
                    "No. CAS\n"
                    "Nombre\n"
                    "Símbolo de Peligro\n"
                    "Riesgos Especiales\n"
                    "Concentración\n"
                    "39600-42-5 Glifosato Potasio\n"
                    "N\nR51/53\n44.7% W/W\n"
                    "3. Identificación de Peligros\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="HS Touchdown.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Glifosato Potasio")
        self.assertEqual(items[0].concentration, "44.7% W/W")
        self.assertEqual(items[0].cas, "39600-42-5")

    def test_ninkha_split_nombre_quimico_is_not_promoted_to_active_identity(self):
        page = PdfPage(
            page=2,
            text=(
                "COMPOSICIÓN GARANTIZADA:\n"
                "Ingrediente activo:\n"
                "Flubendiamide 480 g/L\n"
                "Nombre\n"
                "químico:\n"
                "3-iodo-N'-(2-mesyl-1,1-dimethylethyl)-N-{4-[...]}phthalamide"
            ),
            blocks=[
                PdfTextBlock(72, 590, 256, 603, "COMPOSICIÓN GARANTIZADA:\n"),
                PdfTextBlock(72, 619, 166, 631, "Ingrediente activo:\n"),
                PdfTextBlock(72, 645, 185, 657, "Flubendiamide 480 g/L\n"),
                PdfTextBlock(
                    72,
                    672,
                    540,
                    699,
                    "Nombre\nquímico:\n"
                    "3-iodo-N'-(2-mesyl-1,1-dimethylethyl)-N-{4-[...]}phthalamide\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Ninkha.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Flubendiamide", "480 g/L")],
        )

    def test_panzer_k_explicit_narrative_declares_glyphosate_identity(self):
        text = (
            "2. DESCRIPCIÓN\n"
            "Panzer K SL es un herbicida que tiene como ingrediente activo "
            "glifosato en forma de sal potasio en una concentración de "
            "443 g/L equivalente a 360 g/L del ácido.\n"
            "3. CARACTERÍSTICAS"
        )
        items = extract_active_ingredients(document(text, "FT Panzer k.pdf"))

        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0].name.casefold(),
            "glifosato en forma de sal potasio",
        )
        self.assertEqual(items[0].concentration, "443 g/L")
        self.assertEqual(items[0].cas, "")
        self.assertEqual(items[0].page, 1)

    def test_panzer_k_wrapped_narrative_does_not_create_potassium_fragment(self):
        text = (
            "1. NOMBRE\n"
            "Panzer K SL Registro Nacional ICA No. PL0009912023\n"
            "2. DESCRIPCIÓN\n"
            "Panzer K SL es un herbicida que tiene como ingrediente activo "
            "glifosato en forma de sal\n"
            "potasio en una concentración de 443 g/L equivalente a 360 g/L del ácido.\n"
            "3. CARACTERÍSTICAS\n"
        )
        page = PdfPage(
            page=1,
            text=text,
            blocks=[PdfTextBlock(85.1, 214.3, 512.6, 238.8, text)],
        )
        doc = PdfDocument(
            file_name="18. FT Panzer k.pdf",
            pages=[page],
            page_count=1,
            character_count=len(text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name.casefold(), item.concentration) for item in items],
            [("glifosato en forma de sal potasio", "443 g/L")],
        )
        self.assertFalse(
            any("potasio en una concentración de" == item.name.casefold() for item in items)
        )

    def test_panzer_747_preserves_ammonium_salt_as_single_active_identity(self):
        text = (
            "2. DESCRIPCIÓN\n"
            "PANZER 747 WG es un herbicida que tiene como ingrediente activo "
            "glifosato en forma de sal\n"
            "amoniacal en una concentración de 747,0 g/kg\n"
            "3. CARACTERÍSTICAS\n"
            "Contenido de Glifosato (sal amonio): 722,0 - 772,0 g./kg.\n"
        )
        page = PdfPage(
            page=1,
            text=text,
            blocks=[PdfTextBlock(85.1, 120.6, 512.8, 668.9, text)],
        )
        doc = PdfDocument(
            file_name="19. FT Panzer.pdf",
            pages=[page],
            page_count=1,
            character_count=len(text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name.casefold(), item.concentration) for item in items],
            [("glifosato en forma de sal amoniacal", "747,0 g/kg")],
        )
        self.assertFalse(
            any("amoniacal en una concentración de" == item.name.casefold() for item in items)
        )

    def test_kunfu_sds_correlates_other_identifier_and_concentration_as_active_identity(self):
        page1 = (
            "1. IDENTIFICACIÓN DEL PRODUCTO Y DE LA COMPAÑÍA\n"
            "1.1 Identificador SGA del producto: KUNFU 100 EC\n"
            "1.2 Otros medios de identificación: bifentrina.\n"
            "1.3 Uso recomendado del producto químico y restricciones: "
            "insecticida para uso agrícola, prohibido el uso doméstico.\n"
        )
        page7 = (
            "9. PROPIEDADES FISICOQUIMICAS\n"
            "Caracterización del producto\n"
            "Concentración: 100g/L de bifentrina.\n"
        )
        doc = PdfDocument(
            file_name="17. HS Kunfu.pdf",
            pages=[
                PdfPage(page=1, text=page1),
                PdfPage(page=7, text=page7),
            ],
            page_count=2,
            character_count=len(page1) + len(page7),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name.casefold(), item.concentration) for item in items],
            [("bifentrina", "100g/L")],
        )

    def test_other_identifier_alone_does_not_become_active_identity(self):
        text = (
            "1.2 Otros medios de identificación: bifentrina.\n"
            "1.3 Uso recomendado: insecticida para uso agrícola.\n"
            "Información general del producto sin concentración química explícita.\n"
        )
        items = extract_active_ingredients(document(text, "sds.pdf"))
        self.assertEqual(items, [])

    def test_polythion_uses_only_sulfur_not_usage_or_ecotox_endpoints(self):
        text = (
            "1.1. Identificador del producto\n"
            "Ingrediente Activo:\n"
            "Azufre CAS 7704-34-9\n"
            "1.2. Usos pertinentes identificados\n"
            "Uso General: Fungicida Agrícola.\n"
            "12. INFORMACIÓN ECOTOXICOLOGIA\n"
            "Ingrediente activo\n"
            "CL50 96 horas, trucha arcoiris: 0.063 ppm\n"
            "EC50 96 horas, Daphnia magna: 0.063 ppm\n"
        )
        items = extract_active_ingredients(document(text, "19. HS Polythion SC.pdf"))
        self.assertEqual(
            [(item.name, item.cas) for item in items],
            [("Azufre", "7704-34-9")],
        )
        self.assertNotIn("Uso General", [item.name for item in items])
        self.assertFalse(any("CL50" in item.name for item in items))

    def test_polythion_real_page_geometry_does_not_promote_version_revision(self):
        page1_text = (
            "1.1. Identificador del producto\n"
            "Ingrediente Activo:\n"
            "Azufre CAS 7704-34-9\n"
            "1.2. Usos pertinentes identificados\n"
            "Uso General: Fungicida Agrícola.\n"
        )
        page2_text = (
            "SECCIÓN 3: COMPOSICIÓN / INFORMACIÓN SOBRE LOS COMPONENTES\n"
            "3.1. SUSTANCIA\n"
            "Nombre CAS Concentración\n"
            "Azufre\nAditivos\n"
            "7704-34-9\nn.a\n"
            "720 g/l\nc.s.p. 1 l\n"
        )
        page5_text = (
            "SECCIÓN 12: SECCIÓN: INFORMACIÓN ECOTOXICOLOGIA\n"
            "12.1. TOXICIDAD\n"
            "Ingrediente activo\n"
            "CL50 96 horas, trucha arcoiris: 0.063 ppm\n"
            "VERSION: 3 SDS-H&S-106\n"
            "REVISION: 21-Nov-2023\n"
        )
        doc = PdfDocument(
            file_name="19. HS Polythion SC.pdf",
            pages=[
                PdfPage(page=1, text=page1_text),
                PdfPage(page=2, text=page2_text),
                PdfPage(
                    page=5,
                    text=page5_text,
                    blocks=[
                        PdfTextBlock(
                            32.4, 667.4, 292.7, 678.5,
                            "SECCIÓN 12: SECCIÓN: INFORMACIÓN ECOTOXICOLOGIA\n",
                        ),
                        PdfTextBlock(36.0, 680.9, 125.6, 693.7, "12.1.\nTOXICIDAD\n"),
                        PdfTextBlock(
                            36.0, 705.2, 224.1, 729.6,
                            "Ingrediente activo\n"
                            "CL50 96 horas, trucha arcoiris: 0.063 ppm\n",
                        ),
                        PdfTextBlock(
                            36.0, 735.9, 572.0, 756.5,
                            "VERSION: 3 SDS-H&S-106\nREVISION: 21-Nov-2023\n",
                        ),
                    ],
                ),
            ],
            page_count=3,
            character_count=len(page1_text) + len(page2_text) + len(page5_text),
            pages_with_text=3,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [("Azufre", "7704-34-9", "720 g/l")],
        )
        self.assertNotIn("VERSION", [item.name for item in items])
        self.assertNotIn("REVISION", [item.name for item in items])

    def test_dow_similar_active_toxicology_references_do_not_create_identity(self):
        page8_text = (
            "11. INFORMACIÓN TOXICOLÓGICA\n"
            "Toxicidad Sistémica de Organo Blanco Específico (Exposición Repetida)\n"
            "Para materiales similares(s):\n"
            "Glifosato.\n"
            "Carcinogenicidad\n"
            "Para ingrediente(s) activo(s) similare(s). Glifosato. "
            "No provocó cáncer en animales de laboratorio.\n"
            "Teratogenicidad\n"
            "Para ingrediente(s) activo(s) similare(s). Glifosato. "
            "Es tóxico para el feto de animales de laboratorio.\n"
            "Toxicidad para la reproducción\n"
            "Para ingrediente(s) activo(s) similare(s). Glifosato. "
            "En estudios realizados sobre animales de laboratorio, sólo se han "
            "demostrado efectos en la reproducción a dosis que también produjeron "
            "toxicidad importante en los progenitores.\n"
        )
        page9_text = (
            "12. INFORMACIÓN ECOLÓGICA\n"
            "Persistencia y degradabilidad\n"
            "Glifosato Sal DMA\n"
            "Biodegradabilidad: Para ingrediente(s) activo(s) similare(s). "
            "Glifosato. Puede ocurrir una biodegradación en condiciones aeróbicas.\n"
            "Potencial de bioacumulación\n"
            "Glifosato Sal DMA\n"
            "Bioacumulación: Para ingrediente(s) activo(s) similare(s). "
            "Glifosato. El potencial de bioconcentración es bajo.\n"
            "Movilidad en el suelo\n"
            "Glifosato Sal DMA\n"
            "Para ingrediente(s) activo(s) similare(s).\n"
            "Glifosato.\n"
            "Se prevé que el material sea relativamente inmóvil en el suelo.\n"
        )
        doc = PdfDocument(
            file_name="HS Dow.pdf",
            pages=[
                PdfPage(
                    page=8,
                    text=page8_text,
                    blocks=[
                        PdfTextBlock(
                            79.2, 233.2, 531.7, 278.9,
                            "Carcinogenicidad\n"
                            "Para ingrediente(s) activo(s) similare(s).  Glifosato.  "
                            "No provocó cáncer en animales de laboratorio.\n"
                            "Peso de la evaluación de la evidencia de estudios "
                            "epidemiológicos apoya ninguna asociación entre la "
                            "exposición al glifosato y el cáncer.\n",
                        ),
                        PdfTextBlock(
                            79.2, 290.7, 534.6, 324.9,
                            "Teratogenicidad\n"
                            "Para ingrediente(s) activo(s) similare(s).  Glifosato.  "
                            "Es tóxico para el feto de animales de laboratorio a dosis "
                            "tóxicas para la madre.\n",
                        ),
                        PdfTextBlock(
                            79.2, 336.6, 504.0, 382.4,
                            "Toxicidad para la reproducción\n"
                            "Para ingrediente(s) activo(s) similare(s).  Glifosato.  "
                            "En estudios realizados sobre animales de laboratorio, "
                            "sólo se han demostrado efectos en la reproducción.\n",
                        ),
                    ],
                ),
                PdfPage(
                    page=9,
                    text=page9_text,
                    blocks=[
                        PdfTextBlock(
                            115.2, 359.7, 521.5, 382.4,
                            "Biodegradabilidad: Para ingrediente(s) activo(s) "
                            "similare(s).  Glifosato.  Puede ocurrir una biodegradación "
                            "en condiciones aeróbicas.\n",
                        ),
                        PdfTextBlock(
                            115.2, 463.1, 523.0, 508.9,
                            "Bioacumulación: Para ingrediente(s) activo(s) similare(s).  "
                            "Glifosato.  El potencial de bioconcentración es bajo.\n",
                        ),
                        PdfTextBlock(
                            115.2, 589.9, 456.3, 623.9,
                            "Para ingrediente(s) activo(s) similare(s).\n"
                            "Glifosato.\n"
                            "Se prevé que el material sea relativamente inmóvil en el suelo.\n",
                        ),
                    ],
                ),
            ],
            page_count=2,
            character_count=len(page8_text) + len(page9_text),
            pages_with_text=2,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(items, [])

    def test_metsulfuron_ecology_endpoints_do_not_become_active_identity(self):
        text = (
            "IngredienteActivo:\n"
            "Metsulfuron methyl 600 g/kg\n"
            "CAS/EPA/EU Número de registro del Ingrediente Activo:\n"
            "CAS 74223-64-6\n"
            "12. INFORMACIÓN ECOLÓGICA\n"
            "El ingrediente activo es persistente en aguas, tiene alto potencial "
            "de lixiviación y es altamente tóxico a organismos acuáticos.\n"
            "Aves:\n"
            "DL50 pato > 2510 mg/kg/pc\n"
            "CL50 pato > 1275 mg/kg/pc\n"
        )
        items = extract_active_ingredients(document(text, "20. HS Metsulfuron.pdf"))
        self.assertEqual([item.name for item in items], ["Metsulfuron methyl"])
        self.assertFalse(any(item.name.startswith("DL50") for item in items))

    def test_fossile_name_active_field_wins_over_ecotoxicology_rows(self):
        text = (
            "1. IDENTIFICACIÓN DEL PRODUCTO\n"
            "Nombre Ingrediente Activo: Fosetyl-aluminium\n"
            "Número CAS: 39148-24-8\n"
            "3. INFORMACIÓN SOBRE COMPONENTES\n"
            "Componente Número CAS Concentración\n"
            "Fosetyl-aluminium 39148-24-8 800 g/Kg\n"
            "12. INFORMACIÓN ECO TOXICOLÓGICA\n"
            "12.1. Toxicidad (Ingrediente Activo: Fosetyl-aluminium)\n"
            "Peces (Oncorhynchus mykiss)) CL50, 96 h: 251.95 mg/l\n"
            "Crustáceos (Daphnia magna) CE50, 48 h: 304 mg/l\n"
        )
        items = extract_active_ingredients(document(text, "24. HS Fossile 80 WP.pdf"))
        self.assertEqual([item.name for item in items], ["Fosetyl-aluminium"])
        self.assertFalse(any(item.name.startswith("Peces") for item in items))

    def test_coragen_ecology_reference_does_not_create_semividas_identity(self):
        text = (
            "12.2 Persistencia y degradabilidad\n"
            "Producto:\n"
            "Biodegradabilidad: Resultado: No es fácilmente biodegradable.\n"
            "Observaciones: Estimación basada en datos obtenidos del\n"
            "ingrediente activo.\n"
            "Componentes:\n"
            "Clorantraniliprol:\n"
            "Biodegradabilidad: Resultado: No es fácilmente biodegradable.\n"
            "Estabilidad en el agua: Las semividas de degradación (DT50): 10 d (25 °C)\n"
            "Las semividas de degradación (DT50): 0,3 d (50 °C)\n"
        )
        items = extract_active_ingredients(document(text, "07. HS Coragen 20 SC.pdf"))
        self.assertEqual(items, [])

    def test_malathion_direct_narrative_identity_does_not_absorb_ecotoxicology_prose(self):
        text = (
            "12. Información Ecológica\n"
            "El ingrediente activo Malathion es fácilmente biodegradable. "
            "Se descompone rápidamente en el medio ambiente.\n"
            "El producto es tóxico para aves, invertebrados acuáticos, "
            "estados de vida acuática de los anfibios y altamente tóxico para las abejas.\n"
            "Peces: 96-h CL50 Trucha arco iris 0,200 mg/l\n"
        )
        items = extract_active_ingredients(document(text, "16. HS Malathion 57 EC.pdf"))
        self.assertEqual([item.name for item in items], ["Malathion"])
        self.assertFalse(any("producto es tóxico" in item.name.casefold() for item in items))

    def test_narrative_mention_of_ingredients_activos_does_not_open_identity_block(self):
        text = (
            "Generalidades:\n"
            "KADABRA es un insecticida a base de los ingredientes activos "
            "Bifentrina y Fipronil.\n"
            "Bifentrina es un piretroide de cuarta generación.\n"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])

    def test_inert_and_composition_rows_are_not_promoted_to_active_ingredients(self):
        page = PdfPage(
            page=1,
            text=(
                "INGREDIENTE ACTIVO\nBeauveria bassiana\n"
                "INGREDIENTES INERTES\nSustrato alimenticio\n"
                "COMPOSICIÓN\nGARANTIZADA\n"
                "1x 10^9 Unidades formadoras de colonia viables por gramo"
            ),
            blocks=[
                PdfTextBlock(
                    64.2,
                    388.2,
                    338.7,
                    449.6,
                    "INGREDIENTE ACTIVO\n"
                    "Beauveria bassiana\n"
                    "INGREDIENTES INERTES\n"
                    "Sustrato alimenticio\n"
                    "COMPOSICIÓN\n"
                    "GARANTIZADA\n",
                ),
                PdfTextBlock(
                    64.2,
                    418.8,
                    497.8,
                    526.9,
                    "1x 10^9 Unidades formadoras de colonia viables por gramo\n"
                    "PUREZA\n>95%\nFORMULACIÓN\nPolvo mojable W.P\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="FT Agroin-B.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual([item.name for item in items], ["Beauveria bassiana"])

    def test_enumerated_two_column_active_table_pairs_names_cas_and_concentration(self):
        page = PdfPage(
            page=2,
            text=(
                "SECCIÓN 3: Composición garantizada e identificación del producto\n"
                "Ingrediente Activo\n"
                "a. Gentamicin sulphate\n"
                "b. Oxytetracycline hydrochloride\n"
                "No CAS Ingrediente Activo\n"
                "a. 1405-41-0\n"
                "b. 2058-46-0\n"
                "Concentración\n"
                "a. 100 g/Kg\n"
                "b. 300 g/Kg"
            ),
            blocks=[
                PdfTextBlock(294.5, 172.5, 381.7, 183.5, "a. Gentamicin sulphate\n"),
                PdfTextBlock(77.4, 181.9, 151.4, 189.9, "Ingrediente Activo\n"),
                PdfTextBlock(294.5, 185.2, 418.3, 196.3, "b. Oxytetracycline hydrochloride\n"),
                PdfTextBlock(294.5, 363.9, 342.0, 375.0, "a. 1405-41-0\n"),
                PdfTextBlock(77.4, 373.3, 182.9, 381.3, "No CAS Ingrediente Activo\n"),
                PdfTextBlock(294.5, 376.7, 346.5, 387.7, "b. 2058-46-0\n"),
                PdfTextBlock(294.5, 415.0, 337.6, 426.0, "a. 100 g/Kg\n"),
                PdfTextBlock(77.4, 424.3, 135.9, 432.4, "Concentración\n"),
                PdfTextBlock(294.5, 427.7, 339.7, 438.7, "b. 300 g/Kg\n"),
            ],
        )
        doc = PdfDocument(
            file_name="FT Cumbre WP.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page.text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.cas, item.concentration) for item in items],
            [
                ("Gentamicin sulphate", "1405-41-0", "100 g/Kg"),
                ("Oxytetracycline hydrochloride", "2058-46-0", "300 g/Kg"),
            ],
        )

    def test_additives_are_not_promoted_to_active_ingredients(self):
        text = (
            "Ingredientes activos:\n"
            "Paraquat 200 g/L\n"
            "Ingredientes aditivos:\n"
            "Surfactante 20 g/L"
        )
        items = extract_active_ingredients(document(text))
        self.assertEqual([item.name for item in items], ["Paraquat"])

    def test_marker_without_ingredient_does_not_create_identity(self):
        text = (
            "Ingredientes activos:\n"
            "Ingredientes aditivos:\n"
            "c.s.p. 1 L"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])


    def test_geox_reordered_single_block_recovers_active_concentration(self):
        block_text = (
            "Ingrediente activo:\n"
            "Glifosato\n"
            "Ingredientes aditivos\n"
            "480 g/L\n"
            "c.s.p. 1 Litro\n"
        )
        page = PdfPage(
            page=1,
            text=block_text,
            blocks=[PdfTextBlock(249, 435, 577, 469, block_text)],
        )
        doc = PdfDocument(
            file_name="09. FT Geox.pdf",
            pages=[page],
            page_count=1,
            character_count=len(block_text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Glifosato", "480 g/L")],
        )

    def test_mayoral_compact_plus_field_splits_two_actives_and_pairs_concentrations(self):
        block_text = (
            "TITULAR PROFICOL ANDINA B.V. Sucursal Colombia\n"
            "Marca registrada:\n"
            "Mayoral 350 SL.\n"
            "Tipo de producto:\n"
            "Herbicida Agrícola.\n"
            "Formulación:\n"
            "Concentrado Soluble – SL.\n"
            "Ingrediente activo: IMAZAPIC+IMAZAPYR.\n"
            "Concentración:\n"
            "262.5 + 87.5 g/L.\n"
            "Categoría Toxicológica:\n"
            "III – Ligeramente peligroso.\n"
            "Modo de acción.\n"
            "El imazapic y el imazapyr del Mayoral 350 SL se absorben fácilmente.\n"
        )
        page = PdfPage(
            page=1,
            text=block_text,
            blocks=[PdfTextBlock(85, 153, 529, 737, block_text)],
        )
        doc = PdfDocument(
            file_name="15. FT Mayoral.pdf",
            pages=[page],
            page_count=1,
            character_count=len(block_text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration, item.cas) for item in items],
            [
                ("IMAZAPIC", "262.5 g/L", ""),
                ("IMAZAPYR", "87.5 g/L", ""),
            ],
        )

    def test_proclaim_fit_narrative_plural_marker_is_not_promoted_to_identity(self):
        narrative = (
            "1. CARACTERÍSTICAS / BENEFICIOS\n"
            "Proclaim Fit es muy potente contra lepidópteros en general.\n"
            "Proclaim Fit, presenta una excelente resistencia contra el lavado por lluvia. Tiene dos\n"
            "ingredientes activos especialistas en lepidópteros que lo hace muy robusto contra la\n"
            "resistencia.\n"
            "Proclaim Fit es ideal para ser considerado dentro de un Manejo Integrado de Plagas.\n"
        )
        active_block = (
            "Ingredientes Activos:\n"
            "Emamectina benzoato + Lufenuron\n"
        )
        page_text = (
            narrative
            + "2. GENERALIDADES\n"
            + active_block
            + "Nombre Químico: (IUPAC)*\n"
            + "Concentración:\n"
            + "Emamectina benzoato 50 g/kg\n"
            + "Lufenuron 400 g/kg\n"
        )
        page = PdfPage(
            page=1,
            text=page_text,
            blocks=[
                PdfTextBlock(96.8, 193.2, 515.2, 339.5, narrative),
                PdfTextBlock(253.1, 343.2, 359.2, 357.5, "2. GENERALIDADES\n"),
                PdfTextBlock(91.6, 360.8, 374.6, 375.0, active_block),
                PdfTextBlock(91.6, 383.0, 178.2, 408.7, "Nombre Químico:\n(IUPAC)*\n"),
                PdfTextBlock(
                    91.6,
                    669.8,
                    353.8,
                    694.9,
                    "Concentración:\nEmamectina benzoato 50 g/kg\nLufenuron 400 g/kg\n",
                ),
            ],
        )
        doc = PdfDocument(
            file_name="24. FT ProclaimFit.pdf",
            pages=[page],
            page_count=1,
            character_count=len(page_text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [item.name for item in items],
            ["Emamectina benzoato", "Lufenuron"],
        )
        self.assertFalse(
            any("especialistas en lepidopteros" in match_key(item.name) for item in items)
        )
        self.assertFalse(
            any(match_key(item.name) == "resistencia" for item in items)
        )

    def test_glifosol_same_block_structural_concentration_is_retained(self):
        block_text = (
            "Ingrediente Activo:\n"
            "Glifosato\n"
            "Concentración:\n"
            "480 g/L\n"
            "Nombre químico:\n"
            "N-(phosphonomethyl) glycine, en forma de sal isopropilamina\n"
            "Tipo de Formulación:\n"
            "Concentrado Soluble- SL\n"
        )
        page = PdfPage(
            page=1,
            text=block_text,
            blocks=[PdfTextBlock(85, 336, 530, 719, block_text)],
        )
        doc = PdfDocument(
            file_name="10. Ft Glifosol.pdf",
            pages=[page],
            page_count=1,
            character_count=len(block_text),
            pages_with_text=1,
            processable=True,
            warnings=[],
        )

        items = extract_active_ingredients(doc)

        self.assertEqual(
            [(item.name, item.concentration) for item in items],
            [("Glifosato", "480 g/L")],
        )


if __name__ == "__main__":
    unittest.main()
