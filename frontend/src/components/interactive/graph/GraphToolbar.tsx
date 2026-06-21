import React from 'react';
import {
  Maximize2,
  Network,
  ArrowRight,
  ArrowLeft,
  ArrowLeftRight,
  RotateCcw,
  Loader2,
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
}) => {
  const hasFocus = Boolean(focusNode);
  const focusLabel = focusNode
    ? focusNode.split('/').pop() ?? focusNode
    : null;

  return (
    <div className="px-3 py-2 border-b border-border bg-canvas/40 flex flex-wrap items-center gap-2 z-10">
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
          <span className="text-zinc-600">
            {nodeCount}n · {edgeCount}e
          </span>
        )}
      </div>
    </div>
  );
};
