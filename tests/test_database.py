import unittest
from pathlib import Path
from src.prohibited_database import ProhibitedDatabase,GROUP_RULES
from src.text_utils import match_key
MASTER=Path(__file__).resolve().parents[1]/'data'/'master_restrictions.csv'
class DatabaseTests(unittest.TestCase):
 def test_three_normative_lists_loaded(self):
  db=ProhibitedDatabase(MASTER)
  self.assertEqual(len(db.prohibited),165);self.assertEqual(len(db.obsolete),24);self.assertEqual(len(db.mitigation),168)
 def test_prohibited_groups_preserved(self):
  db=ProhibitedDatabase(MASTER); groups=[e for e in db.groups if e.source_list=='PROHIBITED']
  self.assertEqual(len(groups),8); names={e.ingredient for e in groups}
  self.assertIn('Arsénico y sus compuestos',names);self.assertIn('Sales e isómeros de glufosinato de amonio',names)
 def test_all_eight_prohibited_group_rows_have_explicit_rules(self):
  db=ProhibitedDatabase(MASTER); groups=[e for e in db.groups if e.source_list=='PROHIBITED']
  self.assertEqual({match_key(e.ingredient) for e in groups},set(GROUP_RULES))
 def test_alias_matching_metadata_is_precomputed(self):
  db=ProhibitedDatabase(MASTER)
  entry=next(e for e in db.specific if e.ingredient=='Tiametoxam')
  self.assertEqual(db.aliases(entry),('Tiametoxam',))
  self.assertEqual(db.alias_pairs(entry),(('Tiametoxam','tiametoxam'),))
