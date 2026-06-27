import React, { useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  type Node,
  type Edge,
} from 'reactflow';
import { PanControls } from './PanControls';
import dagre from 'dagre';
import 'reactflow/dist/style.css';
import { CATEGORY_COLORS } from './types';
import type { GraphNode, GraphEdge } from './types';

// ---------------------------------------------------------------------------
// Layout
// ---------------------------------------------------------------------------

const NODE_W = 200;
const NODE_H = 40;

function applyDagreLayout(
  rfNodes: Node[],
  rfEdges: Edge[],
  direction: 'TB' | 'LR' = 'TB',
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, ranksep: 60, nodesep: 40 });

  rfNodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  rfEdges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const laid = rfNodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
    };
  });
  return { nodes: laid, edges: rfEdges };
}

// ---------------------------------------------------------------------------
// Node style factory
// ---------------------------------------------------------------------------

/**
 * Returns a Tailwind className string for a graph node.
 *
 * Style priority: focus > highlighted > category > regular.
 */
function nodeClassName(
  category: string,
  highlighted: boolean,
  isFocus: boolean,
): string {
  const base =
    'rounded px-3 py-2 text-center text-xs font-mono truncate shadow cursor-pointer transition-all';

  if (isFocus)
    return `${base} !bg-white/20 !border-2 !border-white !text-white shadow-lg shadow-white/10 hover:!bg-white/30`;

  if (highlighted) {
    return `${base} !bg-amber-950/60 !border-2 !border-amber-400 !text-amber-300 shadow-lg shadow-amber-500/10 hover:!bg-amber-900/40`;
  }

  switch (category) {
    case 'entry_point':
      return `${base} !bg-emerald-950/60 !border-2 !border-emerald-500 !text-emerald-400 font-semibold shadow-emerald-500/5 hover:!bg-emerald-900/40`;
    case 'core_module':
      return `${base} !bg-blue-950/60 !border-2 !border-blue-500 !text-blue-400 font-semibold shadow-blue-500/5 hover:!bg-blue-900/40`;
    case 'high_coupling':
      return `${base} !bg-orange-950/60 !border !border-orange-500 !text-orange-400 hover:!bg-orange-900/40`;
    case 'directory':
      return `${base} !bg-purple-950/60 !border !border-purple-500 !text-purple-400 font-semibold hover:!bg-purple-900/40`;
    default:
      return `${base} !bg-zinc-900 !border !border-zinc-700 !text-zinc-300 hover:!border-zinc-500`;
  }
}

// ---------------------------------------------------------------------------
// Conversion helpers
// ---------------------------------------------------------------------------

export function toReactFlowNodes(apiNodes: GraphNode[]): Node[] {
  return apiNodes.map((n) => ({
    id: n.id,
    type: 'default',
    data: { label: n.label, raw: n },
    className: nodeClassName(n.category, n.highlighted, n.is_focus),
    position: { x: 0, y: 0 }, // overwritten by layout
  }));
}

export function toReactFlowEdges(apiEdges: GraphEdge[], categoryMap: Map<string, string>): Edge[] {
  return apiEdges.map((e) => {
    const srcCategory = categoryMap.get(e.source) ?? 'regular';
    let strokeColor = '#4b5563'; // default gray
    
    if (srcCategory === 'entry_point') {
      strokeColor = '#10b981'; // emerald
    } else if (srcCategory === 'core_module') {
      strokeColor = '#3b82f6'; // blue
    } else if (srcCategory === 'high_coupling') {
      strokeColor = '#f97316'; // orange
    } else if (srcCategory === 'directory') {
      strokeColor = '#a855f7'; // purple
    }

    return {
      id: `${e.source}→${e.target}`,
      source: e.source,
      target: e.target,
      animated: e.relationship === 'imports',
      style: { stroke: strokeColor, strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 12,
        height: 12,
        color: strokeColor,
      },
    };
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface GraphCanvasProps {
  apiNodes: GraphNode[];
  apiEdges: GraphEdge[];
  onNodeSelect: (node: GraphNode | null) => void;
  /** Exposed ref so parent can call fitView imperatively */
  fitViewRef: React.MutableRefObject<(() => void) | null>;
}

/**
 * Pure React Flow canvas — receives serialised graph data, converts it to
 * React Flow node/edge format, applies Dagre layout, and renders.
 *
 * Does NOT own any fetching logic.  The parent (InteractiveDependencyGraph)
 * manages all data fetching and passes results down.
 */
export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  apiNodes,
  apiEdges,
  onNodeSelect,
  fitViewRef,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const rfRef = useRef<any>(null);

  // Re-layout whenever the API data changes — keep setState inside an effect.
  useEffect(() => {
    const rfNodes = toReactFlowNodes(apiNodes);
    
    const categoryMap = new Map<string, string>();
    apiNodes.forEach((n) => categoryMap.set(n.id, n.category));
    
    const rfEdges = toReactFlowEdges(apiEdges, categoryMap);
    const { nodes: laid, edges: laidEdges } = applyDagreLayout(rfNodes, rfEdges, 'TB');
    setNodes(laid);
    setEdges(laidEdges);
  }, [apiNodes, apiEdges, setNodes, setEdges]);

  // Expose fitView to parent via ref
  const onInit = useCallback(
    (instance: any) => {
      rfRef.current = instance;
      fitViewRef.current = () => instance.fitView({ padding: 0.15, duration: 300 });
    },
    [fitViewRef],
  );

  const handleNodeClick = useCallback(
    (_evt: React.MouseEvent, node: Node) => {
      onNodeSelect(node.data?.raw ?? null);
    },
    [onNodeSelect],
  );

  const handlePaneClick = useCallback(() => {
    onNodeSelect(null);
  }, [onNodeSelect]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={handleNodeClick}
      onPaneClick={handlePaneClick}
      onInit={onInit}
      fitView
      minZoom={0.05}
      maxZoom={2.5}
      nodesDraggable
      nodesConnectable={false}
      elementsSelectable
    >
      <Controls showInteractive={false} />
      <PanControls />
      <MiniMap
        nodeColor={(node) => {
          const raw: GraphNode | undefined = node.data?.raw;
          if (!raw) return '#27272a';
          if (raw.is_focus) return '#ffffff';
          if (raw.highlighted) return '#f59e0b';
          return CATEGORY_COLORS[raw.category] ?? '#71717a';
        }}
        maskColor="rgba(15, 23, 42, 0.75)"
        className="!bg-slate-950/95 !border-slate-800/80 !rounded-xl !shadow-float overflow-hidden"
        nodeStrokeWidth={0}
        nodeBorderRadius={5}
      />
      <Background color="#27272a" gap={16} />
    </ReactFlow>
  );
};
