import React, { useState, useEffect, useRef } from 'react';
import { CheckCircle2, CircleDashed, Hourglass, Terminal } from 'lucide-react';

export interface TimelineStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed';
}

interface TimelineProps {
  steps: TimelineStep[];
}

interface Stage {
  id: string;
  label: string;
  steps: string[];
  status: 'pending' | 'active' | 'completed';
}

const STAGES: Stage[] = [
  { id: 'repo', label: 'Repository', steps: ['detecting'], status: 'pending' },
  { id: 'clone', label: 'Clone', steps: ['cloning'], status: 'pending' },
  { id: 'parse', label: 'Parse Files', steps: ['parsing'], status: 'pending' },
  { id: 'symbols', label: 'Symbols', steps: ['building_symbols', 'building_dependency', 'building_call', 'building_api'], status: 'pending' },
  { id: 'architecture', label: 'Architecture', steps: ['computing_intel'], status: 'pending' },
  { id: 'vector', label: 'Vector Index', steps: ['generating_embeddings'], status: 'pending' },
  { id: 'report', label: 'Report', steps: ['generating_report'], status: 'pending' },
];

const typicalDurations: Record<string, number> = {
  repo: 1.0,
  clone: 3.5,
  parse: 4.0,
  symbols: 6.0,
  architecture: 4.0,
  vector: 7.0,
  report: 2.5,
};

export const Timeline: React.FC<TimelineProps> = ({ steps }) => {
  const [now, setNow] = useState(Date.now());
  const startTimesRef = useRef<Record<string, number>>({});
  const endTimesRef = useRef<Record<string, number>>({});
  const overallStart = useRef(Date.now());

  // Map 10 backend steps to 7 stages
  const mappedStages = STAGES.map((stage) => {
    const stepStatuses = stage.steps.map((stepId) => {
      const found = steps.find((s) => s.id === stepId);
      return found ? found.status : 'pending';
    });

    let status: 'pending' | 'active' | 'completed' = 'pending';
    if (stepStatuses.every((s) => s === 'completed')) {
      status = 'completed';
    } else if (stepStatuses.some((s) => s === 'active')) {
      status = 'active';
    } else if (stepStatuses.some((s) => s === 'completed')) {
      // Partially completed step within a multi-step stage
      status = 'active';
    }

    // Special fallback: if previous stages are pending but we are already active on this one,
    // ensure logical state.
    return { ...stage, status };
  });

  // Align start/end times whenever steps status updates
  useEffect(() => {
    mappedStages.forEach((stage) => {
      if (stage.status === 'active' && !startTimesRef.current[stage.id]) {
        startTimesRef.current[stage.id] = Date.now();
      }
      if (stage.status === 'completed') {
        if (!startTimesRef.current[stage.id]) {
          startTimesRef.current[stage.id] = Date.now() - 1000; // fallback default
        }
        if (!endTimesRef.current[stage.id]) {
          endTimesRef.current[stage.id] = Date.now();
        }
      }
    });
  }, [steps]);

  // High-accuracy live timer ticks
  useEffect(() => {
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Compute live stage elapsed times
  const getStageDuration = (stage: typeof mappedStages[0]) => {
    if (stage.status === 'completed') {
      const start = startTimesRef.current[stage.id] || overallStart.current;
      const end = endTimesRef.current[stage.id] || now;
      return (end - start) / 1000;
    }
    if (stage.status === 'active') {
      const start = startTimesRef.current[stage.id] || now;
      return (now - start) / 1000;
    }
    return 0;
  };

  // Estimate remaining time
  let estRemaining = 0;
  mappedStages.forEach((stage) => {
    if (stage.status === 'pending') {
      estRemaining += typicalDurations[stage.id];
    } else if (stage.status === 'active') {
      const elapsed = getStageDuration(stage);
      const remainingForThisStage = Math.max(0.2, typicalDurations[stage.id] - elapsed);
      estRemaining += remainingForThisStage;
    }
  });

  const overallElapsed = (now - overallStart.current) / 1000;
  const isFinished = mappedStages.every((s) => s.status === 'completed');

  // Helper to generate the text progress bar (e.g. ████████░░)
  const getBlockBar = (status: 'pending' | 'active' | 'completed', stageId: string) => {
    let progress = 0;
    if (status === 'completed') {
      progress = 100;
    } else if (status === 'active') {
      if (stageId === 'symbols') {
        // Multi-step progress calculation
        const subSteps = STAGES.find(s => s.id === stageId)?.steps || [];
        const completedCount = subSteps.filter(id => steps.find(s => s.id === id)?.status === 'completed').length;
        progress = Math.min(90, Math.round((completedCount / subSteps.length) * 100) + 15);
      } else {
        // Standard single-step active progress
        const elapsed = (now - (startTimesRef.current[stageId] || now)) / 1000;
        const expected = typicalDurations[stageId];
        progress = Math.min(90, Math.round((elapsed / expected) * 70));
      }
    }
    
    const totalBlocks = 10;
    const filledBlocks = Math.round((progress / 100) * totalBlocks);
    const emptyBlocks = totalBlocks - filledBlocks;
    return '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);
  };

  return (
    <div className="border border-border bg-card/60 rounded-xl p-5 shadow-float font-mono text-xs w-full max-w-md fade-up">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border/80 select-none">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-primary animate-pulse" />
          <span className="text-text font-bold uppercase tracking-wider">Analysis Engine</span>
        </div>
        <div className="flex items-center gap-3 text-[10px] text-text-muted">
          <span>Elapsed: <span className="text-text font-semibold">{overallElapsed.toFixed(1)}s</span></span>
          {!isFinished && estRemaining > 0 && (
            <span>Est. left: <span className="text-primary font-semibold">~{Math.ceil(estRemaining)}s</span></span>
          )}
        </div>
      </div>

      <div className="space-y-2.5">
        {mappedStages.map((stage) => {
          const duration = getStageDuration(stage);
          const blockBar = getBlockBar(stage.status, stage.id);
          
          let statusText = '';
          let iconColor = 'text-text-subtle';
          let barColor = 'text-border';
          let rowBg = 'border-transparent';
          let Icon = Hourglass;

          if (stage.status === 'completed') {
            Icon = CheckCircle2;
            iconColor = 'text-success';
            barColor = 'text-success/30';
            statusText = `${duration.toFixed(1)}s`;
          } else if (stage.status === 'active') {
            Icon = CircleDashed;
            iconColor = 'text-primary animate-spin';
            barColor = 'text-primary/70';
            rowBg = 'border-primary/20 bg-primary/5';
            statusText = `${duration.toFixed(1)}s`;
          } else {
            statusText = 'pending';
          }

          return (
            <div
              key={stage.id}
              className={`flex items-center justify-between p-2.5 rounded-lg border ${rowBg} transition-all duration-300`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`h-4 w-4 shrink-0 ${iconColor}`} />
                <span className={stage.status === 'completed' ? 'text-text-muted line-through opacity-60' : 'text-text font-medium'}>
                  {stage.label}
                </span>
              </div>

              <div className="flex items-center gap-4">
                <span className={`text-xs select-none tracking-wider ${barColor}`}>
                  {blockBar}
                </span>
                <span className={`text-[10px] font-bold uppercase w-12 text-right ${
                  stage.status === 'completed'
                    ? 'text-success'
                    : stage.status === 'active'
                    ? 'text-primary'
                    : 'text-text-subtle'
                }`}>
                  {statusText}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Timeline;
