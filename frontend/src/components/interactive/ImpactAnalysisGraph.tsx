import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import dagre from 'dagre';
import { 
  Info, 
  X, 
  AlertTriangle, 
  CheckCircle,
  ExternalLink,
  MessageSquare,
  Layers,
  ChevronRight,
  TrendingUp
} from 'lucide-react';
import 'reactflow/dist/style.css';

interface DependencyPath {
  path: string[];
}

interface ImpactAnalysisData {
  repo: string;
  issue_text: string;
  directly_affected_files: string[];
  indirectly_affected_files: string[];
  affected_components: string[];
  risk_level: string;
  estimated_file_count: number;
  dependency_paths: DependencyPath[];
  confidence: number;
}

interface GraphProps {
  repoName: string;
  impactData: ImpactAnalysisData;
  onReset: () => void;
}

interface SelectedNodeData {
  id: string;
  label: string;
  category: 'direct' | 'indirect' | 'component' | 'regular';
  inDegree: number;
  outDegree: number;
  riskContribution: 'High' | 'Medium' | 'Low';
  reason?: string;
}

const nodeWidth = 200;
const nodeHeight = 40;

const getLayoutedElements = (nodes: any[], edges: any[], direction = 'LR') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, ranksep: 80, nodesep: 40 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export const ImpactAnalysisGraph: React.FC<GraphProps> = ({ repoName, impactData, onReset }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<SelectedNodeData | null>(null);

  // Parse raw impact data into React Flow nodes and edges
  useEffect(() => {
    const directSet = new Set(impactData.directly_affected_files);
    const indirectSet = new Set(impactData.indirectly_affected_files);
    const componentSet = new Set(impactData.affected_components);

    const uniqueNodes = new Set<string>();
    const tempEdges: { source: string; target: string; isDotted?: boolean }[] = [];

    // 1. Process propagation paths
    impactData.dependency_paths.forEach((p) => {
      const path = p.path;
      for (let i = 0; i < path.length; i++) {
        uniqueNodes.add(path[i]);
        if (i < path.length - 1) {
          tempEdges.push({
            source: path[i],
            target: path[i + 1]
          });
        }
      }
    });

    // 2. Add remaining isolated files
    impactData.directly_affected_files.forEach((f) => uniqueNodes.add(f));
    impactData.indirectly_affected_files.forEach((f) => uniqueNodes.add(f));

    // 3. Process component nodes
    impactData.affected_components.forEach((comp) => {
      const compId = `component-${comp}`;
      uniqueNodes.add(compId);

      // Heuristic connection: Link components to directly affected files that are related
      let connectedAny = false;
      const compLower = comp.toLowerCase();
      
      impactData.directly_affected_files.forEach((file) => {
        const fileLower = file.toLowerCase();
        // Simple matching logic
        const matches = 
          (compLower.includes('api') && (fileLower.includes('api') || fileLower.includes('route'))) ||
          (compLower.includes('auth') && (fileLower.includes('auth') || fileLower.includes('sec'))) ||
          (compLower.includes('service') && fileLower.includes('service')) ||
          (compLower.includes('db') && (fileLower.includes('db') || fileLower.includes('model'))) ||
          fileLower.includes(compLower);

        if (matches) {
          tempEdges.push({
            source: compId,
            target: file,
            isDotted: true
          });
          connectedAny = true;
        }
      });

      // Fallback: connect component node to the first directly affected file if no matches found
      if (!connectedAny && impactData.directly_affected_files.length > 0) {
        tempEdges.push({
          source: compId,
          target: impactData.directly_affected_files[0],
          isDotted: true
        });
      }
    });

    // Build React Flow Node objects
    const flowNodes = Array.from(uniqueNodes).map((id) => {
      const isComponent = id.startsWith('component-');
      const cleanLabel = isComponent ? id.replace('component-', '') : id.split('/').pop() || id;
      
      let category: 'direct' | 'indirect' | 'component' | 'regular' = 'regular';
      let styleClass = 'bg-zinc-900 border border-zinc-700 text-zinc-300 rounded px-3 py-2 text-center text-xs font-mono truncate shadow cursor-pointer hover:border-zinc-500 transition-all';
      
      if (isComponent) {
        category = 'component';
        styleClass = 'bg-purple-500/10 border-2 border-purple-500 text-purple-400 font-semibold rounded px-3 py-2 text-center text-xs font-mono shadow-lg shadow-purple-500/5 cursor-pointer hover:bg-purple-500/20 transition-all';
      } else if (directSet.has(id)) {
        category = 'direct';
        styleClass = 'bg-red-500/10 border-2 border-red-500 text-red-400 font-semibold rounded px-3 py-2 text-center text-xs font-mono shadow-lg shadow-red-500/5 cursor-pointer hover:bg-red-500/20 transition-all';
      } else if (indirectSet.has(id)) {
        category = 'indirect';
        styleClass = 'bg-yellow-500/10 border border-yellow-500 text-yellow-400 rounded px-3 py-2 text-center text-xs font-mono shadow cursor-pointer hover:bg-yellow-500/20 transition-all';
      }

      return {
        id,
        data: { label: cleanLabel, category, fullId: id },
        className: styleClass,
        type: 'default'
      };
    });

    // Build React Flow Edge objects
    const flowEdges = tempEdges.map((e, idx) => ({
      id: `edge-${idx}`,
      source: e.source,
      target: e.target,
      animated: !e.isDotted, // Animate direct propagation chains
      style: e.isDotted 
        ? { stroke: '#a855f7', strokeDasharray: '5,5', strokeWidth: 1.5 } // Purple dotted for component link
        : { stroke: '#ef4444', strokeWidth: 2 }, // Red solid for impact path
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 12,
        height: 12,
        color: e.isDotted ? '#a855f7' : '#ef4444',
      },
    }));

    // Apply Dagre auto-layout
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      flowNodes,
      flowEdges,
      'LR' // Left-to-Right flow fits propagation best
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
    setSelectedNode(null);
  }, [impactData, setNodes, setEdges]);

  // Handle node selection
  const onNodeClick = (_event: any, node: any) => {
    const id = node.id;
    const isComponent = id.startsWith('component-');
    
    // Calculate in-degree (dependents) and out-degree (dependencies) in this view
    const inDegree = edges.filter((e) => e.target === id).length;
    const outDegree = edges.filter((e) => e.source === id).length;

    let riskContribution: 'High' | 'Medium' | 'Low' = 'Low';
    if (node.data.category === 'direct') {
      riskContribution = outDegree > 2 ? 'High' : 'Medium';
    } else if (node.data.category === 'indirect') {
      riskContribution = 'Medium';
    }

    setSelectedNode({
      id,
      label: node.data.label,
      category: node.data.category,
      inDegree,
      outDegree,
      riskContribution
    });
  };

  const getRiskColors = (risk: string) => {
    const r = risk.toLowerCase();
    if (r === 'high') return { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400' };
    if (r === 'medium') return { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400' };
    return { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400' };
  };

  const riskStyle = getRiskColors(impactData.risk_level);

  return (
    <div className="flex flex-col lg:flex-row gap-6 items-start w-full">
      {/* Left Column: Risk Summary Panel */}
      <div className="w-full lg:w-80 shrink-0 space-y-4">
        <div className="border border-border bg-card/10 rounded-lg p-5 space-y-4">
          <div className="border-b border-border/40 pb-3 flex justify-between items-center">
            <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider font-mono">
              Risk Intelligence
            </span>
            <button 
              onClick={onReset}
              className="text-[10px] font-mono border border-border px-2 py-0.5 rounded text-text-muted hover:text-text hover:bg-card/20 transition-all"
            >
              Reset Scenario
            </button>
          </div>

          <div className="space-y-4 font-mono text-xs">
            {/* Risk Badge */}
            <div className={`border rounded p-4 flex flex-col gap-1.5 ${riskStyle.bg} ${riskStyle.border}`}>
              <div className="flex items-center gap-2">
                <AlertTriangle className={`h-4.5 w-4.5 ${riskStyle.text}`} />
                <span className={`text-sm font-bold uppercase ${riskStyle.text}`}>
                  {impactData.risk_level} RISK
                </span>
              </div>
              <span className="text-[10px] text-text-muted font-sans mt-0.5 leading-relaxed">
                Calculated risk of change propagation based on coupling and core components.
              </span>
            </div>

            {/* Analysis Confidence */}
            <div className="border border-border bg-canvas/30 rounded p-3.5 space-y-1">
              <span className="text-text-muted block text-[9px] uppercase tracking-wider">Analysis Confidence</span>
              <div className="text-base font-bold text-text flex items-baseline gap-1">
                <span>{impactData.confidence}%</span>
                <span className="text-[9px] text-text-muted font-normal font-sans">certainty score</span>
              </div>
            </div>

            {/* Total Affected count */}
            <div className="border border-border bg-canvas/30 rounded p-3.5 space-y-1">
              <span className="text-text-muted block text-[9px] uppercase tracking-wider">Estimated Impacted Files</span>
              <div className="text-base font-bold text-text">
                {impactData.estimated_file_count} files
              </div>
            </div>

            {/* Affected Components */}
            <div className="space-y-2 pt-1">
              <span className="text-[10px] text-text-muted uppercase tracking-wider font-bold block">Affected Components</span>
              <div className="flex flex-wrap gap-1.5">
                {impactData.affected_components.map((comp) => (
                  <span key={comp} className="bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded text-purple-400 text-[10px]">
                    {comp}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Technical Summary List */}
        <div className="border border-border bg-card/10 rounded-lg p-5 space-y-3 font-mono text-xs">
          <h4 className="text-[10px] text-text-muted uppercase font-bold tracking-wider">Propagation Overview</h4>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Directly affected:</span>
              <span className="text-red-400 font-semibold">{impactData.directly_affected_files.length}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Indirectly affected:</span>
              <span className="text-yellow-400 font-semibold">{impactData.indirectly_affected_files.length}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-text-muted">Chains analyzed:</span>
              <span className="text-text font-semibold">{impactData.dependency_paths.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: React Flow Graph & Detail drawer */}
      <div className="flex-grow w-full border border-border bg-card/5 rounded-lg flex flex-col h-[550px] relative overflow-hidden">
        {/* Graph Header / Legend */}
        <div className="p-3 border-b border-border bg-canvas/40 flex justify-between items-center gap-3 z-10 font-mono text-[10px] text-text-muted">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
            <span>Impact Propagation Graph</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500"></span>
              <span>Direct</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-yellow-500"></span>
              <span>Indirect</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-purple-500"></span>
              <span>Component</span>
            </div>
          </div>
        </div>

        {/* React Flow Area */}
        <div className="flex-grow h-full bg-canvas/10 relative flex">
          <div className="flex-grow h-full">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              minZoom={0.1}
              maxZoom={2}
            >
              <Controls showInteractive={false} />
              <MiniMap
                nodeColor={(node) => {
                  const cat = node.data?.category;
                  if (cat === 'direct') return '#ef4444';
                  if (cat === 'indirect') return '#eab308';
                  if (cat === 'component') return '#a855f7';
                  return '#27272a';
                }}
                maskColor="rgba(9, 9, 11, 0.7)"
                style={{ backgroundColor: '#09090b', border: '1px solid #27272a' }}
              />
              <Background color="#27272a" gap={16} />
            </ReactFlow>
          </div>

          {/* Node detail side panel */}
          {selectedNode && (
            <div className="absolute right-0 top-0 bottom-0 w-72 bg-zinc-950 border-l border-border p-4 z-10 flex flex-col justify-between shadow-2xl animate-in slide-in-from-right duration-200">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] font-bold text-primary uppercase tracking-wider font-mono">
                    Dependency Chain Explorer
                  </span>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-text-muted hover:text-text rounded p-0.5"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <div>
                    <span className="text-text-muted block text-[10px] uppercase">Node Identifier</span>
                    <span className="text-text font-semibold break-all text-xs block mt-0.5">{selectedNode.id}</span>
                  </div>

                  <div>
                    <span className="text-text-muted block text-[10px] uppercase">Impact Type</span>
                    <span className={`inline-block text-[9px] font-bold uppercase px-2 py-0.5 rounded border mt-1 ${
                      selectedNode.category === 'direct' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                      selectedNode.category === 'indirect' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400' :
                      selectedNode.category === 'component' ? 'bg-purple-500/10 border-purple-500/20 text-purple-400' :
                      'bg-zinc-800 border-zinc-700 text-zinc-300'
                    }`}>
                      {selectedNode.category}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div className="border border-border bg-canvas/30 rounded p-2">
                      <span className="text-text-muted block text-[8px] uppercase">Dependents</span>
                      <span className="text-text text-sm font-bold block mt-0.5">{selectedNode.inDegree}</span>
                    </div>
                    <div className="border border-border bg-canvas/30 rounded p-2">
                      <span className="text-text-muted block text-[8px] uppercase">Dependencies</span>
                      <span className="text-text text-sm font-bold block mt-0.5">{selectedNode.outDegree}</span>
                    </div>
                  </div>

                  <div>
                    <span className="text-text-muted block text-[10px] uppercase">Risk Contribution</span>
                    <span className={`inline-block text-[9px] font-bold uppercase px-2 py-0.5 rounded border mt-1 ${
                      selectedNode.riskContribution === 'High' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
                      selectedNode.riskContribution === 'Medium' ? 'bg-orange-500/10 border-orange-500/20 text-orange-400' :
                      'bg-zinc-800 border-zinc-700 text-zinc-400'
                    }`}>
                      {selectedNode.riskContribution}
                    </span>
                  </div>
                </div>
              </div>

              {/* Placeholders for Future Compatibility */}
              <div className="border-t border-border/40 pt-4 mt-4 space-y-2">
                <button
                  disabled
                  className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-1.5 rounded text-[11px] font-mono opacity-60 cursor-not-allowed"
                >
                  <span className="flex items-center gap-1.5">
                    <ExternalLink className="h-3 w-3" />
                    <span>Open File</span>
                  </span>
                  <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
                </button>
                <button
                  disabled
                  className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-1.5 rounded text-[11px] font-mono opacity-60 cursor-not-allowed"
                >
                  <span className="flex items-center gap-1.5">
                    <Layers className="h-3 w-3" />
                    <span>View Architecture</span>
                  </span>
                  <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
                </button>
                <button
                  disabled
                  className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-1.5 rounded text-[11px] font-mono opacity-60 cursor-not-allowed"
                >
                  <span className="flex items-center gap-1.5">
                    <MessageSquare className="h-3 w-3" />
                    <span>Ask About Impact</span>
                  </span>
                  <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
