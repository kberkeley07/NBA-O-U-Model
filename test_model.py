import unittest
from scripts.update import extract_box, calculate_team_stats, project, grade_paper
class ModelTests(unittest.TestCase):
 def test_boxscore_possessions(self):
  rows=[{'label':'FG','displayValue':'40-88'},{'label':'FT','displayValue':'16-22'},{'label':'OR','displayValue':'10'},{'label':'TO','displayValue':'12'}]
  self.assertAlmostEqual(extract_box(rows)['poss'],99.68)
 def test_missing_boxscore_returns_none(self):
  self.assertIsNone(extract_box([{'label':'FG','displayValue':'40-88'}]))
 def test_models_locked_without_sample(self):
  stats={'A':{'games':9,'ready':False},'B':{'games':15,'ready':True}}
  self.assertIsNone(project({'home':'A','away':'B'},stats,110,{'line':220}))
 def test_projection_watch_when_valid(self):
  stats={'A':{'games':12,'ready':True,'pace':101,'ortg':115,'drtg':113},'B':{'games':12,'ready':True,'pace':100,'ortg':114,'drtg':112}}
  r=project({'home':'A','away':'B'},stats,110,{'line':210})
  self.assertEqual(r['watch'],'OVER'); self.assertGreater(r['total'],210)
 def test_push_grade(self):
  picks={'g':{'event_id':'g','line':220,'side':'OVER','price':-110,'result':'pending'}}
  archive={'g':{'home_score':110,'away_score':110}}
  self.assertEqual(grade_paper(picks,archive)['g']['result'],'push')
if __name__=='__main__':unittest.main()
