import React from 'react';
import { Settings, ShieldCheck, ShieldAlert } from 'lucide-react';
import type { HealthStatus } from './usePrerequisites';

interface Props {
  title?: string;
  healthStatus: HealthStatus | null;
  description?: string;
  showSymbolIndex?: boolean;
}

/**
 * Shared diagnostics panel — used by PR Intelligence and Architecture Drift.
 */
export const DiagnosticsPanel: React.FC<Props> = ({
  title = 'Diagnostics & Status',
  healthStatus,
  description,
  showSymbolIndex = true,
}) => (
  <div className="card-padded flex flex-col gap-4">
    <div className="flex items-center gap-2.5">
      <Settings className="w-5 h-5 text-primary" aria-hidden="true" />
      <h3 className="text-base font-semibold text-text">{title}</h3>
    </div>

    <dl className="flex flex-col gap-3 text-sm">
      <Row label="GitHub Token Status">
        {healthStatus?.github_token ? (
          <span className="badge-success">
            <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" /> Active
          </span>
        ) : (
          <span className="badge-danger">
            <ShieldAlert className="w-3.5 h-3.5" aria-hidden="true" /> Inactive
          </span>
        )}
      </Row>

      <Row label="GitHub Rate Limit">
        <span className="text-text font-mono text-xs">
          {healthStatus?.rate_limit_remaining ?? '—'} left
        </span>
      </Row>

      <Row label="Dependency Graph">
        {healthStatus?.graph_available
          ? <span className="badge-success">Available</span>
          : <span className="badge-neutral">Unavailable</span>}
      </Row>

      {showSymbolIndex && (
        <Row label="Symbol Index">
          {healthStatus?.symbol_index_available
            ? <span className="badge-success">Available</span>
            : <span className="badge-neutral">Unavailable</span>}
        </Row>
      )}
    </dl>

    {description && (
      <p className="text-xs text-text-subtle leading-relaxed font-sans">
        {description}
      </p>
    )}
  </div>
);

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex justify-between items-center py-1.5 border-b border-border/60 last:border-b-0">
    <dt className="text-text-muted font-medium text-xs">{label}</dt>
    <dd>{children}</dd>
  </div>
);

export default DiagnosticsPanel;
