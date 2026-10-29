import unittest
from engine import initial_state, shortest_path, simulate, compare
class RoutingTests(unittest.TestCase):
 def setUp(self): self.s=initial_state()
 def test_default_routes(self):
  results=compare(self.s)
  self.assertTrue(all(r['reachable'] for r in results.values()))
  self.assertEqual(results['latency']['path'],['A','B','D','F'])
 def test_failure_recovery(self):
  before=shortest_path(self.s,algorithm='latency')
  next(e for e in self.s['edges'] if e['id']=='BD')['up']=False
  after=shortest_path(self.s,algorithm='latency')
  self.assertNotEqual(before['path'],after['path'])
  self.assertNotIn('BD',after['edge_ids'])
 def test_disconnection(self):
  for e in self.s['edges']:
   if e['source']=='F' or e['target']=='F':e['up']=False
  self.assertFalse(shortest_path(self.s)['reachable'])
 def test_congestion_change(self):
  before=shortest_path(self.s,algorithm='adaptive')
  next(e for e in self.s['edges'] if e['id']=='AB')['utilization']=99
  after=shortest_path(self.s,algorithm='adaptive')
  self.assertNotEqual(before['path'],after['path'])
 def test_reproducible_packets(self):
  a=simulate(self.s,packets=300,seed=5)
  b=simulate(self.s,packets=300,seed=5)
  self.assertEqual(a,b)
 def test_no_mutation(self):
  before=initial_state();shortest_path(self.s)
  self.assertEqual(before,self.s)
if __name__=='__main__':unittest.main()
