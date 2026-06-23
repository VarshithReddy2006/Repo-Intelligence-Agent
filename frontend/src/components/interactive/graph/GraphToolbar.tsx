import React, { useState } from 'react';
import {
  Maximize2,
  Network,
  ArrowRight,
  ArrowLeft,
  ArrowLeftRight,
  RotateCcw,
  Loader2,
  HelpCircle,
  Palette,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Crosshair,
} from 'lucide-react';
import type { GraphMode } from './types';

interface GraphToolbarProps {
  mode: GraphMode;
  traceDir: 'forward' | 'backward' | 'both';
  focusNode: string | null;
  loading: boolean;
  nodeCount: number;
  edgeCount: number;
  onFitView: () => void;
  onReset: () => void;
  onTraceForward: () => void;
  onTraceBackward: () => void;
  onTraceBoth: () => void;
  onNeighbors: () => void;
  onPanUp: () => void;
  onPanDown: () => void;
  onPanLeft: () => void;
  onPanRight: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onCenterGraph: () => void;
}

interface ToolButtonProps {
  onClick: () => void;
  active?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
  variant?: 'default' | 'danger';
}

const ToolButton: React.FC<ToolButtonProps> = ({
  onClick,
  active,
  disabled,
  title,
  children,
  variant = 'default',
}) => {
  const base =
    'flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[10px] font-mono font-semibold transition-all border';
  const inactive =
    'bg-canvas border-border text-text-muted hover:text-text hover:border-primary/50';
  const activeStyle =
    'bg-primary/10 border-primary text-primary';
  const dangerStyle =
    'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20';
  const disabledStyle = 'opacity-40 cursor-not-allowed';

  const cls = [
    base,
    disabled ? disabledStyle : variant === 'danger' ? dangerStyle : active ? activeStyle : inactive,
  ].join(' ');

  return (
    <button className={cls} onClick={onClick} disabled={disabled} title={title}>
      {children}
    </button>
  );
};
const NODE_LEGEND = [
  { label: 'Module',    color: '#5e6ad2' },
  { label: 'Service',   color: '#10b981' },
  { label: 'Utility',   color: '#f59e0b' },
  { label: 'Config',    color: '#9ca0a8' },
  { label: 'Test',      color: '#3b82f6' },
];

const SHORTCUTS = [
  { key: 'F',          desc: 'Fit view' },
  { key: 'R',          desc: 'Reset graph' },
  { key: 'Scroll',     desc: 'Zoom in / out' },
  { key: '↑ ↓ ← →',   desc: 'Pan canvas' },
  { key: 'Click node', desc: 'Select & inspect' },
];


export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  mode,
  traceDir,
  focusNode,
  loading,
  nodeCount,
  edgeCount,
  onFitView,
  onReset,
  onTraceForward,
  onTraceBackward,
  onTraceBoth,
  onNeighbors,
  onPanUp,
  onPanDown,
  onPanLeft,
  onPanRight,
  onZoomIn,
  onZoomOut,
  onCenterGraph,
}) => {
  const hasFocus = Boolean(focusNode);
  const focusLabel = focusNode
    ? focusNode.split('/').pop() ?? focusNode
    : null;
  const [showLegend,    setShowLegend]    = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);

  return (
    <div className="px-3 py-2 border-b border-border bg-canvas/40 flex flex-wrap items-center gap-2 z-10 relative">
      {/* Left — interaction mode buttons */}
      <div className="flex items-center gap-1.5">
        <ToolButton
          onClick={onNeighbors}
          active={mode === 'neighbors'}
          disabled={!hasFocus}
          title={hasFocus ? `Expand neighbours of ${focusNode}` : 'Click a node first'}
        >
          <Network className="h-3 w-3" />
          <span>Expand</span>
        </ToolButton>

        <ToolButton
          onClick={onTraceForward}
          active={mode === 'trace_fwd' && traceDir === 'forward'}
          disabled={!hasFocus}
          title={hasFocus ? `Trace forward deps of ${focusNode}` : 'Click a node first'}
        >
          <ArrowRight className="h-3 w-3" />
          <span>Deps →</span>
        </ToolButton>

        <ToolButton
          onClick={onTraceBackward}
          active={mode === 'trace_bwd' && traceDir === 'backward'}
          disabled={!hasFocus}
          title={hasFocus ? `Trace who imports ${focusNode}` : 'Click a node first'}
        >
          <ArrowLeft className="h-3 w-3" />
          <span>← Users</span>
        </ToolButton>

        <ToolButton
          onClick={onTraceBoth}
          active={mode === 'trace_fwd' && traceDir === 'both'}
          disabled={!hasFocus}
          title={hasFocus ? `Trace both directions from ${focusNode}` : 'Click a node first'}
        >
          <ArrowLeftRight className="h-3 w-3" />
          <span>Both</span>
        </ToolButton>
      </div>

      {/* Divider */}
      <div className="h-4 w-px bg-border" />

      {/* View controls */}
      <div className="flex items-center gap-1.5">
        <ToolButton onClick={onFitView} title="Fit all nodes in view">
          <Maximize2 className="h-3 w-3" />
          <span>Fit</span>
        </ToolButton>

        <ToolButton onClick={onReset} title="Reset to full graph" variant={mode !== 'full' ? 'danger' : 'default'}>
          <RotateCcw className="h-3 w-3" />
          <span>Reset</span>
        </ToolButton>
      </div>

      {/* Divider */}
      <div className="h-4 w-px bg-border" />

      {/* Viewport Pan/Zoom Controls */}
      <div className="flex items-center gap-1">
        <ToolButton onClick={onPanLeft} title="Move Left">
          <ChevronLeft className="h-3.5 w-3.5" />
        </ToolButton>
        <ToolButton onClick={onPanUp} title="Move Up">
          <ChevronUp className="h-3.5 w-3.5" />
        </ToolButton>
        <ToolButton onClick={onPanDown} title="Move Down">
          <ChevronDown className="h-3.5 w-3.5" />
        </ToolButton>
        <ToolButton onClick={onPanRight} title="Move Right">
          <ChevronRight className="h-3.5 w-3.5" />
        </ToolButton>
        
        <div className="w-1" />
        
        <ToolButton onClick={onZoomIn} title="Zoom In">
          <ZoomIn className="h-3.5 w-3.5" />
        </ToolButton>
        <ToolButton onClick={onZoomOut} title="Zoom Out">
          <ZoomOut className="h-3.5 w-3.5" />
        </ToolButton>
        <ToolButton onClick={onCenterGraph} title="Center Graph">
          <Crosshair className="h-3.5 w-3.5" />
        </ToolButton>
      </div>


      {/* Divider */}
      <div className="h-4 w-px bg-border" />

      {/* Legend + shortcuts */}
      <div className="flex items-center gap-1.5">
        <ToolButton onClick={() => setShowLegend(v => !v)} active={showLegend} title="Toggle node colour legend">
          <Palette className="h-3 w-3" />
          <span>Legend</span>
        </ToolButton>
        <ToolButton onClick={() => setShowShortcuts(v => !v)} active={showShortcuts} title="Keyboard shortcuts">
          <HelpCircle className="h-3 w-3" />
          <span>Keys</span>
        </ToolButton>
      </div>

      {/* Status / focus indicator */}
      <div className="flex items-center gap-2 ml-auto text-[10px] font-mono text-text-muted">
        {loading && (
          <span className="flex items-center gap-1 text-primary">
            <Loader2 className="h-3 w-3 animate-spin" />
            Loading…
          </span>
        )}

        {focusLabel && !loading && (
          <span className="flex items-center gap-1">
            <span className="text-primary">⬤</span>
            <span className="truncate max-w-[140px]" title={focusNode ?? ''}>
              {focusLabel}
            </span>
          </span>
        )}

        {!loading && (
          <span className="text-text-subtle">
            {nodeCount}n · {edgeCount}e
          </span>
        )}
      </div>

      {/* Legend dropdown */}
      {showLegend && (
        <div className="absolute top-full left-0 mt-1 z-20 bg-surface-1 border border-border rounded-lg p-3 min-w-[160px]" style={{boxShadow:'var(--shadow-raised)'}}>
          <p className="text-[9px] font-mono uppercase tracking-widest text-text-subtle mb-2">Node Categories</p>
          <dl className="space-y-1.5">
            {NODE_LEGEND.map(({ label, color }) => (
              <div key={label} className="flex items-center gap-2">
                <dt className="h-3 w-3 rounded-full shrink-0" style={{ background: color }} />
                <dd className="text-[11px] font-mono text-text-muted">{label}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Shortcuts dropdown */}
      {showShortcuts && (
        <div className="absolute top-full left-36 mt-1 z-20 bg-surface-1 border border-border rounded-lg p-3 min-w-[210px]" style={{boxShadow:'var(--shadow-raised)'}}>
          <p className="text-[9px] font-mono uppercase tracking-widest text-text-subtle mb-2">Keyboard Shortcuts</p>
          <dl className="space-y-1.5">
            {SHORTCUTS.map(({ key, desc }) => (
              <div key={key} className="flex items-center justify-between gap-4">
                <dt className="text-[11px] font-mono text-primary bg-primary/10 border border-primary/20 px-1.5 py-0.5 rounded shrink-0">{key}</dt>
                <dd className="text-[11px] font-mono text-text-muted">{desc}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
};
