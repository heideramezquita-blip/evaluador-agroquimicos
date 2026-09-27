import unittest

from src.active_ingredient_extractor import extract_active_ingredients
from src.models import PdfDocument, PdfPage, PdfTextBlock


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
        self.assertEqual(items[0].name.casefold(), "glifosato")
        self.assertEqual(items[0].concentration, "443 g/L")
        self.assertEqual(items[0].cas, "")
        self.assertEqual(items[0].page, 1)

    def test_narrative_mention_of_ingredients_activos_does_not_open_identity_block(self):
        text = (
            "Generalidades:\n"
            "KADABRA es un insecticida a base de los ingredientes activos "
            "Bifentrina y Fipronil.\n"
            "Bifentrina es un piretroide de cuarta generación.\n"
        )
        self.assertEqual(extract_active_ingredients(document(text)), [])

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


if __name__ == "__main__":
    unittest.main()
