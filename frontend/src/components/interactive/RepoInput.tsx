import React, { useState, useEffect } from 'react';
import { Timeline } from './Timeline';
import type { TimelineStep } from './Timeline';
import { Sparkles, Terminal, ArrowRight, BookOpen, AlertCircle } from 'lucide-react';
import { apiUrl } from '../../lib/api';

interface ExampleRepo {
  name: string;
  url: string;
  tech_stack: string[];
  description: string;
}

export const RepoInput: React.FC = () => {
  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [examples, setExamples] = useState<ExampleRepo[]>([]);
  const [timelineSteps, setTimelineSteps] = useState<TimelineStep[]>([
    { id: 'cloning', label: 'Clone repository from GitHub', status: 'pending' },
    { id: 'detecting', label: 'Detect languages and frameworks', status: 'pending' },
    { id: 'analyzing', label: 'Run architecture scanning & index codebase', status: 'pending' },
    { id: 'mapping', label: 'Map issue relationships & suggested reading order', status: 'pending' },
  ]);

  useEffect(() => {
    // Fetch example repos on mount
    fetch(apiUrl('/api/repos/examples'))
      .then(res => res.json())
      .then(data => setExamples(data))
      .catch(err => console.error(err));
  }, []);

  const handleAnalyze = async (repoUrl: string) => {
    if (!repoUrl.trim() || isAnalyzing) return;

    setIsAnalyzing(true);
    setErrorMessage(null);
    setTimelineSteps([
      { id: 'cloning', label: 'Clone repository from GitHub', status: 'active' },
      { id: 'detecting', label: 'Detect languages and frameworks', status: 'pending' },
      { id: 'analyzing', label: 'Run architecture scanning & index codebase', status: 'pending' },
      { id: 'mapping', label: 'Map issue relationships & suggested reading order', status: 'pending' },
    ]);

    try {
      const response = await fetch(apiUrl('/api/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: repoUrl,
          branch: 'main',
          model: 'Gemini 2.5 Flash'
        })
      });

      if (!response.body) throw new Error("Stream not available");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        if (value) {
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('SSE Event:', data);
                
                if (data.status === 'error') {
                  // Strip legacy "✗ " prefix if present
                  const rawMsg: string = data.message || 'An error occurred during analysis.';
                  const cleanMsg = rawMsg.replace(/^[✗×x]\s*/i, '').trim();
                  console.error('Analysis error from backend:', cleanMsg);
                  setErrorMessage(cleanMsg);
                  setIsAnalyzing(false);
                }

                // Update timeline status
                if (data.status === 'cloned') {
                  setTimelineSteps(prev => prev.map(s => s.id === 'cloning' ? { ...s, status: 'completed' as const } : s.id === 'detecting' ? { ...s, status: 'active' as const } : s));
                } else if (data.status === 'detected') {
                  setTimelineSteps(prev => prev.map(s => s.id === 'detecting' ? { ...s, status: 'completed' as const } : s.id === 'analyzing' ? { ...s, status: 'active' as const } : s));
                } else if (data.status === 'analyzed') {
                  setTimelineSteps(prev => prev.map(s => s.id === 'analyzing' ? { ...s, status: 'completed' as const } : s.id === 'mapping' ? { ...s, status: 'active' as const } : s));
                } else if (data.status === 'complete') {
                  setTimelineSteps(prev => prev.map(s => s.id === 'mapping' ? { ...s, status: 'completed' as const } : s));
                } else if (data.status === 'done') {
                  const repoPath = data.repo || data.repository || (data.owner && data.repo_name ? `${data.owner}/${data.repo_name}` : null);
                  
                  if (repoPath) {
                    const parts = repoPath.split('/')
                    if (parts.length === 2) {
                      const [owner, repo] = parts
                      window.location.href = `/analysis?owner=${owner}&repo=${repo}`
                    } else {
                      setErrorMessage('Invalid repo format received');
                      setIsAnalyzing(false);
                    }
                  } else {
                    setErrorMessage('Missing repo in analysis result');
                    setIsAnalyzing(false);
                  }
                }
              } catch (e) {
                // Ignore parsing issues
              }
            }
          }
        }
      }
    } catch (err) {
      console.error("Analysis stream interrupted", err);
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="space-y-12 max-w-3xl mx-auto w-full py-8">
      {/* Hero Header */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-text">
          Repo Intelligence <span className="text-primary">Agent</span>
        </h1>
        <p className="text-text-muted text-base sm:text-lg max-w-xl mx-auto font-mono">
          Understand any codebase in minutes.
        </p>
      </div>

      {/* URL Input Form */}
      <div className="bg-card/10 border border-border rounded-xl p-6 space-y-4 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAnalyze(url);
          }}
          className="flex flex-col sm:flex-row gap-3"
        >
          <div className="relative flex-grow">
            <span className="absolute inset-y-0 left-3 flex items-center text-text-muted">
              <Terminal className="h-4 w-4" />
            </span>
            <input
              type="url"
              required
              disabled={isAnalyzing}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="w-full bg-canvas border border-border rounded-lg pl-10 pr-3 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary text-text placeholder:text-text-muted/40 font-mono"
            />
          </div>
          <button
            type="submit"
            disabled={isAnalyzing || !url.trim()}
            className="bg-primary hover:bg-primary-hover text-text font-semibold px-6 py-3 rounded-lg flex items-center justify-center gap-2 text-sm transition-all shadow-md hover:shadow-primary/10 disabled:opacity-50"
          >
            <span>Analyze Repository</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {isAnalyzing && (
          <div className="pt-4 border-t border-border flex justify-center">
            <Timeline steps={timelineSteps} />
          </div>
        )}

        {errorMessage && (
          <div className="flex items-start gap-3 bg-red-500/5 border border-red-500/20 text-red-400 rounded-lg p-4 font-mono text-xs mt-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-bold uppercase tracking-wider text-[10px] block">Analysis Failed</span>
              <p className="leading-relaxed">{errorMessage}</p>
              {errorMessage.includes('quota') || errorMessage.includes('429') || errorMessage.includes('RESOURCE_EXHAUSTED') ? (
                <p className="text-red-300/70 text-[10px] mt-1">
                  Gemini API rate limit reached. Please wait a minute before retrying, or check your API quota at{' '}
                  <a href="https://ai.dev/rate-limit" target="_blank" rel="noopener noreferrer" className="underline">ai.dev/rate-limit</a>.
                </p>
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* Examples Grid */}
      {!isAnalyzing && examples.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xs uppercase tracking-wider font-semibold text-text-muted font-mono flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-primary" /> Example Repositories
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {examples.map((repo) => (
              <div
                key={repo.name}
                onClick={() => {
                  setUrl(repo.url);
                  handleAnalyze(repo.url);
                }}
                className="border border-border bg-card/20 hover:bg-border/20 p-4 rounded-lg cursor-pointer transition-colors space-y-3 group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-text font-semibold group-hover:text-primary transition-colors">
                    {repo.name}
                  </span>
                  <BookOpen className="h-3.5 w-3.5 text-text-muted" />
                </div>
                <p className="text-xs text-text-muted line-clamp-2 leading-relaxed">
                  {repo.description}
                </p>
                <div className="flex flex-wrap gap-1">
                  {repo.tech_stack.map((stack) => (
                    <span key={stack} className="text-[9px] font-mono bg-canvas border border-border px-1.5 py-0.5 rounded text-text-muted">
                      {stack}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default RepoInput;
