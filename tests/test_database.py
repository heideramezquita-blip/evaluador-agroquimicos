import unittest
from pathlib import Path
from src.prohibited_database import ProhibitedDatabase,GROUP_RULES
from src.text_utils import match_key
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'
class DatabaseTests(unittest.TestCase):
 def test_only_prohibited_loaded(self):
  db=ProhibitedDatabase(MASTER);self.assertEqual(len(db.groups),8);self.assertGreater(len(db.specific),150);self.assertTrue(all(e.cas for e in db.specific));self.assertTrue(all(not e.cas for e in db.groups))
 def test_group_names(self):
  db=ProhibitedDatabase(MASTER); names={e.ingredient for e in db.groups}
  self.assertIn('Arsénico y sus compuestos',names);self.assertIn('Sales e isómeros de glufosinato de amonio',names)
 def test_all_eight_group_rows_have_explicit_rules(self):
  db=ProhibitedDatabase(MASTER);self.assertEqual({match_key(e.ingredient) for e in db.groups},set(GROUP_RULES))
