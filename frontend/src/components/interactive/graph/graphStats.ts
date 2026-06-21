/**
 * Pure client-side graph statistics over the API response.
 * No backend changes — derives counts from nodes & edges already returned.
 */

import type { GraphEdge, GraphNode } from './types';

interface Stats {
  components: number;
  /** Number of strongly-connected components with size > 1 — i.e. cycle clusters */
  cycleClusters: number;
}

export function computeGraphStats(nodes: GraphNode[], edges: GraphEdge[]): Stats {
  if (nodes.length === 0) return { components: 0, cycleClusters: 0 };

  // Undirected adjacency for weakly-connected components
  const undirected = new Map<string, Set<string>>();
  nodes.forEach((n) => undirected.set(n.id, new Set()));
  edges.forEach((e) => {
    undirected.get(e.source)?.add(e.target);
    undirected.get(e.target)?.add(e.source);
  });

  // BFS-count connected components
  const seen = new Set<string>();
  let components = 0;
  for (const n of nodes) {
    if (seen.has(n.id)) continue;
    components++;
    const queue: string[] = [n.id];
    seen.add(n.id);
    while (queue.length) {
      const cur = queue.shift()!;
      const neighbours = undirected.get(cur);
      if (!neighbours) continue;
      neighbours.forEach((next) => {
        if (!seen.has(next)) {
          seen.add(next);
          queue.push(next);
        }
      });
    }
  }

  // Tarjan's SCC over the DIRECTED graph
  const directed = new Map<string, string[]>();
  nodes.forEach((n) => directed.set(n.id, []));
  edges.forEach((e) => directed.get(e.source)?.push(e.target));

  const index = new Map<string, number>();
  const lowlink = new Map<string, number>();
  const onStack = new Set<string>();
  const stack: string[] = [];
  let counter = 0;
  let cycleClusters = 0;

  // Iterative Tarjan to avoid stack overflow on big graphs
  function strongConnect(start: string) {
    type Frame = { node: string; i: number };
    const frames: Frame[] = [{ node: start, i: 0 }];
    index.set(start, counter);
    lowlink.set(start, counter);
    counter++;
    stack.push(start);
    onStack.add(start);

    while (frames.length) {
      const frame = frames[frames.length - 1];
      const targets = directed.get(frame.node) ?? [];
      if (frame.i < targets.length) {
        const w = targets[frame.i++];
        if (!index.has(w)) {
          index.set(w, counter);
          lowlink.set(w, counter);
          counter++;
          stack.push(w);
          onStack.add(w);
          frames.push({ node: w, i: 0 });
        } else if (onStack.has(w)) {
          lowlink.set(frame.node, Math.min(lowlink.get(frame.node)!, index.get(w)!));
        }
      } else {
        if (lowlink.get(frame.node) === index.get(frame.node)) {
          let size = 0;
          let w: string;
          do {
            w = stack.pop()!;
            onStack.delete(w);
            size++;
          } while (w !== frame.node);
          if (size > 1) cycleClusters++;
        }
        frames.pop();
        if (frames.length) {
          const parent = frames[frames.length - 1];
          lowlink.set(parent.node, Math.min(lowlink.get(parent.node)!, lowlink.get(frame.node)!));
        }
      }
    }
  }

  for (const n of nodes) {
    if (!index.has(n.id)) strongConnect(n.id);
  }

  return { components, cycleClusters };
}
