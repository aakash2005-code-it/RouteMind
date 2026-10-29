import heapq, math, random, time
from copy import deepcopy

INITIAL_NODES = [
 {'id':'A','x':95,'y':210,'label':'Campus Gateway'},
 {'id':'B','x':295,'y':80,'label':'Core Router 1'},
 {'id':'C','x':295,'y':330,'label':'Core Router 2'},
 {'id':'D','x':535,'y':80,'label':'Distribution 1'},
 {'id':'E','x':535,'y':330,'label':'Distribution 2'},
 {'id':'F','x':745,'y':210,'label':'Application Server'},
]
INITIAL_EDGES = [
 {'id':'AB','source':'A','target':'B','latency':14,'loss':0.2,'utilization':20,'capacity':100,'up':True},
 {'id':'AC','source':'A','target':'C','latency':24,'loss':0.1,'utilization':10,'capacity':100,'up':True},
 {'id':'BD','source':'B','target':'D','latency':12,'loss':0.3,'utilization':15,'capacity':100,'up':True},
 {'id':'BE','source':'B','target':'E','latency':20,'loss':0.8,'utilization':45,'capacity':100,'up':True},
 {'id':'CE','source':'C','target':'E','latency':20,'loss':0.1,'utilization':20,'capacity':100,'up':True},
 {'id':'CD','source':'C','target':'D','latency':38,'loss':0.4,'utilization':25,'capacity':100,'up':True},
 {'id':'DF','source':'D','target':'F','latency':14,'loss':0.3,'utilization':20,'capacity':100,'up':True},
 {'id':'EF','source':'E','target':'F','latency':19,'loss':0.2,'utilization':15,'capacity':100,'up':True},
]
PROFILES = {
 'balanced': {'latency':1.0, 'loss':10.0, 'congestion':0.20},
 'realtime': {'latency':1.5, 'loss':25.0, 'congestion':0.30},
 'bulk': {'latency':0.45, 'loss':8.0, 'congestion':1.0},
}

def initial_state():
 return {'nodes':deepcopy(INITIAL_NODES),'edges':deepcopy(INITIAL_EDGES),'events':[], 'version':0}

def edge_cost(e, algorithm='adaptive', profile='balanced'):
 if algorithm=='hop': return 1
 if algorithm=='latency': return e['latency']
 p=PROFILES.get(profile,PROFILES['balanced'])
 # Penalty increases nonlinearly toward saturation; loss given as percent.
 congestion = (e['utilization']/100)**2 * 100
 return round(p['latency']*e['latency'] + p['loss']*e['loss'] + p['congestion']*congestion,4)

def shortest_path(state, src='A', dst='F', algorithm='adaptive', profile='balanced'):
 nodes={n['id'] for n in state['nodes']}
 if src not in nodes or dst not in nodes: raise ValueError('Unknown source or destination')
 adj={n:[] for n in nodes}
 for e in state['edges']:
  if e['up']:
   w=edge_cost(e,algorithm,profile)
   adj[e['source']].append((e['target'],w,e))
   adj[e['target']].append((e['source'],w,e))
 for neighbors in adj.values(): neighbors.sort(key=lambda x:x[0])
 best={src:0}; prev={}; q=[(0,src)]; visited=0
 while q:
  cost,u=heapq.heappop(q)
  if cost>best[u]+1e-9: continue
  visited+=1
  if u==dst: break
  for v,w,e in adj[u]:
   new=cost+w
   if new<best.get(v,float('inf'))-1e-9:
    best[v]=new; prev[v]=(u,e['id']); heapq.heappush(q,(new,v))
 if dst not in best: return {'reachable':False,'path':[],'edge_ids':[],'cost':None,'latency_ms':None,'loss_pct':None,'bottleneck_mbps':None,'visited':visited,'algorithm':algorithm,'profile':profile}
 path=[dst]; edge_ids=[]
 while path[-1]!=src:
  u,eid=prev[path[-1]]; edge_ids.append(eid); path.append(u)
 path.reverse();edge_ids.reverse()
 selected=[next(e for e in state['edges'] if e['id']==i) for i in edge_ids]
 lat=sum(e['latency'] for e in selected)
 success=math.prod(1-e['loss']/100 for e in selected)
 bottleneck=min((e['capacity']*(1-e['utilization']/100) for e in selected),default=0)
 return {'reachable':True,'path':path,'edge_ids':edge_ids,'cost':round(best[dst],3),'latency_ms':round(lat,2),'loss_pct':round((1-success)*100,3),'bottleneck_mbps':round(bottleneck,2),'visited':visited,'algorithm':algorithm,'profile':profile}

def compare(state,source='A',target='F',profile='balanced'):
 return {a:shortest_path(state,source,target,a,profile) for a in ('hop','latency','adaptive')}

def simulate(state,source='A',target='F',algorithm='adaptive',profile='balanced',packets=150,seed=42):
 """Reproducible *modeled* independent packet losses on fixed path. Not real IP traffic."""
 route=shortest_path(state,source,target,algorithm,profile)
 if not route['reachable']: return {'route':route,'packets_sent':packets,'packets_delivered':0,'packets_dropped':packets,'delivery_pct':0,'mean_delay_ms':None,'mode':'modeled'}
 rng=random.Random(seed); edges=[next(e for e in state['edges'] if e['id']==i) for i in route['edge_ids']]
 delivered=0; delays=[]
 for _ in range(packets):
  delay=0; alive=True
  for e in edges:
   if rng.random()<e['loss']/100: alive=False; break
   delay += e['latency'] + rng.uniform(0, e['utilization']/100*e['latency']*.5)
  if alive: delivered+=1; delays.append(delay)
 return {'route':route,'packets_sent':packets,'packets_delivered':delivered,'packets_dropped':packets-delivered,'delivery_pct':round(delivered/packets*100,2),'mean_delay_ms':round(sum(delays)/len(delays),2) if delays else None,'mode':'modeled','seed':seed}
