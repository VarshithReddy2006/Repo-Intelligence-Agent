import React, { useState } from 'react';
import { Target, FileSpreadsheet, ListTodo, Wrench, AlertTriangle, Loader2 } from 'lucide-react';

interface Step {
  step_number: number;
  description: string;
  files_to_modify: string[];
}

interface Plan {
  issue_summary: string;
  relevant_files: string[];
  steps: Step[];
}

export const IssueMapper: React.FC = () => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [completedSteps, setCompletedSteps] = useState<Record<number, boolean>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/issues/map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo: "current/workspace",
          title,
          description
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPlan(data);
        setCompletedSteps({});
      }
    } catch (err) {
      console.error("Failed to map issue", err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleStep = (stepNum: number) => {
    setCompletedSteps(prev => ({
      ...prev,
      [stepNum]: !prev[stepNum]
    }));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full items-start">
      {/* Input Panel */}
      <div className="lg:col-span-5 border border-border bg-card/10 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4 border-b border-border pb-3">
          <Target className="h-5 w-5 text-primary" />
          <h2 className="text-sm font-semibold tracking-wide uppercase font-mono">Issue Specification</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
              Issue Title / URL
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Fix memory leaks in SQLite store"
              className="w-full bg-canvas border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary text-text placeholder:text-text-muted/40 font-sans"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-muted uppercase tracking-wider mb-1.5 font-mono">
              Issue Description / Error Logs
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste terminal logs, error stacktrace, or detailed requirements..."
              rows={6}
              className="w-full bg-canvas border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary text-text placeholder:text-text-muted/40 font-sans resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading || !title.trim()}
            className="w-full bg-primary hover:bg-primary-hover text-text font-semibold py-2 rounded text-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Mapping Issue Relationships...</span>
              </>
            ) : (
              <span>Map Issue & Generate Plan</span>
            )}
          </button>
        </form>
      </div>

      {/* Output Panel */}
      <div className="lg:col-span-7 border border-border bg-card/10 rounded-lg p-5 min-h-[400px] flex flex-col">
        {plan ? (
          <div className="space-y-5">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <ListTodo className="h-5 w-5 text-primary" />
                <h2 className="text-sm font-semibold tracking-wide uppercase font-mono">Analysis Results</h2>
              </div>
              <span className="text-[10px] font-mono bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 px-2.5 py-0.5 rounded">
                COMPLETED
              </span>
            </div>

            {/* Impact Files list */}
            <div>
              <h3 className="text-xs font-semibold text-text uppercase tracking-wider mb-2 font-mono flex items-center gap-1.5">
                <FileSpreadsheet className="h-4 w-4 text-primary" /> Target Files (Impact Analysis)
              </h3>
              <div className="bg-card/40 border border-border rounded p-3 space-y-2">
                {plan.relevant_files.map((file) => (
                  <div key={file} className="flex items-center gap-2 font-mono text-xs text-text-muted bg-canvas/40 px-2 py-1.5 rounded border border-border/50">
                    <span className="h-1.5 w-1.5 rounded-full bg-primary"></span>
                    <span>{file}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Steps Timeline */}
            <div>
              <h3 className="text-xs font-semibold text-text uppercase tracking-wider mb-3 font-mono flex items-center gap-1.5">
                <Wrench className="h-4 w-4 text-primary" /> Implementation Plan Steps
              </h3>
              <div className="space-y-3">
                {plan.steps.map((step) => {
                  const isDone = completedSteps[step.step_number];

                  return (
                    <div
                      key={step.step_number}
                      onClick={() => toggleStep(step.step_number)}
                      className={`border rounded p-3.5 cursor-pointer transition-all duration-300 ${
                        isDone
                          ? 'bg-emerald-500/5 border-emerald-500/20 opacity-70'
                          : 'bg-card/30 border-border hover:border-primary/50'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          checked={!!isDone}
                          onChange={() => {}} // toggled by parent div click
                          className="mt-1 h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary focus:ring-offset-0 accent-primary"
                        />
                        <div className="space-y-2">
                          <p className={`text-xs font-medium ${isDone ? 'line-through text-text-muted' : 'text-text'}`}>
                            <span className="font-mono text-primary font-bold mr-1">Step {step.step_number}:</span>
                            {step.description}
                          </p>
                          
                          <div className="flex flex-wrap gap-1.5">
                            {step.files_to_modify.map((f) => (
                              <span key={f} className="text-[10px] font-mono bg-canvas border border-border px-1.5 py-0.5 rounded text-text-muted">
                                {f}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-grow flex flex-col items-center justify-center text-center p-8 opacity-65">
            <AlertTriangle className="h-8 w-8 text-text-muted mb-2" />
            <p className="text-sm font-semibold text-text mb-1">No plan generated</p>
            <p className="text-xs text-text-muted max-w-sm">
              Enter an issue description and trigger mapping to calculate relevant codebase components and tasks.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default IssueMapper;
