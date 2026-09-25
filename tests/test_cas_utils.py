import unittest
from src.cas_utils import extract_valid_cas,is_valid_cas,parse_manual_cas
class CasTests(unittest.TestCase):
 def test_checksum(self):self.assertTrue(is_valid_cas('153719-23-4'));self.assertFalse(is_valid_cas('167-00-5'))
 def test_variants(self):
  for x in ['153719-23-4','153719 - 23 - 4','153719-\n23-4','153719–23–4']:
   self.assertEqual(extract_valid_cas(x),['153719-23-4'])
 def test_manual_digits(self):self.assertIn('153719-23-4',parse_manual_cas('153719234')[0])
