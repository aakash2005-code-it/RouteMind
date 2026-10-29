"""Advanced reproducible RouteMind experiments. Pure model, never forwards real IP packets."""
import random, statistics, math
from copy import deepcopy
from engine import shortest_path, simulate, edge_cost

ALGORITHMS = ('hop', 'latency', 'adaptive')

def explain_route(state, source, target, algorithm='adaptive', profile='balanced'):
    route = shortest_path(state, source, target, algorithm, profile)
    if not route['reachable']:
        return {'route': route, 'breakdown': [], 'explanation': 'No reachable path. Restore a link or modify the topology.'}
    lookup = {e['id']: e for e in state['edges']}
    breakdown=[]
    for eid in route['edge_ids']:
        e=lookup[eid]
        breakdown.append({'edge': eid, 'latency_ms':e['latency'], 'loss_pct':e['loss'],
                          'utilization_pct':e['utilization'], 'available_mbps':round(e['capacity']*(1-e['utilization']/100),3),
                          'edge_cost':edge_cost(e,algorithm,profile)})
    alternatives=[]
    for excluded in route['edge_ids']:
        modified=deepcopy(state)
        next(e for e in modified['edges'] if e['id']==excluded)['up']=False
        other=shortest_path(modified,source,target,algorithm,profile)
        if other['reachable'] and other['path'] != route['path']:
            alternatives.append({'excluded_edge': excluded,'path':other['path'],'cost':other['cost'],'latency_ms':other['latency_ms']})
    alternatives.sort(key=lambda a:(a['cost'],a['excluded_edge']))
    return {'route':route,'breakdown':breakdown,'alternatives':alternatives[:3],
            'explanation':f"{algorithm.title()} selected {' → '.join(route['path'])} using {profile} policy. Its {len(route['edge_ids'])} link costs total {route['cost']}."}

def benchmark(state,source='A',target='F',profile='balanced', packets=300,runs=20,seed=42):
    """Paired seeded Monte Carlo trials for modeled packet outcomes."""
    results={}
    for algo in ALGORITHMS:
        trials=[simulate(state,source,target,algo,profile,packets,seed+i) for i in range(runs)]
        deliveries=[x['delivery_pct'] for x in trials]
        delays=[x['mean_delay_ms'] for x in trials if x['mean_delay_ms'] is not None]
        route=trials[0]['route']
        results[algo]={'route':route, 'mean_delivery_pct':round(statistics.mean(deliveries),3),
                       'delivery_stddev_pct':round(statistics.stdev(deliveries),3) if runs>1 else 0,
                       'mean_delay_ms':round(statistics.mean(delays),3) if delays else None,
                       'runs':runs,'total_packets':packets*runs,
                       'delivered_packets':sum(t['packets_delivered'] for t in trials),
                       'trials':[{'run':i+1,'delivery_pct':x['delivery_pct'],'mean_delay_ms':x['mean_delay_ms']} for i,x in enumerate(trials)]}
    return {'mode':'modeled','runs':runs,'packets_per_run':packets,'seed':seed,'profile':profile,'source':source,'target':target,'algorithms':results,
            'caveat':'Independent per-link packet losses and modeled delay; not measured live traffic. No algorithm universally dominates.'}

def failure_sweep(state,source='A',target='F',algorithm='adaptive',profile='balanced'):
    baseline=shortest_path(state,source,target,algorithm,profile)
    cases=[]
    for edge in state['edges']:
        if not edge['up']: continue
        temp=deepcopy(state)
        next(e for e in temp['edges'] if e['id']==edge['id'])['up']=False
        r=shortest_path(temp,source,target,algorithm,profile)
        cases.append({'failed_link':edge['id'],'reachable':r['reachable'],'path':r['path'],
                      'latency_ms':r['latency_ms'],'cost':r['cost'],'changed_path':r['path']!=baseline['path']})
    return {'baseline':baseline,'cases':cases,'recoverable_failures':sum(x['reachable'] for x in cases),'tested_failures':len(cases),
            'mode':'modeled topology resilience'}
