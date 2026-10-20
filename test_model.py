import unittest
from scripts.update import extract_box, calculate_team_stats, project, excel_v1_projection, grade_paper
class ModelTests(unittest.TestCase):
 def test_boxscore_possessions(self):
  rows=[{'label':'FG','displayValue':'40-88'},{'label':'FT','displayValue':'16-22'},{'label':'OR','displayValue':'10'},{'label':'TO','displayValue':'12'}]
  self.assertAlmostEqual(extract_box(rows)['poss'],99.68)
 def test_missing_boxscore_returns_none(self):
  self.assertIsNone(extract_box([{'label':'FG','displayValue':'40-88'}]))
 def test_models_locked_without_sample(self):
  stats={'A':{'games':0,'ready':False},'B':{'games':15,'ready':True}}
  self.assertIsNone(project({'home':'A','away':'B'},stats,110,{'line':220}))
 def test_preview_not_counted_as_paper_pick(self):
  stats={'A':{'games':1,'ready':False,'pace':101,'ortg':115,'drtg':113},'B':{'games':1,'ready':False,'pace':100,'ortg':114,'drtg':112}}
  r=project({'home':'A','away':'B'},stats,110,{'line':210})
  self.assertTrue(r['preview']); self.assertIsNone(r['watch']); self.assertEqual(r['preview_direction'],'OVER')
 def test_projection_watch_when_valid(self):
  stats={'A':{'games':12,'ready':True,'pace':101,'ortg':115,'drtg':113},'B':{'games':12,'ready':True,'pace':100,'ortg':114,'drtg':112}}
  r=project({'home':'A','away':'B'},stats,110,{'line':210})
  self.assertEqual(r['watch'],'OVER'); self.assertGreater(r['total'],210); self.assertFalse(r['preview'])
 def test_original_excel_formula_reproduces_workbook(self):
  # NBA Totals v1.xlsx / Daily row 2: Milwaukee @ Orlando, book 220.5.
  stats={'Milwaukee Bucks':{'games':15,'pace':97.7,'ortg':113.1,'drtg':118.4},
         'Orlando Magic':{'games':15,'pace':99.5,'ortg':114.9,'drtg':113.9}}
  g={'away':'Milwaukee Bucks','home':'Orlando Magic'}
  r=excel_v1_projection(g,stats,{'line':220.5})
  self.assertAlmostEqual(r['total'],226.9,places=1)
  self.assertAlmostEqual(r['away_points'],111.91,places=2)
  self.assertAlmostEqual(r['home_points'],115.02,places=2)
  self.assertEqual(r['watch'],'OVER')
 def test_v1_and_v2_independent_previews(self):
  stats={'A':{'games':1,'ready':False,'pace':101,'ortg':115,'drtg':113},'B':{'games':1,'ready':False,'pace':100,'ortg':114,'drtg':112}}
  result=project({'home':'A','away':'B'},stats,110,{'line':210})
  self.assertIsNotNone(result['original']);self.assertTrue(result['original']['preview']);self.assertIsNone(result['original']['watch'])
  self.assertIsNone(result['watch']);self.assertNotEqual(result['original']['total'],result['total'])
 def test_push_grade(self):
  picks={'g':{'event_id':'g','line':220,'side':'OVER','price':-110,'result':'pending'}}
  archive={'g':{'home_score':110,'away_score':110}}
  self.assertEqual(grade_paper(picks,archive)['g']['result'],'push')
if __name__=='__main__':unittest.main()
