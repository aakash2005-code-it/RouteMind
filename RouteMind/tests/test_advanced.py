import unittest
from engine import initial_state
from advanced import explain_route, benchmark, failure_sweep

class AdvancedTests(unittest.TestCase):
 def setUp(self): self.state=initial_state()
 def test_explanations_add_up(self):
  x=explain_route(self.state,'A','F','adaptive','balanced')
  self.assertTrue(x['route']['reachable'])
  self.assertAlmostEqual(sum(e['edge_cost'] for e in x['breakdown']),x['route']['cost'],places=2)
 def test_benchmark_reproducible(self):
  a=benchmark(self.state,packets=30,runs=3,seed=12)
  b=benchmark(self.state,packets=30,runs=3,seed=12)
  self.assertEqual(a,b)
  self.assertEqual(set(a['algorithms']),{'hop','latency','adaptive'})
 def test_sweep_no_state_mutation(self):
  initial=[e.copy() for e in self.state['edges']]
  r=failure_sweep(self.state)
  self.assertEqual(len(r['cases']),len(initial))
  self.assertEqual(self.state['edges'],initial)
 def test_disconnected_route_explanation(self):
  for e in self.state['edges']:e['up']=False
  x=explain_route(self.state,'A','F')
  self.assertFalse(x['route']['reachable'])
  self.assertEqual(x['breakdown'],[])
