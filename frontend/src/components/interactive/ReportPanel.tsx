import React, { useState, useEffect } from 'react';
import { apiUrl, extractErrorMessage } from '../../lib/api';
import {
  FileText, Download, Printer, ShieldAlert, CheckCircle, Info,
  Layers, Globe, Workflow, Trash2, BookOpen, AlertTriangle, ChevronRight,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { MetricCard } from '../ui/MetricCard';
import { EmptyState } from '../ui/EmptyState';
import { SkeletonCard, SkeletonGroup, Skeleton } from '../ui/Skeleton';
import { Tabs, type TabItem } from './Tabs';
import { SVGDonut } from '../ui/SVGDonut';
import { AnimatedNumber } from '../ui/AnimatedNumber';

interface ScoreBreakdown {
  overall: number;
  architecture: number;
  api: number;
  hygiene: number;
  churn: number;
  readability: number;
  grade: string;
}

interface ReportMetadata {
  repo_name: string;
  owner: string;
  name: string;
  total_loc: number;
  commits_count: number;
  languages: Record<string, number>;
  generated_at: string;
  execution_time_ms: number;
}

interface ArchReportSection {
  cycles_count: number;
  cycles: string[][];
  strongly_connected_components: number;
  smells_count: number;
  smells: string[];
}

interface ApiReportSection {
  total_exported_symbols: number;
  public_private_ratio: number;
  average_distance_main_sequence: number;
  unstable_modules_count: number;
}

interface HygieneReportSection {
  dead_functions_count: number;
  dead_functions: string[];
  dead_code_ratio: number;
}

interface OnboardingReportSection {
  reading_path_completeness: number;
  core_entry_points: string[];
  recommended_reading_path: string[];
}

interface ReportDataModel {
  metadata: ReportMetadata;
  scores: ScoreBreakdown;
  architecture: ArchReportSection;
  api_surface: ApiReportSection;
  hygiene: HygieneReportSection;
  onboarding: OnboardingReportSection;
  refactoring_priorities: string[];
  ai_summary?: string;
}

interface ReportPanelProps {
  repoName: string;
}

type SubTabId = 'architecture' | 'api' | 'hygiene' | 'onboarding';

const SUB_TABS: TabItem<SubTabId>[] = [
  { id: 'architecture', label: 'Architecture', icon: Layers },
  { id: 'api',          label: 'API Surface',  icon: Globe },
  { id: 'hygiene',      label: 'Hygiene',      icon: Trash2 },
  { id: 'onboarding',   label: 'Onboarding',   icon: BookOpen },
];

function getGradeTone(grade: string): 'success' | 'warn' | 'danger' | 'primary' {
  if (grade === 'A') return 'success';
  if (grade === 'B') return 'primary';
  if (grade === 'C') return 'warn';
  return 'danger';
}

function getScoreTone(score: number): 'success' | 'warn' | 'danger' {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warn';
  return 'danger';
}

function getMetricProgressColor(score: number): string {
  if (score >= 80) return 'bg-success';
  if (score >= 60) return 'bg-warn';
  return 'bg-danger';
}

function relativeTime(iso: string): string {
  try {
    const diff = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (diff < 1) return 'just now';
    if (diff < 60) return `${diff} min ago`;
    return `${Math.round(diff / 60)}h ago`;
  } catch {
    return iso;
  }
}

export const ReportPanel: React.FC<ReportPanelProps> = ({ repoName }) => {
  const [report, setReport]   = useState<ReportDataModel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [subTab, setSubTab]   = useState<SubTabId>('architecture');

  const [owner, repo] = repoName.split('/');

  useEffect(() => {
    if (!owner || !repo) {
      setError('Invalid repository name');
      setReport(null);
      setLoading(false);
      return;
    }

    setReport(null);
    setLoading(true);
    setError(null);

    fetch(apiUrl(`/api/v1/report/${owner}/${repo}/build`), { method: 'POST' })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to generate intelligence report');
        return res.json();
      })
      .then((data) => { setReport(data); setLoading(false); })
      .catch((err) => { setError(extractErrorMessage(err)); setLoading(false); });
  }, [repoName]);

  const handleExport = (format: 'html' | 'pdf' | 'markdown') => {
    if (!owner || !repo) return;
    const downloadUrl = apiUrl(`/api/v1/report/${owner}/${repo}/download?format=${format}`);
    window.open(downloadUrl, '_blank');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="card p-6 flex items-center justify-center space-x-3">
          <svg className="h-6 w-6 text-primary animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <span className="text-text font-mono text-sm">Compiling Repository Intelligence Report...</span>
        </div>
        <SkeletonGroup label="Generating report skeleton">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-4 space-y-4">
              <SkeletonCard /><SkeletonCard />
            </div>
            <div className="lg:col-span-8 space-y-4">
              <div className="card p-6 space-y-4">
                <Skeleton size="h-6 w-1/3" />
                <Skeleton size="h-4 w-full" />
                <Skeleton size="h-4 w-5/6" />
                <Skeleton size="h-4 w-4/5" />
              </div>
            </div>
          </div>
        </SkeletonGroup>
      </div>
    );
  }

  if (error || !report) {
    return (
      <EmptyState
        tone="danger"
        icon={<AlertTriangle className="h-6 w-6" />}
        title="Report Generation Failed"
        description={error || 'Could not compile report metadata.'}
      />
    );
  }

  const gradeTone  = getGradeTone(report.scores.grade);
  const scoreTone  = getScoreTone(report.scores.overall);

  return (
    <div className="space-y-6">
      {/* ── Main content grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left Column: Scores & Action Items */}
        <div className="lg:col-span-4 space-y-6">

          {/* Health Score Card with animated SVG donut */}
          <div className="card p-6 space-y-6 text-center">
            <div className="flex flex-col items-center gap-2">
              <SVGDonut
                value={report.scores.overall}
                size={128}
                strokeWidth={10}
                tone={scoreTone}
                label={
                  <>
                    <span className="text-3xl font-extrabold text-text font-mono leading-none">
                      <AnimatedNumber value={report.scores.overall} duration={800} />
                    </span>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Health</span>
                  </>
                }
              />
              <div className={`px-3 py-1 rounded-md border text-sm font-mono font-bold ${{
                success: 'text-success border-success/30 bg-success/10',
                primary: 'text-primary border-primary/30 bg-primary/10',
                warn:    'text-warn border-warn/30 bg-warn/10',
                danger:  'text-danger border-danger/30 bg-danger/10',
              }[gradeTone]}`}>
                Grade {report.scores.grade}
              </div>
            </div>

            {/* Sub-dimension progress bars */}
            <div className="space-y-3.5 text-left pt-2 border-t border-border/60">
              {[
                { label: 'Architecture Stability', value: report.scores.architecture },
                { label: 'API Quality & Distance', value: report.scores.api },
                { label: 'Code Hygiene',            value: report.scores.hygiene },
                { label: 'Hotspot & Churn Risk',    value: report.scores.churn },
                { label: 'Onboarding Clarity',      value: report.scores.readability },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-xs font-mono text-text-muted">
                    <span>{item.label}</span>
                    <span><AnimatedNumber value={item.value} duration={600} suffix="/100" /></span>
                  </div>
                  <div className="h-1.5 w-full bg-border rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${getMetricProgressColor(item.value)}`}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* AI Summary — rendered only if present */}
          {report.ai_summary && (
            <div className="card p-5 space-y-3">
              <h3 className="panel-title">
                <svg className="h-4 w-4 text-primary" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/></svg>
                AI Summary
              </h3>
              <p className="text-xs text-text-muted leading-relaxed font-sans">{report.ai_summary}</p>
            </div>
          )}

          {/* Refactoring Priorities */}
          <div className="card p-5 space-y-4">
            <h3 className="panel-title">
              <ShieldAlert className="h-4 w-4 text-primary" aria-hidden="true" />
              Prioritized Action Items
            </h3>
            {report.refactoring_priorities.length > 0 ? (
              <div className="space-y-2.5">
                {report.refactoring_priorities.map((item, idx) => {
                  const isHighRisk = item.toLowerCase().includes('volatile') || item.toLowerCase().includes('high');
                  return (
                    <div key={idx} className="flex items-start gap-2.5 p-2.5 bg-canvas/45 rounded-lg border border-border/80 text-xs">
                      <span className={`shrink-0 text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
                        isHighRisk ? 'bg-danger/10 text-danger border border-danger/30' : 'bg-warn/10 text-warn border border-warn/30'
                      }`}>
                        {isHighRisk ? 'HIGH RISK' : 'CLEANUP'}
                      </span>
                      <span className="text-text-muted leading-relaxed font-sans">{item}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-xs text-text-muted">No high priority refactoring issues found.</p>
            )}
          </div>
        </div>

        {/* Right Column: Detail Sub-Tabs */}
        <div className="lg:col-span-8 space-y-4">
          {/* Shared Tabs component instead of inline duplicate */}
          <Tabs items={SUB_TABS} active={subTab} onChange={setSubTab} />

          <div id={`tabpanel-${subTab}`} role="tabpanel" className="min-w-0">
            {subTab === 'architecture' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Circular Imports</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.architecture.cycles_count} />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">SCC Clusters</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.architecture.strongly_connected_components} />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Design Smells</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.architecture.smells_count} />
                    </p>
                  </div>
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    Dependency Design Violations
                  </h4>
                  {report.architecture.smells.length > 0 ? (
                    <ul className="space-y-2 text-xs text-text-muted font-sans">
                      {report.architecture.smells.map((smell, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <ChevronRight className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" aria-hidden="true" />
                          <span>{smell}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-text-muted">No dependency smells detected.</p>
                  )}
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    Circular Import Paths
                  </h4>
                  {report.architecture.cycles.length > 0 ? (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {report.architecture.cycles.map((cycle, idx) => (
                        <div key={idx} className="bg-canvas border border-border/60 rounded p-2.5 text-xs font-mono overflow-x-auto">
                          {cycle.join(' → ')} → {cycle[0]}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-text-muted">No circular import loops detected.</p>
                  )}
                </div>
              </div>
            )}

            {subTab === 'api' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Exported Symbols</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.api_surface.total_exported_symbols} />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Pub/Priv Ratio</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.api_surface.public_private_ratio} decimals={2} />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Avg Distance</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.api_surface.average_distance_main_sequence} decimals={2} />
                    </p>
                  </div>
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    API Packaging Stability Guidelines
                  </h4>
                  <p className="text-xs text-text-muted leading-relaxed font-sans">
                    A stable design aligns packaging along the main sequence. Packages with low stability that have
                    highly stable dependents are in risk zones. A public-to-private symbol ratio below 0.5 suggests healthy encapsulation.
                  </p>
                  <div className="table-scroll">
                    <table className="table-base">
                      <thead>
                        <tr>
                          <th>Category</th>
                          <th>Value</th>
                          <th>Target Range</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>Average Distance</td>
                          <td>{report.api_surface.average_distance_main_sequence}</td>
                          <td>≤ 0.3 (Shorter is balanced)</td>
                        </tr>
                        <tr>
                          <td>Public / Private Ratio</td>
                          <td>{report.api_surface.public_private_ratio}</td>
                          <td>0.1 – 0.5 (Encapsulated)</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {subTab === 'hygiene' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Dead Functions</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.hygiene.dead_functions_count} />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Dead Code Ratio</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.hygiene.dead_code_ratio} decimals={1} suffix="%" />
                    </p>
                  </div>
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    Dead Code Registry
                  </h4>
                  {report.hygiene.dead_functions.length > 0 ? (
                    <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                      {report.hygiene.dead_functions.map((func, idx) => (
                        <div key={idx} className="flex justify-between items-center p-2.5 bg-canvas/30 border border-border/50 rounded text-xs font-mono">
                          <span className="text-text break-all">{func}</span>
                          <span className="shrink-0 text-[10px] text-text-muted bg-canvas px-1.5 py-0.5 rounded ml-2">Unused</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-text-muted">No unused functions detected in call graph sweep.</p>
                  )}
                </div>
              </div>
            )}

            {subTab === 'onboarding' && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Reading Path Coverage</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.onboarding.reading_path_completeness} decimals={0} suffix="%" />
                    </p>
                  </div>
                  <div className="card p-4 space-y-1">
                    <span className="text-[10px] font-mono text-text-subtle uppercase">Primary Entry Points</span>
                    <p className="text-2xl font-bold font-mono text-text">
                      <AnimatedNumber value={report.onboarding.core_entry_points.length} />
                    </p>
                  </div>
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    Main Entry Points
                  </h4>
                  {report.onboarding.core_entry_points.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {report.onboarding.core_entry_points.map((entry, idx) => (
                        <code key={idx} className="text-xs bg-canvas px-2.5 py-1 rounded border border-border text-primary font-semibold">
                          {entry}
                        </code>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-text-muted">No main code entry points detected.</p>
                  )}
                </div>

                <div className="card p-5 space-y-4">
                  <h4 className="text-xs font-mono font-bold text-text-muted border-b border-border/60 pb-2">
                    Topological Reading Order Guide
                  </h4>
                  <p className="text-xs text-text-muted leading-relaxed font-sans">
                    Read the repository's modules in this topological sequence to understand structural dependencies
                    from base imports up to high-level controllers.
                  </p>
                  {report.onboarding.recommended_reading_path.length > 0 ? (
                    <ol className="space-y-2 text-xs font-mono pl-4 list-decimal text-text-muted">
                      {report.onboarding.recommended_reading_path.map((path, idx) => (
                        <li key={idx} className="pl-1 text-text hover:text-primary transition-colors">
                          {path}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-xs text-text-muted">No reading path compiled.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Sticky export footer ── */}
      <div className="sticky bottom-0 bg-canvas/90 backdrop-blur-sm border-t border-border flex flex-wrap items-center justify-between gap-3 px-5 py-3 -mx-4 sm:-mx-6 lg:-mx-8 rounded-b-lg">
        <span className="text-xs font-mono text-text-muted">
          Grade:{' '}
          <span className={`font-bold ${{
            success: 'text-success', primary: 'text-primary', warn: 'text-warn', danger: 'text-danger',
          }[gradeTone]}`}>
            {report.scores.grade}
          </span>
          {' · '}{report.metadata.repo_name}
          {' · '}Generated {relativeTime(report.metadata.generated_at)}
        </span>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => handleExport('html')}>
            <Download className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            HTML
          </Button>
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => handleExport('markdown')}>
            <FileText className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            Markdown
          </Button>
          <Button variant="primary" size="sm" className="text-xs" onClick={() => handleExport('pdf')}>
            <Printer className="h-3.5 w-3.5 mr-1" aria-hidden="true" />
            Print / PDF
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ReportPanel;
