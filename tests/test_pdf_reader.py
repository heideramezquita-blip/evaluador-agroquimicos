import unittest,fitz
from src.pdf_reader import read_pdf
class PdfTests(unittest.TestCase):
 def test_blank_is_unprocessable(self):
  d=fitz.open();d.new_page();b=d.tobytes();d.close();r=read_pdf(b,'scan.pdf');self.assertFalse(r.processable)
