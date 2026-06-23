import React, { useState, useEffect, useMemo, Suspense, lazy } from 'react';
import { apiUrl, extractErrorMessage } from '../../lib/api';
import FileTree from './FileTree';
import IssueMapper from './IssueMapper';
import ChatInterface from './ChatInterface';
import { ReadingOrderTimeline } from './ReadingOrderTimeline';
import { PRIntelligence } from './PRIntelligence';
import { ArchitectureDrift } from './ArchitectureDrift';
import { DeadCodeAnalyzer } from './DeadCodeAnalyzer';
import { GitHistoryAnalyzer } from './GitHistoryAnalyzer';
import { CallGraphAnalyzer } from './CallGraphAnalyzer';
import { APISurfaceAnalyzer } from './APISurfaceAnalyzer';
import { ReportPanel } from './ReportPanel';
import { Tabs, type TabItem } from './Tabs';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { MetricCard } from '../ui/MetricCard';
import { EmptyState } from '../ui/EmptyState';
import { SkeletonCard, SkeletonGroup, SkeletonGraph, Skeleton } from '../ui/Skeleton';
import {
  Layers, Box, Code2, BookOpen, Cpu, Info, CheckCircle2, Target, HelpCircle,
  MessageSquareCode, GitPullRequest, GitCompare, Trash2, FileText, DoorOpen,
  Network, AlertCircle, GitCommit, Workflow, Globe, ArrowRight, Sparkles,
  RefreshCw, BarChart2,
} from 'lucide-react';

// ── Lazy-load graph-heavy components ──────────────────────────────────────────
const InteractiveDependencyGraph = lazy(
  () => import('./graph/InteractiveDependencyGraph').then(m => ({ default: m.InteractiveDependencyGraph }))
);
const ImpactAnalysisGraph = lazy(
  () => import('./ImpactAnalysisGraph').then(m => ({ default: m.ImpactAnalysisGraph }))
);

// ── Types ─────────────────────────────────────────────────────────────────────

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

type TabId =
  | 'analysis' | 'reading_path' | 'chat'
  | 'graph' | 'call_graph' | 'api_surface'
  | 'report' | 'dead_code' | 'issues'
  | 'git_history' | 'pr_intelligence' | 'architecture_drift' | 'impact_analysis';

const TABS: TabItem<TabId>[] = [
  // ── Understand ──
  { id: 'analysis',           label: 'Overview',      icon: Layers,          group: 'Understand' },
  { id: 'reading_path',       label: 'Reading Path',  icon: BookOpen,        group: 'Understand' },
  { id: 'chat',               label: 'Chat',          icon: MessageSquareCode, group: 'Understand' },
  // ── Structure ──
  { id: 'graph',              label: 'File Graph',    icon: Code2,           group: 'Structure' },
  { id: 'call_graph',         label: 'Call Graph',    icon: Workflow,        group: 'Structure' },
  { id: 'api_surface',        label: 'API Surface',   icon: Globe,           group: 'Structure' },
  // ── Quality ──
  { id: 'report',             label: 'Health Report', icon: FileText,        group: 'Quality' },
  { id: 'dead_code',          label: 'Dead Code',     icon: Trash2,          group: 'Quality' },
  { id: 'issues',             label: 'Issues',        icon: Cpu,             group: 'Quality' },
  // ── History & PRs ──
  { id: 'git_history',        label: 'Git History',   icon: GitCommit,       group: 'History & PRs' },
  { id: 'pr_intelligence',    label: 'PR Risk',       icon: GitPullRequest,  group: 'History & PRs' },
  { id: 'architecture_drift', label: 'PR Drift',      icon: GitCompare,      group: 'History & PRs' },
  { id: 'impact_analysis',    label: 'Impact',        icon: Target,          group: 'History & PRs' },
];

function countFiles(structure: Record<string, string[]>): number {
  return Object.values(structure).reduce((sum, arr) => sum + arr.length, 0);
}

function countComponents(rels: ComponentRelationship[]): number {
  const set = new Set<string>();
  rels.forEach((r) => { set.add(r.source); set.add(r.target); });
  return set.size;
}

/** Reads the ?tab= URL param, validates it, and returns a valid TabId. */
function resolveInitialTab(): TabId {
  if (typeof window === 'undefined') return 'analysis';
  const param = new URLSearchParams(window.location.search).get('tab') as TabId | null;
  if (param && TABS.some(t => t.id === param)) return param;
  return 'analysis';
}

/** Syncs the active tab into the URL without a page reload. */
function syncTabToUrl(tab: TabId) {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  url.searchParams.set('tab', tab);
  window.history.replaceState({}, '', url.toString());
}

// ── Component ─────────────────────────────────────────────────────────────────

export const getRepoFromUrl = (repoParam?: string): string => {
  if (repoParam) return repoParam.replace('-', '/');
  if (typeof window !== 'undefined') {
    const urlParams = new URLSearchParams(window.location.search);
    const owner = urlParams.get('owner');
    const repo  = urlParams.get('repo');
    if (owner && repo) return `${owner}/${repo}`;
    const repoQuery = urlParams.get('repo');
    if (repoQuery) return repoQuery;
  }
  return 'unknown/repo';
};

export const AnalysisDashboard: React.FC<DashboardProps> = ({ repoParam }) => {
  const [repoName, setRepoName]       = useState(() => getRepoFromUrl(repoParam));
  const [data, setData]               = useState<AnalysisData | null>(null);
  const [loading, setLoading]         = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [activeTab, setActiveTab]     = useState<TabId>(resolveInitialTab);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Impact Analysis state
  const [impactData, setImpactData]   = useState<any | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [issueInput, setIssueInput]   = useState('');
  const [impactError, setImpactError] = useState<string | null>(null);

  // Lazy mount: tracks which tabs have been visited (so we only mount on first visit)
  const [mountedTabs, setMountedTabs] = useState<Set<TabId>>(new Set([resolveInitialTab()]));

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
    setMountedTabs(prev => new Set([...prev, tab]));
    syncTabToUrl(tab);
  };

  // Sync state if repoParam changes from parent
  useEffect(() => {
    const nextRepo = getRepoFromUrl(repoParam);
    setRepoName(nextRepo);
  }, [repoParam]);

  // Sync state on popstate (browser back/forward buttons)
  useEffect(() => {
    const handlePopState = () => {
      const tab = resolveInitialTab();
      setActiveTab(tab);
      setMountedTabs(prev => new Set([...prev, tab]));
      
      const repoVal = getRepoFromUrl(repoParam);
      setRepoName(repoVal);
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [repoParam]);

  useEffect(() => {
    const [owner, name] = repoName.split('/');
    if (!owner || !name || owner === 'unknown' || name === 'repo') {
      setErrorMessage('Repository information missing or invalid. Redirecting to home.');
      setTimeout(() => (window.location.href = '/'), 2000);
      setLoading(false);
      return;
    }
    
    // Clear stale state for the previous repository
    setData(null);
    setSelectedFile(null);
    setImpactData(null);
    setIssueInput('');
    setImpactError(null);
    setLoading(true);
    setErrorMessage(null);

    if (typeof window !== 'undefined') {
      localStorage.setItem('activeRepo', repoName);
      localStorage.setItem(`lastAnalysed:${repoName}`, String(Date.now()));
      // Dispatch custom event to notify Astro header navigation that activeRepo changed
      window.dispatchEvent(new CustomEvent('active-repo-changed', { detail: repoName }));
    }

    fetch(apiUrl(`/api/analysis/${owner}/${name}`))
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch repository details');
        return res.json();
      })
      .then((resData) => { setData(resData); setLoading(false); })
      .catch((err) => { setErrorMessage(err.message); setLoading(false); });
  }, [repoName]);

  const handleRunImpactAnalysis = (overrideText?: string) => {
    const queryText = overrideText !== undefined ? overrideText : issueInput;
    if (!queryText.trim()) return;
    if (overrideText !== undefined) setIssueInput(overrideText);
    setImpactLoading(true);
    setImpactError(null);

    fetch(apiUrl('/api/impact-analysis'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo: repoName, issue: queryText }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(extractErrorMessage(errData) || 'Failed to analyze impact');
        }
        return res.json();
      })
      .then((resData) => { setImpactData(resData); setImpactLoading(false); })
      .catch((err) => { setImpactError(extractErrorMessage(err)); setImpactLoading(false); });
  };

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <SkeletonGroup label="Loading repository analysis">
        <div className="space-y-6 py-4 fade-up">
          <div className="space-y-4">
            <Skeleton size="h-8 w-1/2" />
            <Skeleton size="h-4 w-1/3" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Array.from({ length: 5 }, (_, i) => <SkeletonCard key={i} />)}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 card p-5 space-y-3">
              <Skeleton size="h-4 w-32" />
              {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} size="h-3 w-full" />)}
            </div>
            <div className="lg:col-span-8 space-y-4">
              <Skeleton size="h-10 w-full" />
              <div className="card p-5 space-y-3">
                <Skeleton size="h-4 w-40" />
                <Skeleton size="h-3 w-full" />
                <Skeleton size="h-3 w-5/6" />
              </div>
            </div>
          </div>
        </div>
      </SkeletonGroup>
    );
  }

  // ── Hard error state ───────────────────────────────────────────────────────
  if (!data) {
    return (
      <div className="py-12">
        <EmptyState
          tone="danger"
          icon={<AlertCircle className="h-6 w-6" aria-hidden="true" />}
          title="Could not load repository analysis"
          description={errorMessage ?? 'Make sure the backend is running and the repository has been analyzed.'}
          action={<Button variant="ghost" onClick={() => (window.location.href = '/')}>Back to home</Button>}
        />
      </div>
    );
  }

  const { analysis, architecture } = data;

  const fileCount       = countFiles(analysis.structure);
  const componentCount  = countComponents(architecture.relationships);
  const languageCount   = analysis.tech_stack.length;
  const dependencyCount = analysis.dependencies.length;
  const readingSteps    = architecture.reading_order.length;
  const [owner, repoSlug] = repoName.split('/');

  return (
    <div className="space-y-6 w-full py-4 fade-up">
      {/* ── REPO CONTEXT HEADER ──────────────────────────────────────────────── */}
      <header className="space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 border-b border-border pb-5">
          <div className="min-w-0">
            <div className="text-[10px] font-mono uppercase tracking-widest text-primary font-bold mb-1.5">
              Repository Intelligence
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-text tracking-tight flex items-center gap-2.5 break-all">
              <Layers className="h-6 w-6 text-primary shrink-0" aria-hidden="true" />
              <span className="font-mono">
                <span className="text-text-muted">{owner}</span>
                <span className="text-text-subtle">/</span>
                <span className="text-text">{repoSlug}</span>
              </span>
            </h1>
            <p className="text-sm text-text-muted mt-2 font-sans max-w-2xl leading-relaxed">
              {architecture.summary.slice(0, 160)}{architecture.summary.length > 160 ? '…' : ''}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Badge tone="success" icon={<CheckCircle2 className="h-3 w-3" />}>
              Indexed
            </Badge>
            <a
              href={`https://github.com/${owner}/${repoSlug}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost text-xs"
            >
              <GitPullRequest className="h-3.5 w-3.5" aria-hidden="true" />
              GitHub
            </a>
            <button
              type="button"
              className="btn-ghost text-xs"
              onClick={() => window.location.reload()}
              aria-label="Refresh analysis"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Refresh
            </button>
            <button
              type="button"
              className="btn-ghost text-xs"
              onClick={() => handleTabChange('report')}
              aria-label="Export health report"
            >
              <FileText className="h-3.5 w-3.5" aria-hidden="true" />
              Export Report
            </button>
          </div>
        </div>

        {/* KPI metric strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricCard
            tone="primary"
            icon={<FileText className="h-4 w-4" />}
            label="Files Indexed"
            value={fileCount.toLocaleString()}
            hint={`${Object.keys(analysis.structure).length} directories`}
          />
          <MetricCard
            tone="info"
            icon={<Code2 className="h-4 w-4" />}
            label="Languages"
            value={languageCount}
            hint={analysis.tech_stack.slice(0, 3).join(' · ') || '—'}
          />
          <MetricCard
            tone="success"
            icon={<Network className="h-4 w-4" />}
            label="Components"
            value={componentCount}
            hint={`${architecture.relationships.length} relationships`}
          />
          <MetricCard
            tone="warn"
            icon={<Box className="h-4 w-4" />}
            label="Dependencies"
            value={dependencyCount}
            hint="primary manifests"
          />
          <MetricCard
            tone="primary"
            icon={<DoorOpen className="h-4 w-4" />}
            label="Reading Steps"
            value={readingSteps}
            hint="ranked onboarding flow"
            onClick={() => handleTabChange('reading_path')}
          />
        </div>
      </header>

      {/* ── WORKSPACE ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-4 space-y-4">
          <FileTree structure={analysis.structure} onFileSelect={setSelectedFile} />
          {selectedFile && (
            <div className="card p-4 space-y-2 fade-up">
              <span className="text-primary font-bold uppercase tracking-wider block text-[10px] font-mono">
                Selected Node
              </span>
              <p className="text-text break-all text-xs font-mono">{selectedFile}</p>
              <p className="text-text-muted text-xs font-sans leading-relaxed">
                Pass this file context to the Issue Mapper or Chat tab to discuss implementation plans.
              </p>
            </div>
          )}
        </div>

        <div className="lg:col-span-8 space-y-6 min-w-0">
          <Tabs items={TABS} active={activeTab} onChange={handleTabChange} />

          {/* Tab panels — mount-on-first-visit, stay mounted to preserve state */}
          {TABS.map(({ id }) => (
            <div
              key={id}
              id={`tabpanel-${id}`}
              role="tabpanel"
              aria-labelledby={id}
              hidden={activeTab !== id}
              className="space-y-6"
            >
              {mountedTabs.has(id) && (
                <>
                  {/* ── Overview ── */}
                  {id === 'analysis' && (
                    <>
                      {/* Quick-action chips */}
                      <div className="flex flex-wrap gap-2" role="navigation" aria-label="Quick navigation">
                        {[
                          { label: 'Explore Graph', tab: 'graph' as TabId },
                          { label: 'Read Path',     tab: 'reading_path' as TabId },
                          { label: 'Health Report', tab: 'report' as TabId },
                          { label: 'Ask Chat',      tab: 'chat' as TabId },
                        ].map(({ label, tab }) => (
                          <button
                            key={tab}
                            type="button"
                            onClick={() => handleTabChange(tab)}
                            className="inline-flex items-center gap-1.5 text-xs font-medium font-sans
                                       px-3 py-1.5 rounded-md border border-primary/30 bg-primary/5
                                       text-primary hover:bg-primary/10 transition-colors
                                       focus-visible:outline-none focus-visible:shadow-ring"
                          >
                            {label}
                            <ArrowRight className="h-3 w-3" aria-hidden="true" />
                          </button>
                        ))}
                      </div>

                      <div className="card p-6 space-y-3">
                        <h2 className="panel-title">
                          <Info className="h-4 w-4 text-primary" aria-hidden="true" /> Codebase Summary
                        </h2>
                        <p className="text-sm text-text leading-relaxed font-sans">
                          {architecture.summary}
                        </p>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="card p-4 space-y-3">
                          <h2 className="panel-title">
                            <Code2 className="h-4 w-4 text-primary" aria-hidden="true" /> Detected Stack
                          </h2>
                          <div className="flex flex-wrap gap-2">
                            {analysis.tech_stack.map((t) => (
                              <span key={t} className="text-xs font-mono bg-canvas border border-border px-2.5 py-1 rounded-md text-text">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="card p-4 space-y-3">
                          <h2 className="panel-title">
                            <Box className="h-4 w-4 text-primary" aria-hidden="true" /> Primary Dependencies
                          </h2>
                          <div className="flex flex-wrap gap-1.5 max-h-44 overflow-y-auto">
                            {analysis.dependencies.map((dep) => (
                              <span key={dep} className="text-[10px] font-mono bg-canvas border border-border/60 px-2 py-0.5 rounded text-text-muted">
                                {dep}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Cross-navigate to health report if available */}
                      <button
                        type="button"
                        onClick={() => handleTabChange('report')}
                        className="w-full card p-4 flex items-center justify-between hover:border-primary/40 hover:-translate-y-0.5 transition-all text-left"
                        aria-label="View Health Report"
                      >
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center">
                            <BarChart2 className="h-4 w-4 text-primary" aria-hidden="true" />
                          </div>
                          <div>
                            <div className="text-sm font-semibold text-text">Repository Health Report</div>
                            <div className="text-xs text-text-muted font-sans">Architecture · API · Hygiene · Onboarding scores</div>
                          </div>
                        </div>
                        <ArrowRight className="h-4 w-4 text-text-muted" aria-hidden="true" />
                      </button>

                      <div className="card p-6 space-y-3">
                        <h2 className="panel-title">
                          <Cpu className="h-4 w-4 text-primary" aria-hidden="true" /> Architecture Component Relationships
                        </h2>
                        {architecture.relationships.length > 0 ? (
                          <div className="space-y-3">
                            {architecture.relationships.map((rel, idx) => (
                              <div key={idx} className="border border-border bg-canvas/40 rounded-lg p-3 text-xs space-y-2">
                                <div className="flex flex-wrap items-center gap-2 font-mono">
                                  <span className="text-text font-semibold">{rel.source}</span>
                                  <Badge tone="primary">{rel.relationship_type}</Badge>
                                  <span className="text-text font-semibold">{rel.target}</span>
                                </div>
                                <p className="text-text-muted leading-relaxed font-sans">{rel.description}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <EmptyState
                            compact
                            icon={<Network className="h-5 w-5" aria-hidden="true" />}
                            title="No architectural relationships found"
                            description="This repository's components run independently."
                          />
                        )}
                      </div>
                    </>
                  )}

                  {/* ── Structure ── */}
                  {id === 'graph' && (
                    <Suspense fallback={<SkeletonGraph />}>
                      <InteractiveDependencyGraph repoName={repoName} />
                    </Suspense>
                  )}
                  {id === 'call_graph'  && <CallGraphAnalyzer  repoName={repoName} />}
                  {id === 'api_surface' && <APISurfaceAnalyzer repoName={repoName} />}

                  {/* ── Understand ── */}
                  {id === 'reading_path' && <ReadingOrderTimeline repoName={repoName} />}
                  {id === 'chat' && (
                    <div className="min-h-[600px] flex flex-col">
                      <ChatInterface repoName={repoName} />
                    </div>
                  )}

                  {/* ── Quality ── */}
                  {id === 'report'     && <ReportPanel      repoName={repoName} />}
                  {id === 'dead_code'  && <DeadCodeAnalyzer  repoName={repoName} />}
                  {id === 'issues'     && <IssueMapper       repoName={repoName} />}

                  {/* ── History & PRs ── */}
                  {id === 'git_history'        && <GitHistoryAnalyzer repoName={repoName} />}
                  {id === 'pr_intelligence'    && <PRIntelligence     repoName={repoName} />}
                  {id === 'architecture_drift' && <ArchitectureDrift  repoName={repoName} />}
                  {id === 'impact_analysis' && (
                    <div className="space-y-4">
                      {impactLoading ? (
                        <SkeletonGroup label="Analyzing change impact">
                          <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>
                        </SkeletonGroup>
                      ) : impactData ? (
                        <Suspense fallback={<SkeletonGraph />}>
                          <ImpactAnalysisGraph
                            repoName={repoName}
                            impactData={impactData}
                            onReset={() => setImpactData(null)}
                          />
                        </Suspense>
                      ) : (
                        <div className="card p-6 space-y-5">
                          <div className="space-y-2">
                            <h2 className="panel-title">
                              <Target className="h-4 w-4 text-primary" aria-hidden="true" /> Predictive Impact Analysis
                            </h2>
                            <p className="text-sm text-text-muted font-sans leading-normal max-w-2xl">
                              Describe a proposed code modification or feature request to trace import propagation
                              and discover risk metrics across architectural layers.
                            </p>
                          </div>

                          <div className="flex flex-col sm:flex-row gap-3">
                            <label htmlFor="impact-query" className="sr-only">Issue text</label>
                            <textarea
                              id="impact-query"
                              value={issueInput}
                              onChange={(e) => setIssueInput(e.target.value)}
                              placeholder="e.g., Add GitHub OAuth Login, or Fix SQLite Timeout Issue"
                              rows={2}
                              className="input flex-grow resize-none"
                            />
                            <Button
                              type="button"
                              onClick={() => handleRunImpactAnalysis()}
                              disabled={impactLoading || !issueInput.trim()}
                              className="shrink-0"
                            >
                              Run Analysis
                            </Button>
                          </div>

                          {impactError && (
                            <div role="alert" className="text-xs font-sans text-danger bg-danger/10 border border-danger/30 p-3 rounded-lg">
                              {impactError}
                            </div>
                          )}

                          <div className="border-t border-border pt-4 space-y-3">
                            <span className="panel-title">Quick Scenario Presets</span>
                            <div className="flex flex-wrap gap-2.5">
                              {[
                                repoName.includes('fastapi') ? 'Add API key authentication' : 'Add GitHub OAuth Login',
                                'Fix SQLite Timeout Issue',
                                'Refactor Duplicate HTML Templates',
                              ].map((preset) => (
                                <button
                                  key={preset}
                                  type="button"
                                  onClick={() => handleRunImpactAnalysis(preset)}
                                  className="text-xs font-sans bg-canvas border border-border hover:border-primary/40
                                             px-3 py-2 rounded-md text-text-muted hover:text-text transition-colors
                                             flex items-center gap-1.5 focus-visible:outline-none focus-visible:shadow-ring"
                                >
                                  <HelpCircle className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                                  <span>{preset}</span>
                                </button>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AnalysisDashboard;
