import React, { useState, useEffect } from 'react';
import { apiUrl } from '../../lib/api';
import FileTree from './FileTree';
import IssueMapper from './IssueMapper';
import ChatInterface from './ChatInterface';
import { ArchitectureGraph } from './ArchitectureGraph';
import { ReadingOrderTimeline } from './ReadingOrderTimeline';
import { ImpactAnalysisGraph } from './ImpactAnalysisGraph';
import { Layers, Box, Code2, BookOpen, Cpu, Info, CheckCircle2, Target, HelpCircle, MessageSquareCode } from 'lucide-react';

interface ComponentRelationship {
  source: string;
  target: string;
  relationship_type: string;
  description: string;
}

interface AnalysisData {
  analysis: {
    structure: Record<string, string[]>;
    dependencies: string[];
    tech_stack: string[];
    metadata: Record<string, string>;
  };
  architecture: {
    summary: string;
    reading_order: string[];
    relationships: ComponentRelationship[];
  };
}

interface DashboardProps {
  repoParam?: string;
}

export const AnalysisDashboard: React.FC<DashboardProps> = ({ repoParam }) => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'analysis' | 'graph' | 'reading_path' | 'impact_analysis' | 'issues' | 'chat'>('analysis');

  // Impact Analysis states
  const [impactData, setImpactData] = useState<any | null>(null);
  const [impactLoading, setImpactLoading] = useState<boolean>(false);
  const [issueInput, setIssueInput] = useState<string>('');
  const [impactError, setImpactError] = useState<string | null>(null);

  // Decode route parameter (e.g., owner-repo to owner/repo) or fetch from query param
  const getRepoName = () => {
    if (repoParam) {
      return repoParam.replace('-', '/');
    }
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const owner = urlParams.get('owner');
      const repo = urlParams.get('repo');
      if (owner && repo) {
        console.log('Parsed owner:', owner, 'repo:', repo);
        return `${owner}/${repo}`;
      }
      const repoQuery = urlParams.get('repo');
      if (repoQuery) {
        console.log('Fallback repo query param:', repoQuery);
        return repoQuery;
      }
    }
    console.warn('Repo name not found in URL');
    return 'unknown/repo';
  };

  const repoName = getRepoName();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const [owner, name] = repoName.split('/');
    if (!owner || !name || owner === 'unknown' || name === 'repo') {
      const msg = 'Repository information missing or invalid. Redirecting to home.';
      console.error(msg);
      setErrorMessage(msg);
      // Redirect after short delay
      setTimeout(() => (window.location.href = '/'), 2000);
      setLoading(false);
      return;
    }
    if (typeof window !== 'undefined') {
      localStorage.setItem('activeRepo', repoName);
    }
    const apiUrlFull = apiUrl(`/api/analysis/${owner}/${name}`);
    console.log('Fetching analysis from', apiUrlFull);
    fetch(apiUrlFull)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch repository details');
        return res.json();
      })
      .then((resData) => {
        setData(resData);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setErrorMessage(err.message);
        setLoading(false);
      });
  }, [repoName]);

  const handleRunImpactAnalysis = (overrideText?: string) => {
    const queryText = overrideText !== undefined ? overrideText : issueInput;
    if (!queryText.trim()) return;

    setImpactLoading(true);
    setImpactError(null);

    if (overrideText !== undefined) {
      setIssueInput(overrideText);
    }

    fetch(apiUrl('/api/impact-analysis'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo: repoName, issue: queryText })
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to analyze impact");
        return res.json();
      })
      .then((resData) => {
        setImpactData(resData);
        setImpactLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setImpactError(err.message || 'Failed to complete impact analysis.');
        setImpactLoading(false);
      });
  };



  if (loading) {
    return (
      <div className="flex-grow flex flex-col items-center justify-center py-24 font-mono text-xs text-text-muted gap-3">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span>Retrieving repository analysis logs...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex-grow flex flex-col items-center justify-center py-24 font-mono text-xs text-text-muted gap-3">
        <Info className="h-6 w-6 text-primary" />
        <span>Failed to load repository metadata. Make sure python API server is running on port 8000/8001.</span>
      </div>
    );
  }

  const { analysis, architecture } = data;

  return (
    <div className="space-y-6 w-full py-4">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-border pb-4 gap-4">
        <div>
          <h1 className="text-xl font-semibold text-text flex items-center gap-2 font-mono">
            <Layers className="h-5 w-5 text-primary" />
            <span>{repoName}</span>
          </h1>
          <p className="text-xs text-text-muted mt-1 font-sans">
            Indexed Codebase Comprehension Board
          </p>
        </div>

        <div className="flex items-center gap-2 bg-emerald-500/5 border border-emerald-500/20 px-3 py-1 rounded-md text-xs font-mono text-emerald-500">
          <CheckCircle2 className="h-4 w-4" />
          <span>INDEXED & SECURED</span>
        </div>
      </div>

      {/* Main Content Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left explorer Column */}
        <div className="lg:col-span-4 space-y-4">
          <FileTree
            structure={analysis.structure}
            onFileSelect={(path) => setSelectedFile(path)}
          />
          {selectedFile && (
            <div className="border border-border bg-card/10 rounded-lg p-4 font-mono text-xs space-y-2">
              <span className="text-primary font-bold uppercase tracking-wider block text-[10px]">Selected Node Context</span>
              <p className="text-text break-all">{selectedFile}</p>
              <p className="text-text-muted">Pass this file context to the Issue Mapper or Chat tab to discuss implementation plans.</p>
            </div>
          )}
        </div>

        {/* Right workspace Column */}
        <div className="lg:col-span-8 space-y-6">
          {/* Tab Selection */}
          <div className="flex flex-wrap border-b border-border">
            <button
              onClick={() => setActiveTab('analysis')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'analysis'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <Layers className="h-4 w-4" />
              <span>CODEBASE ANALYSIS</span>
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'graph'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <Code2 className="h-4 w-4" />
              <span>ARCHITECTURE GRAPH</span>
            </button>
            <button
              onClick={() => setActiveTab('reading_path')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'reading_path'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <BookOpen className="h-4 w-4" />
              <span>READING PATH</span>
            </button>
            <button
              onClick={() => setActiveTab('impact_analysis')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'impact_analysis'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <Target className="h-4 w-4" />
              <span>IMPACT ANALYSIS</span>
            </button>
            <button
              onClick={() => setActiveTab('issues')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'issues'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <Cpu className="h-4 w-4" />
              <span>ISSUE INTELLIGENCE</span>
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-mono tracking-wider font-semibold border-b-2 transition-all ${
                activeTab === 'chat'
                  ? 'border-primary text-text bg-primary/5'
                  : 'border-transparent text-text-muted hover:text-text hover:bg-card/20'
              }`}
            >
              <MessageSquareCode className="h-4 w-4" />
              <span>CHAT</span>
            </button>
          </div>

          {activeTab === 'analysis' && (
            <div className="space-y-6">
              {/* Summary Card */}
              <div className="border border-border bg-card/10 rounded-lg p-5 space-y-3">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                  <Info className="h-4 w-4 text-primary" /> Codebase Summary
                </h2>
                <p className="text-sm text-text leading-relaxed font-sans">
                  {architecture.summary}
                </p>
              </div>

              {/* Tech stack grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="border border-border bg-card/10 rounded-lg p-4 space-y-3">
                  <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                    <Code2 className="h-4 w-4 text-primary" /> Detected Stack
                  </h2>
                  <div className="flex flex-wrap gap-2">
                    {analysis.tech_stack.map((t) => (
                      <span key={t} className="text-xs font-mono bg-canvas border border-border px-2.5 py-1 rounded-md text-text">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="border border-border bg-card/10 rounded-lg p-4 space-y-3">
                  <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                    <Box className="h-4 w-4 text-primary" /> Primary Dependencies
                  </h2>
                  <div className="flex flex-wrap gap-1.5">
                    {analysis.dependencies.map((dep) => (
                      <span key={dep} className="text-[10px] font-mono bg-canvas border border-border/60 px-2 py-0.5 rounded text-text-muted">
                        {dep}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Reading Order List */}
              <div className="border border-border bg-card/10 rounded-lg p-5 space-y-3">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-primary" /> Suggested Reading Order
                </h2>
                <div className="space-y-2">
                  {architecture.reading_order.map((file, idx) => (
                    <div key={file} className="flex items-center gap-3 font-mono text-xs bg-canvas/30 border border-border p-2.5 rounded hover:border-primary/40 transition-colors">
                      <span className="h-5 w-5 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold">
                        {idx + 1}
                      </span>
                      <span className="text-text">{file}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Component relationships */}
              <div className="border border-border bg-card/10 rounded-lg p-5 space-y-3">
                <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                  <Cpu className="h-4 w-4 text-primary" /> Architecture Component Relationships
                </h2>
                <div className="space-y-3">
                  {architecture.relationships.map((rel, idx) => (
                    <div key={idx} className="border border-border/50 bg-canvas/20 rounded p-3 text-xs space-y-2">
                      <div className="flex flex-wrap items-center gap-2 font-mono">
                        <span className="text-text font-semibold">{rel.source}</span>
                        <span className="text-primary uppercase text-[10px] bg-primary/10 border border-primary/20 px-1.5 py-0.5 rounded">
                          {rel.relationship_type}
                        </span>
                        <span className="text-text font-semibold">{rel.target}</span>
                      </div>
                      <p className="text-text-muted leading-relaxed font-sans">{rel.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'reading_path' && (
            <ReadingOrderTimeline repoName={repoName} />
          )}

          {activeTab === 'impact_analysis' && (
            <div className="space-y-4">
              {impactLoading ? (
                <div className="flex flex-col items-center justify-center py-24 font-mono text-xs text-text-muted gap-3">
                  <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                  <span>Analyzing Change Impact...</span>
                </div>
              ) : impactData ? (
                <ImpactAnalysisGraph 
                  repoName={repoName} 
                  impactData={impactData} 
                  onReset={() => setImpactData(null)} 
                />
              ) : (
                <div className="border border-border bg-card/10 rounded-lg p-5 space-y-5">
                  <div className="space-y-2">
                    <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                      <Target className="h-4 w-4 text-primary" /> Predictive Impact Analysis
                    </h2>
                    <p className="text-xs text-text-muted font-sans leading-normal">
                      Describe your proposed code modification or feature request below to trace import propagation and discover risk metrics across architectural layers.
                    </p>
                  </div>

                  {/* Query Input runner */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <textarea
                      value={issueInput}
                      onChange={(e) => setIssueInput(e.target.value)}
                      placeholder="e.g., Add GitHub OAuth Login, or Fix SQLite Timeout Issue"
                      rows={2}
                      className="flex-grow bg-canvas border border-border rounded p-3 text-xs font-mono focus:outline-none focus:border-primary/80 resize-none text-text"
                    />
                    <button
                      onClick={() => handleRunImpactAnalysis()}
                      disabled={impactLoading || !issueInput.trim()}
                      className="bg-primary hover:bg-primary/90 disabled:bg-primary/50 text-canvas font-mono text-xs font-semibold px-5 py-3 rounded-lg transition-colors shrink-0 flex items-center justify-center"
                    >
                      Run Analysis
                    </button>
                  </div>

                  {impactError && (
                    <div className="text-xs font-mono text-red-400 bg-red-500/5 border border-red-500/20 p-3 rounded">
                      {impactError}
                    </div>
                  )}

                  {/* Preset Scenarios / Quick Examples */}
                  <div className="border-t border-border/40 pt-4 space-y-3">
                    <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block font-mono">
                      Quick Scenario Presets
                    </span>
                    <div className="flex flex-wrap gap-2.5">
                      <button
                        onClick={() => handleRunImpactAnalysis(
                          repoName.includes('fastapi') ? 'Add API key authentication' : 'Add GitHub OAuth Login'
                        )}
                        className="text-xs font-mono bg-canvas border border-border hover:border-primary/50 px-3 py-2 rounded-md text-text transition-colors flex items-center gap-1.5"
                      >
                        <HelpCircle className="h-3.5 w-3.5 text-primary" />
                        <span>{repoName.includes('fastapi') ? 'Add API key authentication' : 'Add GitHub OAuth Login'}</span>
                      </button>
                      <button
                        onClick={() => handleRunImpactAnalysis('Fix SQLite Timeout Issue')}
                        className="text-xs font-mono bg-canvas border border-border hover:border-primary/50 px-3 py-2 rounded-md text-text transition-colors flex items-center gap-1.5"
                      >
                        <HelpCircle className="h-3.5 w-3.5 text-primary" />
                        <span>Fix SQLite Timeout Issue</span>
                      </button>
                      <button
                        onClick={() => handleRunImpactAnalysis('Refactor Duplicate HTML Templates')}
                        className="text-xs font-mono bg-canvas border border-border hover:border-primary/50 px-3 py-2 rounded-md text-text transition-colors flex items-center gap-1.5"
                      >
                        <HelpCircle className="h-3.5 w-3.5 text-primary" />
                        <span>Refactor Duplicate HTML Templates</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'issues' && (
            <div className="border border-border bg-card/5 rounded-lg p-4">
              <IssueMapper repoName={repoName} />
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="min-h-[600px] flex flex-col">
              <ChatInterface repoName={repoName} />
            </div>
          )}

          {activeTab === 'graph' && (
            <ArchitectureGraph repoName={repoName} />
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
