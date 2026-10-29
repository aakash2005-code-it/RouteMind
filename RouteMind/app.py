from flask import Flask, jsonify, render_template, request
from threading import RLock
from copy import deepcopy
from datetime import datetime, timezone
from engine import initial_state, shortest_path, compare, simulate, PROFILES
from advanced import explain_route, benchmark, failure_sweep
from flask import Response
import csv, io, json

app=Flask(__name__)
state=initial_state()
lock=RLock()

def event(kind,message):
 state['events'].insert(0,{'at':datetime.now(timezone.utc).isoformat(timespec='seconds'),'kind':kind,'message':message})
 state['events']=state['events'][:60]
 state['version']+=1

def payload():
 return {'nodes':deepcopy(state['nodes']),'edges':deepcopy(state['edges']),'events':deepcopy(state['events']),'version':state['version'],'profiles':PROFILES}

@app.get('/')
def index(): return render_template('index.html')

@app.get('/api/state')
def get_state():
 with lock: return jsonify(payload())

@app.post('/api/reset')
def reset():
 global state
 with lock:
  state=initial_state();event('reset','Topology restored to its original state')
  return jsonify(payload())

@app.post('/api/link/<link_id>')
def update_link(link_id):
 data=request.get_json(silent=True) or {}
 with lock:
  edge=next((e for e in state['edges'] if e['id']==link_id.upper()),None)
  if not edge:return jsonify(error='Unknown link'),404
  valid={'latency':(1,500),'loss':(0,100),'utilization':(0,100),'capacity':(1,10000)}
  for key,value in data.items():
   if key=='up':
    if not isinstance(value,bool):return jsonify(error='up must be boolean'),400
   elif key in valid:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not valid[key][0]<=value<=valid[key][1]: return jsonify(error=f'Invalid {key}'),400
   else:return jsonify(error=f'Unexpected field: {key}'),400
  before=edge.copy();edge.update(data)
  changes=', '.join(f'{k}: {before[k]} → {v}' for k,v in data.items())
  if changes:event('link',f'Link {link_id.upper()} updated: {changes}')
  return jsonify(payload())

@app.post('/api/route')
def route():
 d=request.get_json(silent=True) or {}
 src=d.get('source','A');dst=d.get('target','F');alg=d.get('algorithm','adaptive');profile=d.get('profile','balanced')
 if alg not in ('hop','latency','adaptive') or profile not in PROFILES:return jsonify(error='Invalid algorithm or profile'),400
 with lock:
  try:return jsonify({'route':shortest_path(state,src,dst,alg,profile),'comparison':compare(state,src,dst,profile),'version':state['version']})
  except ValueError as e:return jsonify(error=str(e)),400

@app.post('/api/simulate')
def run_simulation():
 d=request.get_json(silent=True) or {}
 packets=d.get('packets',150);seed=d.get('seed',42)
 if type(packets)!=int or not 1<=packets<=5000 or type(seed)!=int:return jsonify(error='Invalid packets or seed'),400
 alg=d.get('algorithm','adaptive');profile=d.get('profile','balanced')
 if alg not in ('hop','latency','adaptive') or profile not in PROFILES:return jsonify(error='Invalid algorithm or profile'),400
 with lock:
  try:
   result=simulate(state,d.get('source','A'),d.get('target','F'),alg,profile,packets,seed)
   event('experiment',f'{alg} experiment: {result["packets_delivered"]}/{packets} packets modeled as delivered')
   return jsonify(result)
  except ValueError as e:return jsonify(error=str(e)),400

if __name__=='__main__':
 app.run(host='127.0.0.1',port=5055,debug=False)


def request_route_config(data):
 src=data.get('source','A'); dst=data.get('target','F'); alg=data.get('algorithm','adaptive'); profile=data.get('profile','balanced')
 if alg not in ('hop','latency','adaptive') or profile not in PROFILES: raise ValueError('Invalid algorithm or profile')
 return src,dst,alg,profile

@app.post('/api/explain')
def explain():
 try:
  with lock:
   data=request.get_json(silent=True) or {}; return jsonify(explain_route(state,*request_route_config(data)))
 except ValueError as exc: return jsonify(error=str(exc)),400

@app.post('/api/benchmark')
def run_benchmark():
 try:
  d=request.get_json(silent=True) or {}
  src,dst,alg,profile=request_route_config(d)
  packets=d.get('packets',300);runs=d.get('runs',20);seed=d.get('seed',42)
  if type(packets)!=int or not 1<=packets<=2000 or type(runs)!=int or not 1<=runs<=100 or type(seed)!=int: raise ValueError('Invalid benchmark parameters')
  with lock:
   result=benchmark(state,src,dst,profile,packets,runs,seed)
   event('benchmark',f'Compared three algorithms across {runs} × {packets} modeled packets')
   return jsonify(result)
 except ValueError as exc: return jsonify(error=str(exc)),400

@app.post('/api/resilience')
def resilience():
 try:
  d=request.get_json(silent=True) or {}
  with lock: return jsonify(failure_sweep(state,*request_route_config(d)))
 except ValueError as exc: return jsonify(error=str(exc)),400

@app.post('/api/topology/node')
def create_node():
 d=request.get_json(silent=True) or {}
 name=d.get('id'); label=d.get('label','Router')
 if not isinstance(name,str) or not name.isalnum() or not 1<=len(name)<=8: return jsonify(error='Node ID must be 1–8 alphanumeric characters'),400
 if not isinstance(label,str) or not 1<=len(label)<=40: return jsonify(error='Invalid node label'),400
 try:
  x=float(d.get('x',400)); y=float(d.get('y',200))
 except (TypeError,ValueError): return jsonify(error='Invalid coordinates'),400
 if not 0<=x<=840 or not 0<=y<=410: return jsonify(error='Coordinates outside canvas'),400
 with lock:
  if len(state['nodes'])>=20:return jsonify(error='Maximum 20 nodes'),400
  if any(n['id']==name.upper() for n in state['nodes']):return jsonify(error='Node already exists'),409
  state['nodes'].append({'id':name.upper(),'label':label,'x':x,'y':y});event('topology',f'Added node {name.upper()}')
  return jsonify(payload())

@app.post('/api/topology/edge')
def create_edge():
 d=request.get_json(silent=True) or {}
 src=d.get('source');dst=d.get('target')
 if not isinstance(src,str) or not isinstance(dst,str):return jsonify(error='Invalid endpoints'),400
 src=src.upper();dst=dst.upper()
 with lock:
  nodes={n['id'] for n in state['nodes']}
  if src==dst or src not in nodes or dst not in nodes:return jsonify(error='Select two distinct existing nodes'),400
  if any({e['source'],e['target']}=={src,dst} for e in state['edges']):return jsonify(error='Link already exists'),409
  if len(state['edges'])>=50:return jsonify(error='Maximum 50 links'),400
  edge={'id':'-'.join(sorted((src,dst))),'source':src,'target':dst,'latency':20,'loss':0.2,'utilization':15,'capacity':100,'up':True}
  state['edges'].append(edge);event('topology',f'Added link {src} ↔ {dst}')
  return jsonify(payload())

@app.delete('/api/topology/edge/<link_id>')
def remove_edge(link_id):
 with lock:
  edge=next((e for e in state['edges'] if e['id']==link_id),None)
  if not edge:return jsonify(error='Unknown link'),404
  state['edges'].remove(edge);event('topology',f'Removed link {link_id}')
  return jsonify(payload())

@app.delete('/api/topology/node/<node_id>')
def remove_node(node_id):
 with lock:
  node=next((n for n in state['nodes'] if n['id']==node_id.upper()),None)
  if not node:return jsonify(error='Unknown node'),404
  state['nodes'].remove(node)
  state['edges'][:]=[e for e in state['edges'] if node['id'] not in (e['source'],e['target'])]
  event('topology',f'Removed node {node_id.upper()} and attached links')
  return jsonify(payload())

@app.get('/api/export/topology')
def export_topology():
 with lock: data={'nodes':deepcopy(state['nodes']),'edges':deepcopy(state['edges']),'version':state['version'],'mode':'modeled'}
 return Response(json.dumps(data,indent=2),mimetype='application/json',headers={'Content-Disposition':'attachment; filename=routemind_topology.json'})

@app.get('/api/export/events')
def export_events():
 with lock: events=deepcopy(state['events'])
 out=io.StringIO();w=csv.DictWriter(out,fieldnames=['at','kind','message']);w.writeheader();w.writerows(events)
 return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=routemind_events.csv'})
