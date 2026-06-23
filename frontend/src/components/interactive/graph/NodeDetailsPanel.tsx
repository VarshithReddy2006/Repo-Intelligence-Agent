import React from 'react';
import { X, Network, ArrowRight, ArrowLeft, ArrowLeftRight } from 'lucide-react';
import { CATEGORY_COLORS, CATEGORY_LABELS } from './types';
import type { GraphNode } from './types';

interface NodeDetailsPanelProps {
  node: GraphNode;
  onClose: () => void;
  onExpand: (nodeId: string) => void;
  onTraceForward: (nodeId: string) => void;
  onTraceBackward: (nodeId: string) => void;
  onTraceBoth: (nodeId: string) => void;
  className?: string;
}

interface ActionButtonProps {
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  description: string;
}

const ActionButton: React.FC<ActionButtonProps> = ({ onClick, icon, label, description }) => (
  <button
    onClick={onClick}
    className="w-full flex items-center gap-2.5 bg-canvas border border-border hover:border-primary/50 hover:bg-primary/5 px-3 py-2 rounded text-xs font-mono transition-all text-left group"
  >
    <span className="text-primary shrink-0">{icon}</span>
    <span className="flex flex-col min-w-0">
      <span className="text-text font-semibold text-[11px]">{label}</span>
      <span className="text-text-muted text-[9px] truncate">{description}</span>
    </span>
  </button>
);

/**
 * Right-side drawer panel showing metadata for a selected graph node.
 * Includes action buttons to drive expand/trace operations.
 */
export const NodeDetailsPanel: React.FC<NodeDetailsPanelProps> = ({
  node,
  onClose,
  onExpand,
  onTraceForward,
  onTraceBackward,
  onTraceBoth,
  className,
}) => {
  const color = CATEGORY_COLORS[node.category] ?? CATEGORY_COLORS.regular;
  const categoryLabel = CATEGORY_LABELS[node.category] ?? node.category;
  const fileName = node.id.split('/').pop() ?? node.id;
  const dirPath = node.id.includes('/')
    ? node.id.substring(0, node.id.lastIndexOf('/'))
    : '';

  const positionClass = className ??
    'fixed inset-x-0 bottom-0 max-h-[60vh] md:absolute md:right-0 md:top-0 md:bottom-0 md:max-h-none md:w-72';

  return (
    <div
      role="dialog"
      aria-label={`Node details: ${fileName}`}
      className={`${positionClass} bg-surface-2 border-t md:border-t-0 md:border-l border-border flex flex-col z-20 shadow-2xl`}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-4 pb-3 border-b border-border/60 shrink-0">
        <div className="space-y-0.5 min-w-0 pr-2">
          <span className="text-[9px] font-bold text-primary uppercase tracking-wider font-mono block">
            Node Details
          </span>
          <h3
            className="text-xs font-mono font-semibold text-text truncate block"
            title={node.id}
          >
            {fileName}
          </h3>
          {dirPath && (
            <span className="text-[9px] text-text-muted font-mono truncate block" title={dirPath}>
              {dirPath}/
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close node details"
          className="text-text-muted hover:text-text shrink-0 rounded p-0.5 mt-0.5 focus-visible:outline-none focus-visible:shadow-ring"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* Metadata */}
      <div className="px-4 py-3 space-y-3 font-mono text-xs flex-grow overflow-y-auto">
        {/* Full path */}
        <div>
          <span className="text-[9px] text-text-muted uppercase block mb-0.5">Full Path</span>
          <span className="text-text break-all text-[10px] leading-relaxed block bg-canvas/30 border border-border/50 rounded p-1.5">
            {node.id}
          </span>
        </div>

        {/* Category */}
        <div>
          <span className="text-[9px] text-text-muted uppercase block mb-1">Category</span>
          <span
            className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase px-2 py-0.5 rounded border"
            style={{
              color,
              borderColor: `${color}40`,
              backgroundColor: `${color}15`,
            }}
          >
            <span
              className="h-1.5 w-1.5 rounded-full shrink-0"
              style={{ backgroundColor: color }}
            />
            {categoryLabel}
          </span>
        </div>

        {/* Language */}
        {node.language && node.language !== 'unknown' && (
          <div>
            <span className="text-[9px] text-text-muted uppercase block mb-1">Language</span>
            <span className="text-text text-[10px] bg-canvas border border-border px-2 py-0.5 rounded">
              {node.language}
            </span>
          </div>
        )}

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <div className="border border-border bg-canvas/30 rounded p-2">
            <span className="text-[9px] text-text-muted uppercase block">Degree</span>
            <span className="text-text text-sm font-bold block mt-0.5">{node.degree}</span>
          </div>
          <div className="border border-border bg-canvas/30 rounded p-2">
            <span className="text-[9px] text-text-muted uppercase block">Centrality</span>
            <span className="text-text text-sm font-bold block mt-0.5">
              {node.centrality.toFixed(3)}
            </span>
          </div>
        </div>

        {/* Divider */}
        <div className="border-t border-border/40 pt-3">
          <span className="text-[9px] text-text-muted uppercase font-bold tracking-wider block mb-2">
            Actions
          </span>
          <div className="space-y-1.5">
            <ActionButton
              onClick={() => onExpand(node.id)}
              icon={<Network className="h-3.5 w-3.5" />}
              label="Expand Neighbours"
              description="Show direct imports and importers"
            />
            <ActionButton
              onClick={() => onTraceForward(node.id)}
              icon={<ArrowRight className="h-3.5 w-3.5" />}
              label="Trace Dependencies →"
              description="Files this node depends on"
            />
            <ActionButton
              onClick={() => onTraceBackward(node.id)}
              icon={<ArrowLeft className="h-3.5 w-3.5" />}
              label="← Trace Consumers"
              description="Files that import this node"
            />
            <ActionButton
              onClick={() => onTraceBoth(node.id)}
              icon={<ArrowLeftRight className="h-3.5 w-3.5" />}
              label="Trace Both Directions"
              description="Full dependency tree"
            />
          </div>
        </div>
      </div>

      {/* Legend footer */}
      <div className="px-4 py-3 border-t border-border/40 shrink-0">
        <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider block mb-1.5">
          Legend
        </span>
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[9px] font-mono text-text-muted">
          {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
            <span key={key} className="flex items-center gap-1">
              <span
                className="h-1.5 w-1.5 rounded-full shrink-0"
                style={{ backgroundColor: CATEGORY_COLORS[key] }}
              />
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
