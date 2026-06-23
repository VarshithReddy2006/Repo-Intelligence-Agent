/**
 * CallGraphAnalyzer — Function Call Graph tab component.
 *
 * Integrates into the existing AnalysisDashboard tab panel.
 * Reuses React Flow (already a dependency), existing UI components,
 * and the established graph data schema (nodes/edges with id, label,
 * category, etc.) so the existing GraphCanvas renders it unchanged
 * when hooked in through InteractiveDependencyGraph's graphType toggle.
 *
 * This component provides its own self-contained view because the call
 * graph has richer node metadata (fan_in, fan_out, file_path, qualified)
 * than the file graph and warrants dedicated panels.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  Position,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { PanControls } from './graph/PanControls';

import { apiUrl, extractErrorMessage } from '../../lib/api';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { MetricCard } from '../ui/MetricCard';
import { EmptyState } from '../ui/EmptyState';
import { SkeletonCard, SkeletonGroup, Skeleton } from '../ui/Skeleton';
import {
  Workflow, Zap, AlertTriangle, ArrowUpFromLine,
  ArrowDownToLine, RefreshCw, Search, X, ChevronRight,
  Code2, GitBranch, Repeat2, Info,
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────────

interface CgNode {
  id: string;
  label: string;
  category: string;
  degree: number;
  centrality: number;
  language: string;
  highlighted: boolean;
  is_focus: boolean;
  qualified: string;
  file_path: string;
  fan_in: number;
  fan_out: number;
  is_recursive: boolean;
  parent_class?: string;
  symbol_type: string;
}

interface CgEdge {
  source: string;
  target: string;
  relationship: string;
  ambiguous: boolean;
}

interface GraphResponse {
  nodes: CgNode[];
  edges: CgEdge[];
  node_count: number;
  edge_count: number;
  error?: string;
}

interface CgStats {
  node_count: number;
  edge_count: number;
  entry_functions: number;
  recursive_functions: number;
  mutual_recursion_groups: number;
  top_fan_in: { node_id: string; fan_in: number }[];
  top_fan_out: { node_id: string; fan_out: number }[];
  generated_at: string | null;
}

interface BlastRadius {
  function_id: string;
  affected_functions: string[];
  affected_files: string[];
  depth: number;
  risk_level: string;
  recursive_cycles: string[][];
}

interface Props {
  repoName: string;
}

// ── Constants ──────────────────────────────────────────────────────────────

const CAT_COLOR: Record<string, string> = {
  entry_point:  '#6366f1',  // indigo  — call-graph roots
  core_module:  '#22c55e',  // green   — high fan-in (hottest functions)
  high_coupling:'#f59e0b',  // amber   — recursive
  focus:        '#ffffff',  // white   — selected node
  regular:      '#64748b',  // slate
};

function nodeColor(cat: string, isRecursive: boolean): string {
  if (isRecursive) return CAT_COLOR.high_coupling;
  return CAT_COLOR[cat] ?? CAT_COLOR.regular;
}

function shortId(id: string): string {
  // "{file}::{qualified}" → show just the qualified part
  const parts = id.split('::');
  return parts.length > 1 ? parts[1] : id;
}

function riskTone(level: string): 'danger' | 'warn' | 'success' {
  if (level === 'high') return 'danger';
  if (level === 'medium') return 'warn';
  return 'success';
}

// ── React Flow node/edge builders ──────────────────────────────────────────

function toRFNodes(nodes: CgNode[]) {
  return nodes.map((n, i) => ({
    id: n.id,
    position: { x: (i % 12) * 180, y: Math.floor(i / 12) * 100 },
    data: {
      label: (
        <div className="text-[10px] font-mono text-center leading-tight px-1">
          {n.is_recursive && <Repeat2 className="h-2.5 w-2.5 inline mr-0.5 text-amber-400" />}
          {shortId(n.id)}
          {n.fan_in > 0 && (
            <span className="ml-1 text-[9px] text-slate-400">↙{n.fan_in}</span>
          )}
        </div>
      ),
    },
    style: {
      background: nodeColor(n.category, n.is_recursive),
      border: n.is_focus ? '2px solid #fff' : n.highlighted ? '1.5px solid #6366f1' : '1px solid rgba(255,255,255,0.15)',
      borderRadius: 6,
      padding: '4px 8px',
      minWidth: 100,
      color: '#fff',
      fontSize: 10,
      cursor: 'pointer',
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    // Store raw data for the details panel
    _cgNode: n,
  }));
}

function toRFEdges(edges: CgEdge[]) {
  return edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.ambiguous ? '?' : undefined,
    animated: false,
    style: {
      stroke: e.ambiguous ? '#f59e0b' : '#334155',
      strokeWidth: 1.5,
      strokeDasharray: e.ambiguous ? '4 3' : undefined,
    },
    markerEnd: { type: MarkerType.ArrowClosed, color: e.ambiguous ? '#f59e0b' : '#334155' },
  }));
}

// ── Node detail panel ──────────────────────────────────────────────────────

interface NodePanelProps {
  node: CgNode;
  repoName: string;
  onClose: () => void;
  onBlastRadius: (id: string) => void;
  onNeighbors: (id: string) => void;
  onTrace: (id: string, dir: 'forward' | 'backward') => void;
}

const NodePanel: React.FC<NodePanelProps> = ({
  node, repoName, onClose, onBlastRadius, onNeighbors, onTrace,
}) => {
  const [owner, repo] = repoName.split('/');
  const encodedId = encodeURIComponent(node.id);

  return (
    <aside
      className="w-72 shrink-0 border-l border-border bg-surface flex flex-col overflow-hidden"
      aria-label="Function details"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-xs font-semibold text-text font-mono truncate">{node.label}</span>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text focus-visible:outline-none focus-visible:shadow-ring rounded"
          aria-label="Close panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs font-sans">
        {/* Metadata */}
        <div className="space-y-2">
          <p className="text-text-muted break-all font-mono leading-relaxed">{node.file_path}</p>
          <div className="flex flex-wrap gap-1.5">
            <Badge tone="primary">{node.symbol_type}</Badge>
            <Badge tone="info">{node.language}</Badge>
            {node.is_recursive && <Badge tone="warn"><Repeat2 className="h-3 w-3" /> recursive</Badge>}
            {node.fan_in === 0 && <Badge tone="success">entry point</Badge>}
          </div>
          {node.parent_class && (
            <p className="text-text-muted">Class: <span className="font-mono text-text">{node.parent_class}</span></p>
          )}
        </div>

        {/* Fan-in / Fan-out */}
        <div className="grid grid-cols-2 gap-2">
          <div className="card p-3 text-center">
            <p className="text-text-muted text-[10px] uppercase tracking-wide">Fan-in</p>
            <p className="text-xl font-bold font-mono text-primary">{node.fan_in}</p>
            <p className="text-[10px] text-text-muted">callers</p>
          </div>
          <div className="card p-3 text-center">
            <p className="text-text-muted text-[10px] uppercase tracking-wide">Fan-out</p>
            <p className="text-xl font-bold font-mono text-primary">{node.fan_out}</p>
            <p className="text-[10px] text-text-muted">callees</p>
          </div>
        </div>

        {/* Actions */}
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">Actions</p>
          <button
            onClick={() => onNeighbors(node.id)}
            className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-md
                       border border-border hover:border-primary/40 hover:bg-surface/60
                       transition-colors focus-visible:outline-none focus-visible:shadow-ring"
          >
            <GitBranch className="h-3.5 w-3.5 text-primary shrink-0" />
            <span>Show neighbors</span>
          </button>
          <button
            onClick={() => onTrace(node.id, 'forward')}
            className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-md
                       border border-border hover:border-primary/40 hover:bg-surface/60
                       transition-colors focus-visible:outline-none focus-visible:shadow-ring"
          >
            <ArrowDownToLine className="h-3.5 w-3.5 text-green-400 shrink-0" />
            <span>Trace callees (forward)</span>
          </button>
          <button
            onClick={() => onTrace(node.id, 'backward')}
            className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-md
                       border border-border hover:border-primary/40 hover:bg-surface/60
                       transition-colors focus-visible:outline-none focus-visible:shadow-ring"
          >
            <ArrowUpFromLine className="h-3.5 w-3.5 text-orange-400 shrink-0" />
            <span>Trace callers (backward)</span>
          </button>
          <button
            onClick={() => onBlastRadius(node.id)}
            className="w-full text-left flex items-center gap-2 px-3 py-2 rounded-md
                       border border-border hover:border-danger/40 hover:bg-danger/5
                       transition-colors focus-visible:outline-none focus-visible:shadow-ring"
          >
            <Zap className="h-3.5 w-3.5 text-danger shrink-0" />
            <span>Blast radius</span>
          </button>
        </div>
      </div>
    </aside>
  );
};

// ── Blast radius panel ─────────────────────────────────────────────────────

const BlastRadiusPanel: React.FC<{
  br: BlastRadius;
  onClose: () => void;
}> = ({ br, onClose }) => (
  <div className="card p-5 space-y-4 fade-up">
    <div className="flex items-center justify-between">
      <h3 className="panel-title">
        <Zap className="h-4 w-4 text-primary" /> Blast Radius
      </h3>
      <button
        onClick={onClose}
        aria-label="Close blast radius"
        className="text-text-muted hover:text-text focus-visible:outline-none rounded"
      >
        <X className="h-4 w-4" />
      </button>
    </div>

    <div className="grid grid-cols-3 gap-3">
      <div className="card p-3 text-center">
        <p className="text-[10px] text-text-muted uppercase tracking-wide">Callers affected</p>
        <p className="text-2xl font-bold font-mono text-text">{br.affected_functions.length}</p>
      </div>
      <div className="card p-3 text-center">
        <p className="text-[10px] text-text-muted uppercase tracking-wide">Files affected</p>
        <p className="text-2xl font-bold font-mono text-text">{br.affected_files.length}</p>
      </div>
      <div className="card p-3 text-center">
        <p className="text-[10px] text-text-muted uppercase tracking-wide">Max depth</p>
        <p className="text-2xl font-bold font-mono text-text">{br.depth}</p>
      </div>
    </div>

    <div className="flex items-center gap-2">
      <span className="text-xs text-text-muted font-sans">Risk level</span>
      <Badge tone={riskTone(br.risk_level)}>{br.risk_level.toUpperCase()}</Badge>
    </div>

    {br.recursive_cycles.length > 0 && (
      <div className="space-y-2">
        <p className="text-[11px] font-semibold text-orange-400 flex items-center gap-1.5">
          <Repeat2 className="h-3.5 w-3.5" /> {br.recursive_cycles.length} mutual recursion group{br.recursive_cycles.length > 1 ? 's' : ''} detected
        </p>
        {br.recursive_cycles.slice(0, 3).map((cycle, i) => (
          <div key={i} className="text-[10px] font-mono text-text-muted bg-canvas/60 rounded px-2 py-1">
            {cycle.map(shortId).join(' ↔ ')}
          </div>
        ))}
      </div>
    )}

    {br.affected_files.length > 0 && (
      <div className="space-y-1 max-h-40 overflow-y-auto">
        <p className="text-[10px] uppercase tracking-wide text-text-muted font-semibold">Affected files</p>
        {br.affected_files.map((f) => (
          <p key={f} className="text-[11px] font-mono text-text-muted truncate">{f}</p>
        ))}
      </div>
    )}
  </div>
);

// ── Stats panel ────────────────────────────────────────────────────────────

const StatsPanel: React.FC<{ stats: CgStats }> = ({ stats }) => (
  <div className="space-y-4">
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
      <MetricCard tone="primary" icon={<Workflow className="h-4 w-4" />}
        label="Functions" value={stats.node_count.toLocaleString()} hint="tracked symbols" />
      <MetricCard tone="info" icon={<GitBranch className="h-4 w-4" />}
        label="Call Edges" value={stats.edge_count.toLocaleString()} hint="call relationships" />
      <MetricCard tone="success" icon={<ArrowUpFromLine className="h-4 w-4" />}
        label="Entry Points" value={stats.entry_functions} hint="no callers" />
      <MetricCard tone="warn" icon={<Repeat2 className="h-4 w-4" />}
        label="Recursive" value={stats.recursive_functions} hint="self-calling" />
      <MetricCard tone="danger" icon={<AlertTriangle className="h-4 w-4" />}
        label="Mutual Cycles" value={stats.mutual_recursion_groups} hint="SCCs > 1" />
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="card p-4 space-y-2">
        <h3 className="panel-title"><ArrowUpFromLine className="h-3.5 w-3.5 text-primary" /> Top Fan-in (Most Called)</h3>
        {stats.top_fan_in.slice(0, 8).map((item, i) => (
          <div key={item.node_id} className="flex items-center gap-2 text-xs">
            <span className="text-text-muted font-mono w-4 shrink-0">#{i + 1}</span>
            <span className="flex-1 font-mono text-text truncate">{shortId(item.node_id)}</span>
            <Badge tone="primary">{item.fan_in}</Badge>
          </div>
        ))}
      </div>
      <div className="card p-4 space-y-2">
        <h3 className="panel-title"><ArrowDownToLine className="h-3.5 w-3.5 text-primary" /> Top Fan-out (Most Calls)</h3>
        {stats.top_fan_out.slice(0, 8).map((item, i) => (
          <div key={item.node_id} className="flex items-center gap-2 text-xs">
            <span className="text-text-muted font-mono w-4 shrink-0">#{i + 1}</span>
            <span className="flex-1 font-mono text-text truncate">{shortId(item.node_id)}</span>
            <Badge tone="info">{(item as any).fan_out}</Badge>
          </div>
        ))}
      </div>
    </div>
  </div>
);

// ── React Flow canvas wrapper ──────────────────────────────────────────────

interface CanvasProps {
  cgNodes: CgNode[];
  cgEdges: CgEdge[];
  onNodeClick: (node: CgNode) => void;
}

const CallGraphCanvas: React.FC<CanvasProps> = ({ cgNodes, cgEdges, onNodeClick }) => {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);

  // Re-layout whenever data changes using a simple grid placement
  // (no dagre dependency needed — real layout emerges from React Flow's
  // built-in fitView after position seeding)
  useEffect(() => {
    setRfNodes(toRFNodes(cgNodes) as any);
    setRfEdges(toRFEdges(cgEdges) as any);
  }, [cgNodes, cgEdges]);

  const handleNodeClick = useCallback((_: any, node: any) => {
    const original = cgNodes.find((n) => n.id === node.id);
    if (original) onNodeClick(original);
  }, [cgNodes, onNodeClick]);

  return (
    <ReactFlow
      nodes={rfNodes}
      edges={rfEdges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.1}
      maxZoom={3}
      proOptions={{ hideAttribution: true }}
      className="bg-canvas/5"
    >
      <Background color="#1e293b" gap={24} />
      <Controls showInteractive={false} className="!bg-surface !border-border" />
      <PanControls />
      <MiniMap
        nodeColor={(n: any) => nodeColor(n.data?.category ?? 'regular', false)}
        className="!bg-surface !border-border"
        maskColor="rgba(0,0,0,0.4)"
      />
    </ReactFlow>
  );
};

// ── Main component ─────────────────────────────────────────────────────────

export const CallGraphAnalyzer: React.FC<Props> = ({ repoName }) => {
  const [owner, repoSlug] = repoName.split('/');

  // Build state
  const [building, setBuilding] = useState(false);
  const [buildProgress, setBuildProgress] = useState('');
  const [buildError, setBuildError] = useState<string | null>(null);

  // Graph data
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  // Stats
  const [stats, setStats] = useState<CgStats | null>(null);

  // UI state
  const [activeView, setActiveView] = useState<'graph' | 'stats'>('graph');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<CgNode | null>(null);
  const [blastRadius, setBlastRadius] = useState<BlastRadius | null>(null);
  const [brLoading, setBrLoading] = useState(false);

  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Auto-load on mount ───────────────────────────────────────────────────
  useEffect(() => {
    setSelectedNode(null);
    setBlastRadius(null);
    setSearchQuery('');
    setGraphData(null);
    setStats(null);
    loadGraph('');
    loadStats();
  }, [repoName]);

  // ── Data fetchers ────────────────────────────────────────────────────────

  const loadGraph = useCallback(async (q: string) => {
    setGraphLoading(true);
    setGraphError(null);
    try {
      const url = apiUrl(
        `/api/call-graph/${owner}/${repoSlug}${q ? `?q=${encodeURIComponent(q)}` : ''}`
      );
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        // 404 just means not built yet — show empty state, not an error
        if (res.status === 404) { setGraphData(null); return; }
        throw new Error(extractErrorMessage(body));
      }
      const data: GraphResponse = await res.json();
      setGraphData(data);
    } catch (err: any) {
      setGraphError(extractErrorMessage(err));
    } finally {
      setGraphLoading(false);
    }
  }, [owner, repoSlug]);

  const loadStats = useCallback(async () => {
    try {
      const res = await fetch(apiUrl(`/api/call-graph/${owner}/${repoSlug}/stats`));
      if (res.ok) setStats(await res.json());
    } catch { /* stats are optional */ }
  }, [owner, repoSlug]);

  const loadNeighbors = useCallback(async (functionId: string) => {
    setGraphLoading(true);
    setGraphError(null);
    try {
      const res = await fetch(
        apiUrl(`/api/call-graph/${owner}/${repoSlug}/neighbors/${encodeURIComponent(functionId)}`)
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: GraphResponse = await res.json();
      setGraphData(data);
    } catch (err: any) {
      setGraphError(extractErrorMessage(err));
    } finally {
      setGraphLoading(false);
    }
  }, [owner, repoSlug]);

  const loadTrace = useCallback(async (functionId: string, dir: 'forward' | 'backward') => {
    setGraphLoading(true);
    setGraphError(null);
    try {
      const res = await fetch(
        apiUrl(`/api/call-graph/${owner}/${repoSlug}/trace/${encodeURIComponent(functionId)}?direction=${dir}&depth=6`)
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: GraphResponse = await res.json();
      setGraphData(data);
    } catch (err: any) {
      setGraphError(extractErrorMessage(err));
    } finally {
      setGraphLoading(false);
    }
  }, [owner, repoSlug]);

  const loadBlastRadius = useCallback(async (functionId: string) => {
    setBrLoading(true);
    setBlastRadius(null);
    try {
      const res = await fetch(
        apiUrl(`/api/call-graph/${owner}/${repoSlug}/blast-radius/${encodeURIComponent(functionId)}`)
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setBlastRadius(await res.json());
    } catch (err: any) {
      setGraphError(extractErrorMessage(err));
    } finally {
      setBrLoading(false);
    }
  }, [owner, repoSlug]);

  // ── Build handler (SSE stream) ───────────────────────────────────────────

  const handleBuild = useCallback(async () => {
    setBuilding(true);
    setBuildError(null);
    setBuildProgress('Starting…');
    setGraphData(null);
    setStats(null);

    try {
      const res = await fetch(apiUrl('/api/call-graph/build'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo: repoName }),
      });

      if (!res.body) throw new Error('No response body.');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';

        for (const part of parts) {
          const line = part.replace(/^data: /, '').trim();
          if (!line) continue;
          try {
            const ev = JSON.parse(line);
            if (ev.status === 'error') { setBuildError(ev.message); setBuilding(false); return; }
            if (ev.status === 'done') { setBuilding(false); loadGraph(''); loadStats(); return; }
            if (ev.message) setBuildProgress(ev.message);
          } catch { /* non-JSON */ }
        }
      }
    } catch (err: any) {
      setBuildError(extractErrorMessage(err));
    } finally {
      setBuilding(false);
    }
  }, [repoName, loadGraph, loadStats]);

  // ── Search debounce ──────────────────────────────────────────────────────
  const handleSearch = (val: string) => {
    setSearchQuery(val);
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    searchDebounce.current = setTimeout(() => loadGraph(val), 350);
  };

  const resetView = () => {
    setSearchQuery('');
    setSelectedNode(null);
    setBlastRadius(null);
    loadGraph('');
  };

  // ── Render ───────────────────────────────────────────────────────────────

  const notBuilt = !graphLoading && !graphData && !graphError;
  const hasData  = !!graphData && (graphData.node_count ?? 0) > 0;

  return (
    <div className="space-y-5 fade-up">

      {/* ── Header bar ─────────────────────────────────────────────────── */}
      <div className="card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="panel-title">
              <Workflow className="h-4 w-4 text-primary" aria-hidden="true" />
              Function Call Graph
            </h2>
            <p className="text-xs text-text-muted font-sans mt-1">
              Function-to-function dependency graph. Blast radius, callers, callees, recursion detection.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {hasData && (
              <button
                onClick={resetView}
                aria-label="Reset view"
                className="btn-ghost text-xs"
              >
                <RefreshCw className="h-3.5 w-3.5" /> Reset
              </button>
            )}
            <Button onClick={handleBuild} disabled={building}>
              {building
                ? <><RefreshCw className="h-3.5 w-3.5 animate-spin" /> Building…</>
                : hasData ? <><RefreshCw className="h-3.5 w-3.5" /> Rebuild</>
                : 'Build Call Graph'}
            </Button>
          </div>
        </div>

        {/* Build progress */}
        {building && (
          <div className="space-y-1.5" role="status" aria-live="polite">
            <div className="h-1 rounded-full bg-border overflow-hidden">
              <div className="h-full bg-primary rounded-full animate-pulse w-3/5" />
            </div>
            <p className="text-xs font-mono text-text-muted">{buildProgress}</p>
          </div>
        )}

        {/* Build error */}
        {buildError && (
          <div role="alert" className="text-xs text-danger bg-danger/10 border border-danger/30 p-3 rounded-lg font-sans">
            {buildError}
          </div>
        )}
      </div>

      {/* ── Loading skeleton ────────────────────────────────────────────── */}
      {(graphLoading || brLoading) && !hasData && (
        <SkeletonGroup label="Loading call graph">
          <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[0,1,2,3,4].map(i => <SkeletonCard key={i} />)}
            </div>
            <div className="h-[500px] card">
              <Skeleton size="h-full w-full" />
            </div>
          </div>
        </SkeletonGroup>
      )}

      {/* ── Not built empty state ────────────────────────────────────────── */}
      {notBuilt && !building && (
        <EmptyState
          icon={<Workflow className="h-6 w-6" aria-hidden="true" />}
          title="Call graph not built yet"
          description="Click 'Build Call Graph' to extract function call relationships from the codebase."
          action={<Button onClick={handleBuild}>Build Call Graph</Button>}
        />
      )}

      {/* ── Graph error ─────────────────────────────────────────────────── */}
      {graphError && !graphLoading && (
        <div role="alert" className="text-xs text-danger bg-danger/10 border border-danger/30 p-3 rounded-lg font-sans">
          {graphError}
        </div>
      )}

      {/* ── Main content ────────────────────────────────────────────────── */}
      {hasData && !graphLoading && (
        <div className="space-y-4 fade-up">

          {/* View toggle */}
          <div className="card p-1 flex gap-1 w-fit" role="tablist">
            {(['graph', 'stats'] as const).map((v) => (
              <button
                key={v}
                role="tab"
                aria-selected={activeView === v}
                onClick={() => setActiveView(v)}
                className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors capitalize
                  focus-visible:outline-none focus-visible:shadow-ring
                  ${activeView === v ? 'bg-primary text-white' : 'text-text-muted hover:text-text hover:bg-surface'}`}
              >
                {v === 'graph' ? '🔗 Graph' : '📊 Stats'}
              </button>
            ))}
          </div>

          {/* Stats view */}
          {activeView === 'stats' && stats && <StatsPanel stats={stats} />}
          {activeView === 'stats' && !stats && (
            <EmptyState compact icon={<Info className="h-5 w-5" />}
              title="Stats unavailable" description="Build the call graph to see statistics." />
          )}

          {/* Graph view */}
          {activeView === 'graph' && (
            <div className="space-y-3">

              {/* Search bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-text-muted pointer-events-none" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  placeholder="Search functions… (e.g. authenticate, parse)"
                  className="input pl-9 pr-9 text-xs w-full"
                  aria-label="Search call graph"
                />
                {searchQuery && (
                  <button
                    onClick={() => { setSearchQuery(''); loadGraph(''); }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text"
                    aria-label="Clear search"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>

              {/* Legend */}
              <div className="flex flex-wrap gap-3 text-[10px] font-mono text-text-muted">
                {[
                  { color: CAT_COLOR.entry_point, label: 'Entry point' },
                  { color: CAT_COLOR.core_module,  label: 'High fan-in' },
                  { color: CAT_COLOR.high_coupling,label: 'Recursive' },
                  { color: CAT_COLOR.regular,      label: 'Regular' },
                ].map(({ color, label }) => (
                  <span key={label} className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: color }} aria-hidden="true" />
                    {label}
                  </span>
                ))}
                <span className="flex items-center gap-1.5">
                  <span className="h-0.5 w-5 border-t-2 border-dashed border-amber-400" aria-hidden="true" />
                  Ambiguous edge
                </span>
              </div>

              {/* Canvas + side panel */}
              <div className="flex gap-0 border border-border rounded-xl overflow-hidden"
                   style={{ height: 540 }}>
                <div className="flex-1 min-w-0">
                  <ReactFlowProvider>
                    <CallGraphCanvas
                      cgNodes={graphData.nodes}
                      cgEdges={graphData.edges}
                      onNodeClick={(node) => {
                        setSelectedNode(node);
                        setBlastRadius(null);
                      }}
                    />
                  </ReactFlowProvider>
                </div>

                {/* Node details panel */}
                {selectedNode && (
                  <NodePanel
                    node={selectedNode}
                    repoName={repoName}
                    onClose={() => { setSelectedNode(null); setBlastRadius(null); }}
                    onBlastRadius={loadBlastRadius}
                    onNeighbors={loadNeighbors}
                    onTrace={loadTrace}
                  />
                )}
              </div>

              {/* Graph metadata */}
              <p className="text-[10px] font-mono text-text-muted text-right">
                {graphData.node_count} functions · {graphData.edge_count} call edges
                {searchQuery && ` · filtered by "${searchQuery}"`}
              </p>

              {/* Blast radius panel — shown below graph */}
              {brLoading && (
                <SkeletonGroup label="Computing blast radius">
                  <SkeletonCard />
                </SkeletonGroup>
              )}
              {blastRadius && !brLoading && (
                <BlastRadiusPanel
                  br={blastRadius}
                  onClose={() => setBlastRadius(null)}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CallGraphAnalyzer;
