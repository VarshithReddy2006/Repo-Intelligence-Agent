/**
 * Shared TypeScript types for PH2-001 Interactive Dependency Graph.
 * All components in the graph/ folder import from here.
 */

/** One node returned by any /api/graph/* endpoint. */
export interface GraphNode {
  id: string;
  label: string;
  /** entry_point | core_module | high_coupling | directory | regular | focus */
  category: string;
  degree: number;
  centrality: number;
  language: string;
  highlighted: boolean;
  is_focus: boolean;
}

/** One edge returned by any /api/graph/* endpoint. */
export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

/** Full API response shape for all /api/graph/* endpoints. */
export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
  /** Present only when an error occurred — callers check this first. */
  error?: string;
  /** Present only on /search responses. */
  matched_count?: number;
  query?: string;
}

/**
 * Interaction mode driving which overlay the toolbar shows as active
 * and what happens on node click.
 */
export type GraphMode =
  | 'full'        // show the complete graph, no focus
  | 'neighbors'   // show immediate neighbours of focusNode
  | 'trace_fwd'   // trace forward deps from focusNode
  | 'trace_bwd'   // trace backward deps from focusNode
  | 'search';     // highlight search matches on top of full graph

/** Colour tokens used consistently across canvas, panel, and toolbar. */
export const CATEGORY_COLORS: Record<string, string> = {
  entry_point:  '#10b981', // emerald-500
  core_module:  '#3b82f6', // blue-500
  high_coupling:'#f97316', // orange-500
  directory:    '#a855f7', // purple-500
  focus:        '#ffffff', // white
  regular:      '#71717a', // zinc-500
};

export const CATEGORY_LABELS: Record<string, string> = {
  entry_point:   'Entry Point',
  core_module:   'Core Module',
  high_coupling: 'High Coupling',
  directory:     'Directory',
  focus:         'Focus',
  regular:       'Regular',
};
