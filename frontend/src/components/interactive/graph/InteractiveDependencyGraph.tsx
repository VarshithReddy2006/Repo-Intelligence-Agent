import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from 'react';
import { Info, RefreshCw } from 'lucide-react';
import { ReactFlowProvider } from 'reactflow';

import { apiUrl, extractErrorMessage } from '../../../lib/api';
import { GraphCanvas } from './GraphCanvas';
import { GraphToolbar } from './GraphToolbar';
import { SearchBar } from './SearchBar';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import type { GraphNode, GraphEdge, GraphMode, GraphResponse } from './types';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build the fetch URL for each graph mode. */
function buildUrl(
  owner: string,
  repo: string,
  mode: GraphMode,
  focusNode: string | null,
  searchQuery: string,
  traceDir: 'forward' | 'backward' | 'both',
): string {
  const base = `/api/graph/${owner}/${repo}`;
  switch (mode) {
    case 'neighbors':
      return apiUrl(`${base}/neighbors/${focusNode}`);
    case 'trace_fwd':
      return apiUrl(`${base}/trace/${focusNode}?direction=forward&depth=6`);
    case 'trace_bwd':
      return apiUrl(`${base}/trace/${focusNode}?direction=backward&depth=6`);
    case 'search':
      return apiUrl(`${base}/search?q=${encodeURIComponent(searchQuery)}`);
    case 'full':
    default:
      return searchQuery.trim()
        ? apiUrl(`${base}/full?q=${encodeURIComponent(searchQuery)}`)
        : apiUrl(`${base}/full`);
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface InteractiveDependencyGraphProps {
  repoName: string;
}

/**
 * PH2-001 Interactive Dependency Graph orchestrator.
 *
 * Owns all state: mode, focusNode, searchQuery, selectedNode, graph data.
 * Delegates rendering to four sub-components:
 *   GraphToolbar    — mode buttons, fit/reset, status
 *   SearchBar       — debounced search input
 *   GraphCanvas     — React Flow canvas + Dagre layout
 *   NodeDetailsPanel — right-side drawer
 */
export const InteractiveDependencyGraph: React.FC<
  InteractiveDependencyGraphProps
> = ({ repoName }) => {
  // ── Repo split ──────────────────────────────────────────────────────────
  const [owner, repo] = useMemo(() => {
    const parts = repoName.split('/');
    return [parts[0] ?? '', parts[1] ?? ''];
  }, [repoName]);

  // ── Graph data state ────────────────────────────────────────────────────
  const [apiNodes, setApiNodes] = useState<GraphNode[]>([]);
  const [apiEdges, setApiEdges] = useState<GraphEdge[]>([]);
  const [matchCount, setMatchCount] = useState<number | null>(null);

  // ── Interaction state ───────────────────────────────────────────────────
  const [mode, setMode] = useState<GraphMode>('full');
  const [focusNode, setFocusNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  // used internally to differentiate trace directions when both toolbar
  // buttons share the same mode key
  const [traceDir, setTraceDir] = useState<'forward' | 'backward' | 'both'>(
    'both',
  );

  // ── Request state ───────────────────────────────────────────────────────
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Refs ─────────────────────────────────────────────────────────────────
  const fitViewRef = useRef<(() => void) | null>(null);
  /** AbortController for in-flight requests — cancels stale fetches. */
  const abortRef = useRef<AbortController | null>(null);
  /** Debounce timer for search input. */
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Core fetch ───────────────────────────────────────────────────────────
  const fetchGraph = useCallback(
    async (
      fetchMode: GraphMode,
      focusId: string | null,
      query: string,
      dir: 'forward' | 'backward' | 'both',
    ) => {
      if (!owner || !repo) return;

      // Cancel any in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      setLoading(true);
      setError(null);
      setMatchCount(null);

      const url = buildUrl(owner, repo, fetchMode, focusId, query, dir);

      try {
        const res = await fetch(url, { signal: abortRef.current.signal });

        if (!res.ok) {
          let detail = `HTTP ${res.status}`;
          try {
            const body = await res.json();
            detail = extractErrorMessage(body);
          } catch {
            /* ignore */
          }
          setError(detail);
          setApiNodes([]);
          setApiEdges([]);
          return;
        }

        const data: GraphResponse = await res.json();

        if (data.error) {
          setError(data.error);
          setApiNodes([]);
          setApiEdges([]);
          return;
        }

        setApiNodes(data.nodes ?? []);
        setApiEdges(data.edges ?? []);
        if (data.matched_count !== undefined) {
          setMatchCount(data.matched_count);
        }

        // Auto-fit after data loads
        setTimeout(() => fitViewRef.current?.(), 80);
      } catch (err: any) {
        if (err.name === 'AbortError') return; // stale request cancelled
        setError(extractErrorMessage(err));
        setApiNodes([]);
        setApiEdges([]);
      } finally {
        setLoading(false);
      }
    },
    [owner, repo],
  );

  // ── Initial load ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetchGraph('full', null, '', 'both');
    return () => abortRef.current?.abort();
  }, [fetchGraph]);

  // ── Search debounce ──────────────────────────────────────────────────────
  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchQuery(value);
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
      searchDebounceRef.current = setTimeout(() => {
        if (value.trim()) {
          setMode('search');
          setFocusNode(null);
          setSelectedNode(null);
          fetchGraph('search', null, value, 'both');
        } else {
          setMode('full');
          fetchGraph('full', null, '', 'both');
        }
      }, 300);
    },
    [fetchGraph],
  );

  const handleSearchClear = useCallback(() => {
    setSearchQuery('');
    setMatchCount(null);
    setMode('full');
    fetchGraph('full', null, '', 'both');
  }, [fetchGraph]);

  // ── Toolbar actions ──────────────────────────────────────────────────────
  const handleExpand = useCallback(() => {
    if (!focusNode) return;
    setMode('neighbors');
    setTraceDir('both');
    fetchGraph('neighbors', focusNode, '', 'both');
  }, [focusNode, fetchGraph]);

  const handleTraceForward = useCallback(
    (nodeId?: string) => {
      const id = nodeId ?? focusNode;
      if (!id) return;
      setFocusNode(id);
      setMode('trace_fwd');
      setTraceDir('forward');
      fetchGraph('trace_fwd', id, '', 'forward');
    },
    [focusNode, fetchGraph],
  );

  const handleTraceBackward = useCallback(
    (nodeId?: string) => {
      const id = nodeId ?? focusNode;
      if (!id) return;
      setFocusNode(id);
      setMode('trace_bwd');
      setTraceDir('backward');
      fetchGraph('trace_bwd', id, '', 'backward');
    },
    [focusNode, fetchGraph],
  );

  const handleTraceBoth = useCallback(
    (nodeId?: string) => {
      const id = nodeId ?? focusNode;
      if (!id) return;
      setFocusNode(id);
      // Reuse trace_fwd mode key — backend gets direction=both
      setMode('trace_fwd');
      setTraceDir('both');
      fetchGraph('trace_fwd', id, '', 'both');
    },
    [focusNode, fetchGraph],
  );

  const handleReset = useCallback(() => {
    setMode('full');
    setFocusNode(null);
    setSelectedNode(null);
    setSearchQuery('');
    setMatchCount(null);
    fetchGraph('full', null, '', 'both');
  }, [fetchGraph]);

  const handleFitView = useCallback(() => {
    fitViewRef.current?.();
  }, []);

  // ── Node selection ────────────────────────────────────────────────────────
  const handleNodeSelect = useCallback((node: GraphNode | null) => {
    setSelectedNode(node);
    if (node) setFocusNode(node.id);
  }, []);

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="border border-border bg-card/5 rounded-lg flex flex-col h-[640px] relative overflow-hidden">
      {/* ── Top bar: search left, legend right ─────────────────────── */}
      <div className="px-3 py-2 border-b border-border bg-canvas/40 flex items-center gap-3 z-10">
        <SearchBar
          value={searchQuery}
          matchCount={matchCount}
          onChange={handleSearchChange}
          onClear={handleSearchClear}
        />
        <div className="ml-auto text-[9px] font-mono text-text-muted hidden sm:flex items-center gap-2.5">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Entry
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-blue-500" /> Core
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-orange-500" /> Coupled
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-400" /> Match
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-white" /> Focus
          </span>
        </div>
      </div>

      {/* ── Toolbar ─────────────────────────────────────────────────── */}
      <GraphToolbar
        mode={mode}
        focusNode={focusNode}
        loading={loading}
        nodeCount={apiNodes.length}
        edgeCount={apiEdges.length}
        onFitView={handleFitView}
        onReset={handleReset}
        onExpand={handleExpand}
        onTraceForward={() => handleTraceForward()}
        onTraceBackward={() => handleTraceBackward()}
        onTraceBoth={() => handleTraceBoth()}
        onNeighbors={handleExpand}
      />

      {/* ── Main canvas area ─────────────────────────────────────────── */}
      <div className="flex-grow relative flex overflow-hidden">
        {/* Loading overlay */}
        {loading && (
          <div className="absolute inset-0 bg-canvas/70 flex flex-col items-center justify-center gap-2 z-30 font-mono text-xs text-text-muted">
            <RefreshCw className="h-5 w-5 animate-spin text-primary" />
            <span>Loading graph…</span>
          </div>
        )}

        {/* Error overlay */}
        {!loading && error && (
          <div className="absolute inset-0 bg-canvas/80 flex flex-col items-center justify-center gap-3 z-30 p-6 text-center">
            <Info className="h-6 w-6 text-primary" />
            <span className="font-mono text-xs text-text-muted max-w-sm leading-relaxed">
              {error}
            </span>
            <button
              onClick={handleReset}
              className="text-primary border border-primary/20 px-3 py-1.5 rounded text-xs font-mono hover:bg-primary/5 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && apiNodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 z-30">
            <Info className="h-5 w-5 text-primary" />
            <span className="font-mono text-xs text-text-muted">
              {searchQuery ? 'No nodes matched your search.' : 'No graph data available.'}
            </span>
          </div>
        )}

        {/* React Flow canvas — always mounted so hooks stay stable */}
        <div className="flex-grow h-full bg-canvas/10">
          <ReactFlowProvider>
            <GraphCanvas
              apiNodes={apiNodes}
              apiEdges={apiEdges}
              onNodeSelect={handleNodeSelect}
              fitViewRef={fitViewRef}
            />
          </ReactFlowProvider>
        </div>

        {/* Node details panel */}
        {selectedNode && (
          <NodeDetailsPanel
            node={selectedNode}
            onClose={() => setSelectedNode(null)}
            onExpand={(id) => {
              setFocusNode(id);
              setMode('neighbors');
              fetchGraph('neighbors', id, '', 'both');
            }}
            onTraceForward={handleTraceForward}
            onTraceBackward={handleTraceBackward}
            onTraceBoth={handleTraceBoth}
          />
        )}
      </div>
    </div>
  );
};

export default InteractiveDependencyGraph;
