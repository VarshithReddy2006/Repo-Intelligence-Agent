"""PH2-001 smoke tests — graph_serializer.py. Run and delete."""
import sys, os
sys.path.insert(0, '.')

from services.graph_serializer import GraphSerializer
from services.graph_service import GraphService
from services.architecture_service import ArchitectureService

gs = GraphService()
arch = ArchitectureService()
ser = GraphSerializer(graph_service=gs, architecture_service=arch)

REPO = 'fastapi/fastapi'  # 1125 nodes, 1440 edges — a real populated graph

# ── Full graph ─────────────────────────────────────────────────────────────
data = ser.get_full_graph(REPO)
assert len(data['nodes']) > 0, 'full graph returned no nodes'
assert len(data['edges']) > 0, 'full graph returned no edges'
n = data['nodes'][0]
# Every node must have these keys
for key in ('id','label','category','degree','centrality','language','highlighted','is_focus'):
    assert key in n, f'node missing key: {key}'
e = data['edges'][0]
for key in ('source','target','relationship'):
    assert key in e, f'edge missing key: {key}'
print(f'PASS full_graph: {len(data["nodes"])} nodes, {len(data["edges"])} edges')

# ── Full graph with search filter ─────────────────────────────────────────
data_q = ser.get_full_graph(REPO, search_query='routing')
assert len(data_q['nodes']) <= len(data['nodes']), 'filtered result larger than full'
print(f'PASS full_graph+search: {len(data_q["nodes"])} nodes matched routing')

# ── Neighbours ───────────────────────────────────────────────────────────
# Pick a node that definitely has edges
focus = 'fastapi/routing.py'
neigh = ser.get_neighbors(REPO, focus)
assert not neigh.get('error'), f'neighbors error: {neigh.get("error")}'
assert len(neigh['nodes']) > 0, 'neighbors returned no nodes'
focus_nodes = [n for n in neigh['nodes'] if n['is_focus']]
assert len(focus_nodes) == 1, 'expected exactly 1 focus node'
assert focus_nodes[0]['id'] == focus
assert focus_nodes[0]['category'] == 'focus'
print(f'PASS neighbors: {len(neigh["nodes"])} nodes around {focus}')

# ── Bad node returns error ────────────────────────────────────────────────
bad = ser.get_neighbors(REPO, 'does/not/exist.py')
assert bad.get('error'), 'expected error for missing node'
assert bad['nodes'] == []
print(f'PASS neighbors bad node: error returned correctly')

# ── Trace forward ─────────────────────────────────────────────────────────
trace_fwd = ser.get_trace(REPO, focus, direction='forward', max_depth=3)
assert not trace_fwd.get('error'), f'trace forward error: {trace_fwd.get("error")}'
assert len(trace_fwd['nodes']) > 0
focus_in_trace = [n for n in trace_fwd['nodes'] if n['id'] == focus]
assert len(focus_in_trace) == 1, 'focus node must be in trace result'
print(f'PASS trace_forward: {len(trace_fwd["nodes"])} nodes, depth=3')

# ── Trace backward ────────────────────────────────────────────────────────
trace_bwd = ser.get_trace(REPO, focus, direction='backward', max_depth=3)
assert not trace_bwd.get('error')
print(f'PASS trace_backward: {len(trace_bwd["nodes"])} nodes')

# ── Trace both ────────────────────────────────────────────────────────────
trace_both = ser.get_trace(REPO, focus, direction='both', max_depth=4)
assert not trace_both.get('error')
assert len(trace_both['nodes']) >= len(trace_fwd['nodes']), \
    'both should have >= nodes than forward alone'
print(f'PASS trace_both: {len(trace_both["nodes"])} nodes')

# ── Search ────────────────────────────────────────────────────────────────
search = ser.get_search(REPO, 'routing')
assert not search.get('error')
assert search.get('matched_count', 0) > 0, 'expected matches for routing'
assert search.get('query') == 'routing'
highlighted = [n for n in search['nodes'] if n['highlighted']]
assert len(highlighted) == search['matched_count'], \
    'highlighted count must equal matched_count'
print(f'PASS search: {search["matched_count"]} matched, {len(search["nodes"])} total nodes')

# ── Empty search falls back to full ──────────────────────────────────────
search_empty = ser.get_search(REPO, '   ')
assert len(search_empty['nodes']) > 0, 'empty search should return full graph'
print(f'PASS search empty query falls back to full graph')

# ── Missing repo returns error gracefully ─────────────────────────────────
missing = ser.get_neighbors('no/repo', 'any/file.py')
assert missing.get('error'), 'expected error for missing repo'
print(f'PASS missing repo: error returned gracefully')

# ── Node schema validation — all 7 required fields on every node ───────────
REQUIRED_NODE_FIELDS = {'id','label','category','degree','centrality','language','highlighted','is_focus'}
for data_set, name in [
    (neigh, 'neighbors'),
    (trace_fwd, 'trace_forward'),
    (search, 'search'),
]:
    for node in data_set['nodes']:
        missing_keys = REQUIRED_NODE_FIELDS - set(node.keys())
        assert not missing_keys, f'{name} node {node.get("id")} missing: {missing_keys}'
print('PASS all nodes have required schema fields across neighbors/trace/search')

print()
print('=' * 58)
print('All PH2-001 graph serializer smoke tests PASSED.')
print('=' * 58)
