import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';
import type { HealthStatus } from './usePrerequisites';

interface Props {
  activeRepo: string;
  healthStatus: HealthStatus;
  onRepair: () => void;
  isRepairing: boolean;
}

/**
 * Warning banner shown when the active repo is missing index/graph/symbol prerequisites.
 * Mounts the Rebuild button only when symbol_index is the missing piece.
 */
export const PrerequisitesBanner: React.FC<Props> = ({
  activeRepo, healthStatus, onRepair, isRepairing,
}) => {
  const message = !healthStatus.analysis_exists
    ? `Repository '${activeRepo}' has not been analyzed yet. Go to Repository Analysis to run the initial analysis.`
    : !healthStatus.graph_available
    ? `Repository '${activeRepo}' analyzed but dependency graph is missing. Re-run Architecture Build.`
    : `Repository '${activeRepo}' analyzed but symbol index is missing. Re-run Architecture Build or click rebuild below.`;

  return (
    <div className="flex flex-col gap-2 bg-warn/10 border border-warn/30 rounded-lg p-4 text-sm text-warn font-sans">
      <div className="flex gap-2.5 items-start">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-1">
          <span className="font-bold uppercase tracking-wider text-[10px] block">
            Repository Prerequisite Validation
          </span>
          <p className="leading-relaxed">{message}</p>
        </div>
      </div>
      {healthStatus.analysis_exists && !healthStatus.symbol_index_available && (
        <button
          type="button"
          onClick={onRepair}
          disabled={isRepairing}
          className="mt-2 self-start text-primary hover:text-primary-hover font-semibold text-xs
                     flex items-center gap-1.5 bg-primary/10 hover:bg-primary/20
                     border border-primary/30 px-3 py-1.5 rounded transition-all
                     focus-visible:outline-none focus-visible:shadow-ring
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isRepairing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
              Rebuilding Symbol Index...
            </>
          ) : 'Rebuild Symbol Index'}
        </button>
      )}
    </div>
  );
};

export default PrerequisitesBanner;
