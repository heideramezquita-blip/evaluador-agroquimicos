import unittest

from src.context_classifier import ACTIVE, UNCERTAIN, classify_context
from src.prohibited_detector import _line_context


class ParaquatContextRegressionTests(unittest.TestCase):
    def test_repeated_product_name_does_not_hide_explicit_active_ingredient(self):
        # Mirrors the extraction pattern of the VECOL Paraquat 200 SL FT:
        # the product name appears first and the PDF inserts many blank layout
        # lines between the active-ingredient heading and its value.
        text = """
FICHA TECNICA

Producto: Paraquat Vecol 200 SL. Ficha Técnica año 2021

A. USO: HERBICIDA AGRICOLA

PARAQUAT VECOL 200 SL es un herbicida no selectivo.

MODO DE ACCIÓN: Herbicida no selectivo.

Ingredientes Activos






















:








Paraquat                               200 g/L
"""
        context = _line_context(text, "Paraquat")
        self.assertEqual(classify_context(context, "Paraquat"), ACTIVE)

    def test_product_name_alone_is_not_promoted_to_active_ingredient(self):
        text = """
FICHA TECNICA
Producto: Paraquat Ejemplo
Descripción general del producto.
Recomendaciones de uso.
"""
        context = _line_context(text, "Paraquat")
        self.assertEqual(classify_context(context, "Paraquat"), UNCERTAIN)


if __name__ == "__main__":
    unittest.main()
