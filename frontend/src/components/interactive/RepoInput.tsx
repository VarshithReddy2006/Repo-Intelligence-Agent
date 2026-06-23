import React, { useState, useEffect } from 'react';
import { Timeline } from './Timeline';
import type { TimelineStep } from './Timeline';
import { Terminal, ArrowRight, BookOpen, AlertCircle } from 'lucide-react';
import { apiUrl } from '../../lib/api';

interface ExampleRepo {
  name: string;
  url: string;
  tech_stack: string[];
  description: string;
}

const initialSteps: TimelineStep[] = [
  { id: 'cloning',              label: 'Cloning Repository',                    status: 'pending' },
  { id: 'detecting',            label: 'Detecting Languages',                    status: 'pending' },
  { id: 'parsing',              label: 'Parsing Source Files',                   status: 'pending' },
  { id: 'generating_embeddings', label: 'Generating Embeddings',                  status: 'pending' },
  { id: 'building_symbols',     label: 'Building Symbol Index',                  status: 'pending' },
  { id: 'building_dependency',  label: 'Building Dependency Graph',              status: 'pending' },
  { id: 'building_call',        label: 'Building Call Graph',                    status: 'pending' },
  { id: 'building_api',         label: 'Computing API Surface',                  status: 'pending' },
  { id: 'computing_intel',      label: 'Computing Repository Intelligence',      status: 'pending' },
  { id: 'generating_report',    label: 'Generating Report',                      status: 'pending' },
];

export const RepoInput: React.FC = () => {
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [examples, setExamples] = useState<ExampleRepo[]>([]);
  const [timelineSteps, setTimelineSteps] = useState<TimelineStep[]>(initialSteps);

  useEffect(() => {
    fetch(apiUrl('/api/repos/examples'))
      .then((res) => res.json())
      .then((data) => setExamples(data))
      .catch((err) => console.error(err));
  }, []);

  const handleAnalyze = async (repoUrl: string) => {
    if (!repoUrl.trim() || isAnalyzing) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setTimelineSteps([
      { ...initialSteps[0], status: 'active' },
      ...initialSteps.slice(1),
    ]);

    try {
      const response = await fetch(apiUrl('/api/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: repoUrl, branch: 'main' }),
      });

      if (!response.body) throw new Error('Stream not available');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        if (!value) continue;

        const lines = decoder.decode(value).split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));

            if (data.status === 'error') {
              const cleanMsg = (data.message || 'An error occurred during analysis.')
                .replace(/^[✗×x]\s*/i, '').trim();
              setErrorMessage(cleanMsg);
              setIsAnalyzing(false);
              reader.cancel().catch(() => {});
              return;
            }

            const activeStatus = data.status;
            
            // Advance steps in the timeline
            setTimelineSteps((prev) => {
              const currentIdx = prev.findIndex((s) => s.id === activeStatus);
              if (currentIdx !== -1) {
                return prev.map((s, idx) => {
                  if (idx < currentIdx) {
                    return { ...s, status: 'completed' as const };
                  } else if (idx === currentIdx) {
                    return { ...s, status: 'active' as const };
                  } else {
                    return { ...s, status: 'pending' as const };
                  }
                });
              } else if (activeStatus === 'cloned') {
                return prev.map((s) =>
                  s.id === 'cloning' ? { ...s, status: 'completed' as const } :
                  s.id === 'detecting' ? { ...s, status: 'active' as const } : s
                );
              } else if (activeStatus === 'detected') {
                return prev.map((s) =>
                  s.id === 'detecting' ? { ...s, status: 'completed' as const } :
                  s.id === 'parsing' ? { ...s, status: 'active' as const } : s
                );
              } else if (activeStatus === 'complete') {
                return prev.map((s) => ({ ...s, status: 'completed' as const }));
              }
              return prev;
            });

            if (data.status === 'done') {
              const repoPath = data.repo || data.repository
                || (data.owner && data.repo_name ? `${data.owner}/${data.repo_name}` : null);

              if (repoPath) {
                const [owner, repo] = repoPath.split('/');
                if (owner && repo) {
                  if (typeof window !== 'undefined') {
                    localStorage.setItem('activeRepo', repoPath);
                  }
                  window.location.href = `/analysis?owner=${owner}&repo=${repo}`;
                } else {
                  setErrorMessage('Invalid repo format received');
                  setIsAnalyzing(false);
                }
              } else {
                setErrorMessage('Missing repo in analysis result');
                setIsAnalyzing(false);
              }
            }
          } catch {/* ignore malformed SSE */}
        }
      }
    } catch (err) {
      console.error('Analysis stream interrupted', err);
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto w-full">
      {/* Input card */}
      <div className="card p-6 sm:p-8 shadow-card">
        <form
          onSubmit={(e) => { e.preventDefault(); handleAnalyze(url); }}
          className="flex flex-col sm:flex-row gap-3"
        >
          <label htmlFor="repo-url" className="sr-only">GitHub repository URL</label>
          <div className="relative flex-grow">
            <span className="absolute inset-y-0 left-3 flex items-center text-text-muted pointer-events-none">
              <Terminal className="h-4 w-4" aria-hidden="true" />
            </span>
            <input
              id="repo-url"
              type="url"
              required
              disabled={isAnalyzing}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="input pl-10 disabled:opacity-60"
            />
          </div>
          <button
            type="submit"
            disabled={isAnalyzing || !url.trim()}
            className="btn-primary px-6 py-3 text-sm shrink-0"
          >
            <span>Analyze Repository</span>
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </form>

        {isAnalyzing && (
          <div className="pt-5 mt-5 border-t border-border flex justify-center" role="status" aria-live="polite">
            <Timeline steps={timelineSteps} />
          </div>
        )}

        {errorMessage && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-3 bg-danger/10 border border-danger/30 text-danger rounded-lg p-4 font-sans text-xs"
          >
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="space-y-1">
              <span className="font-bold uppercase tracking-wider text-[10px] block">Analysis Failed</span>
              <p className="leading-relaxed">{errorMessage}</p>
              {(errorMessage.includes('quota') || errorMessage.includes('429') || errorMessage.includes('RESOURCE_EXHAUSTED') || errorMessage.includes('rate limit')) && (
                <p className="text-danger/70 text-[10px] mt-1">
                  AI provider rate limit reached. Please wait a moment before retrying.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Examples */}
      {!isAnalyzing && examples.length > 0 && (
        <div className="space-y-4 fade-up">
          <h2 className="text-xs uppercase tracking-widest font-semibold text-text-subtle font-mono">
            Try a sample repository
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {examples.map((repo) => (
              <button
                key={repo.name}
                type="button"
                onClick={() => { setUrl(repo.url); handleAnalyze(repo.url); }}
                className="card p-4 text-left transition-all hover:border-primary/40 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:shadow-ring space-y-3 group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-text font-semibold group-hover:text-primary transition-colors truncate">
                    {repo.name}
                  </span>
                  <BookOpen className="h-3.5 w-3.5 text-text-muted shrink-0" aria-hidden="true" />
                </div>
                <p className="text-xs text-text-muted line-clamp-2 leading-relaxed font-sans">
                  {repo.description}
                </p>
                <div className="flex flex-wrap gap-1">
                  {repo.tech_stack.map((stack) => (
                    <span key={stack} className="text-[9px] font-mono bg-canvas border border-border px-1.5 py-0.5 rounded text-text-muted">
                      {stack}
                    </span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RepoInput;
