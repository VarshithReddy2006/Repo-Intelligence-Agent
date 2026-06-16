import React from 'react';
import { CheckCircle2, CircleDashed, Hourglass } from 'lucide-react';

export interface TimelineStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed';
}

interface TimelineProps {
  steps: TimelineStep[];
}

export const Timeline: React.FC<TimelineProps> = ({ steps }) => {
  return (
    <div className="border border-border bg-card/50 rounded-lg p-4 font-mono text-xs w-full max-w-md">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-border">
        <span className="text-text-muted font-semibold uppercase tracking-wider">Agent Execution Timeline</span>
        <span className="text-primary font-bold">ACTIVE</span>
      </div>
      
      <div className="space-y-3">
        {steps.map((step) => {
          let Icon = Hourglass;
          let colorClass = 'text-text-muted';
          let borderClass = 'border-border';
          
          if (step.status === 'completed') {
            Icon = CheckCircle2;
            colorClass = 'text-emerald-500';
            borderClass = 'border-emerald-500/20 bg-emerald-500/5';
          } else if (step.status === 'active') {
            Icon = CircleDashed;
            colorClass = 'text-primary';
            borderClass = 'border-primary/30 bg-primary/5';
          }

          return (
            <div
              key={step.id}
              className={`flex items-center justify-between p-2 rounded-md border ${borderClass} transition-all duration-300`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`h-4 w-4 ${step.status === 'active' ? 'animate-spin' : ''} ${colorClass}`} />
                <span className={step.status === 'completed' ? 'text-text line-through opacity-70' : 'text-text'}>
                  {step.label}
                </span>
              </div>
              
              <span className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded ${
                step.status === 'completed' 
                  ? 'bg-emerald-500/10 text-emerald-500' 
                  : step.status === 'active' 
                  ? 'bg-primary/10 text-primary' 
                  : 'bg-border text-text-muted'
              }`}>
                {step.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Timeline;
