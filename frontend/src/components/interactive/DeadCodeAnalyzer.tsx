import React, { useState, useEffect } from 'react';
import { apiUrl, extractErrorMessage } from '../../lib/api';
import {
  Trash2,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  Activity,
  Award,
  Zap,
  RefreshCw,
  Plus,
  Minus,
  DoorOpen,
  ArrowRight,
  TrendingDown,
  Sparkles,
  GitBranch,
  FileCode,
  FolderOpen
} from 'lucide-react';

interface DeadFile {
  file_path: string;
  confidence: number;
  risk_level: string;
  recommendation: string;
}

interface OrphanModule {
  file_path: string;
  confidence: number;
  risk_level: string;
  recommendation: string;
  last_reachable_parent?: string;
}

interface DeadDependencyChain {
  chain: string[];
  confidence: number;
  risk_level: string;
  recommendation: string;
  length: number;
  total_nodes: number;
  max_centrality: number;
}

interface DeadCodeResult {
  repo: string;
  cleanup_score: number;
  previous_cleanup_score?: number;
  estimated_cleanup_effort: string;
  unused_files: DeadFile[];
  orphan_modules: OrphanModule[];
  dead_dependency_chains: DeadDependencyChain[];
  cleanup_recommendations: string[];
  analyzed_at: string;
}

interface DeadCodeAnalyzerProps {
  repoName?: string;
}

export const DeadCodeAnalyzer: React.FC<DeadCodeAnalyzerProps> = ({ repoName }) => {
  const [activeRepo, setActiveRepo] = useState(() => {
    if (repoName) return repoName;
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const owner = urlParams.get('owner');
      const repo = urlParams.get('repo');
      if (owner && repo) return `${owner}/${repo}`;
      const stored = localStorage.getItem('activeRepo');
      if (stored) return stored;
    }
    return '';
  });

  const [isLoading, setIsLoading] = useState(false);
  const [analyzerResult, setAnalyzerResult] = useState<DeadCodeResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [isRepairing, setIsRepairing] = useState(false);

  const handleRepair = async () => {
    if (!activeRepo) return;
    const [owner, repo] = activeRepo.split('/');
    setIsRepairing(true);
    setErrorMsg('');
    try {
      const res = await fetch(apiUrl('/api/repos/repair'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner, repo })
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(extractErrorMessage(errorData));
      }
      // Re-fetch health status
      const healthRes = await fetch(apiUrl(`/api/pr/health?owner=${owner}&repo=${repo}`));
      const healthData = await healthRes.json();
      setHealthStatus(healthData);
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsRepairing(false);
    }
  };

  // Load diagnostics status on mount or repo change
  useEffect(() => {
    if (activeRepo) {
      const [owner, repo] = activeRepo.split('/');
      fetch(apiUrl(`/api/pr/health?owner=${owner}&repo=${repo}`))
        .then(res => res.json())
        .then(data => setHealthStatus(data))
        .catch(err => console.error("PR Health check failed", err));
    }
  }, [activeRepo]);

  const handleRunAnalysis = async () => {
    if (!activeRepo) {
      setErrorMsg('No active repository loaded.');
      return;
    }

    const [owner, repo] = activeRepo.split('/');
    if (!owner || !repo) {
      setErrorMsg('Invalid repository identifier.');
      return;
    }

    setIsLoading(true);
    setErrorMsg('');
    setAnalyzerResult(null);

    try {
      const res = await fetch(apiUrl('/api/dead-code/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner, repo }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(extractErrorMessage(errorData));
      }

      const data = await res.json();
      setAnalyzerResult(data);
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColorClass = (level: string) => {
    switch (level.toUpperCase()) {
      case 'DANGEROUS': return 'bg-red-500/10 text-red-500 border-red-500/30';
      case 'REVIEW': return 'bg-orange-500/10 text-orange-500 border-orange-500/30';
      default: return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30';
    }
  };

  const getEffortColorClass = (effort: string) => {
    switch (effort.toUpperCase()) {
      case 'HIGH': return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'MEDIUM': return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
      default: return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    }
  };

  const hasPrerequisites = healthStatus
    ? healthStatus.analysis_exists && healthStatus.graph_available && healthStatus.symbol_index_available
    : true;

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto px-4 py-6 text-slate-100">
      
      {/* Trigger Board Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <Trash2 className="w-6 h-6 text-indigo-400" />
              <h2 className="text-xl font-bold tracking-tight text-white font-mono">Dead Code Intelligence</h2>
            </div>
            <p className="text-xs text-slate-400 max-w-xl font-sans">
              Analyze the active repository's dependency graph for unreachable modules, isolated files, and dead dependency chains. Supports automatic path filters via <code>data/dead_code_ignore.json</code>.
            </p>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={isLoading || !activeRepo || !hasPrerequisites}
            className="bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg px-6 py-3 flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/10 cursor-pointer shrink-0"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Running Dead Code Analysis...
              </>
            ) : 'Run Analysis'}
          </button>
        </div>

        {!hasPrerequisites && healthStatus && (
          <div className="flex flex-col gap-2 bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-sm text-amber-400 font-sans">
            <div className="flex gap-2.5 items-start">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-bold uppercase tracking-wider text-[10px] block">Repository Prerequisite Validation</span>
                <p className="leading-relaxed">
                  {!healthStatus.analysis_exists
                    ? `Repository '${activeRepo}' has not been analyzed yet. Go to Repository Analysis to run the initial analysis.`
                    : !healthStatus.graph_available
                    ? `Repository '${activeRepo}' analyzed but dependency graph is missing. Re-run Architecture Build.`
                    : `Repository '${activeRepo}' analyzed but symbol index is missing. Re-run Architecture Build or click rebuild below.`
                  }
                </p>
              </div>
            </div>
            {healthStatus.analysis_exists && !healthStatus.symbol_index_available && (
              <button
                type="button"
                onClick={handleRepair}
                disabled={isRepairing}
                className="mt-2 text-indigo-400 hover:text-indigo-300 font-semibold text-xs flex items-center gap-1.5 self-start bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 px-3 py-1.5 rounded transition-all cursor-pointer disabled:opacity-50"
              >
                {isRepairing ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Rebuilding Symbol Index...
                  </>
                ) : 'Rebuild Symbol Index'}
              </button>
            )}
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="flex gap-2.5 items-start bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-sm text-red-400 font-mono">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Analysis Results */}
      {analyzerResult && (
        <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          
          {/* Header Metadata */}
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider font-mono">Repository Context</span>
              <h1 className="text-lg font-bold text-white tracking-tight font-mono mt-0.5">{analyzerResult.repo}</h1>
              <p className="text-xs text-slate-500 mt-1 font-mono">Completed at {new Date(analyzerResult.analyzed_at).toLocaleString()}</p>
            </div>
            
            <div className="flex items-center gap-4">
              <div className="flex flex-col items-end">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono">Estimated Cleanup Effort</span>
                <span className={`text-xs font-bold px-2.5 py-1 rounded-md border font-mono mt-1 ${getEffortColorClass(analyzerResult.estimated_cleanup_effort)}`}>
                  {analyzerResult.estimated_cleanup_effort}
                </span>
              </div>
            </div>
          </div>

          {/* Scoring details and recommendations */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Score Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between items-center text-center relative overflow-hidden">
              <div className="text-slate-400 font-bold text-sm mb-4 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Award className="w-4 h-4 text-indigo-400" />
                <span>Codebase Cleanup Score</span>
              </div>
              
              <div className="relative flex items-center justify-center w-36 h-36 mb-4">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="72"
                    cy="72"
                    r="60"
                    stroke="#1e293b"
                    strokeWidth="10"
                    fill="transparent"
                  />
                  <circle
                    cx="72"
                    cy="72"
                    r="60"
                    stroke={
                      analyzerResult.cleanup_score > 80 ? '#10b981' :
                      analyzerResult.cleanup_score > 60 ? '#eab308' :
                      analyzerResult.cleanup_score > 40 ? '#f97316' : '#ef4444'
                    }
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray={376.8}
                    strokeDashoffset={376.8 - (376.8 * analyzerResult.cleanup_score) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-white tracking-tighter font-mono">
                    {analyzerResult.cleanup_score}
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    of 100
                  </span>
                </div>
              </div>

              <div className="mt-2 font-mono flex items-center gap-2 text-xs">
                {analyzerResult.previous_cleanup_score !== undefined && analyzerResult.previous_cleanup_score !== null ? (
                  <div className="text-slate-400 flex items-center gap-1">
                    <span>Previous Score:</span>
                    <span className="font-bold text-slate-300">{analyzerResult.previous_cleanup_score}</span>
                    <ArrowRight className="w-3 h-3" />
                    <span className={`font-bold ${analyzerResult.cleanup_score >= analyzerResult.previous_cleanup_score ? 'text-emerald-400' : 'text-red-400'}`}>
                      {analyzerResult.cleanup_score}
                    </span>
                  </div>
                ) : (
                  <span className="text-slate-500 italic">No historical records</span>
                )}
              </div>
            </div>

            {/* Top Recommendations */}
            <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col">
              <h3 className="text-base font-bold text-white mb-4 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-yellow-400" />
                <span>Top Cleanup Recommendations</span>
              </h3>

              {analyzerResult.cleanup_recommendations && analyzerResult.cleanup_recommendations.length > 0 ? (
                <ul className="flex flex-col gap-2.5 flex-grow">
                  {analyzerResult.cleanup_recommendations.map((recommendation, idx) => (
                    <li key={idx} className="flex gap-2.5 items-start font-mono text-xs bg-slate-950/40 border border-slate-850 p-3 rounded-lg hover:border-slate-700 transition-colors">
                      <span className="text-yellow-400 font-bold shrink-0 mt-0.5">[{idx + 1}]</span>
                      <span className="text-slate-200">{recommendation}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="flex-grow flex items-center justify-center text-xs font-mono text-slate-500 italic py-8">
                  Your codebase is clean! No recommendations found.
                </div>
              )}
            </div>

          </div>

          {/* Unused Files Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <FileCode className="w-5 h-5 text-indigo-400" />
              <span>Unused Files (In-Degree = 0)</span>
            </h3>
            
            {analyzerResult.unused_files && analyzerResult.unused_files.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase font-bold">
                      <th className="py-2.5">File Path</th>
                      <th className="py-2.5 text-center">Confidence</th>
                      <th className="py-2.5 text-center">Risk Level</th>
                      <th className="py-2.5">Actionable Advice</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {analyzerResult.unused_files.map((file, idx) => (
                      <tr key={idx} className="hover:bg-slate-950/20">
                        <td className="py-3 pr-2 break-all text-slate-200">{file.file_path}</td>
                        <td className="py-3 text-center text-slate-400">{(file.confidence * 100).toFixed(0)}%</td>
                        <td className="py-3 text-center">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getRiskColorClass(file.risk_level)}`}>
                            {file.risk_level}
                          </span>
                        </td>
                        <td className="py-3 text-slate-300 font-sans text-xs">{file.recommendation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs font-mono text-slate-500 italic">No unused root files identified.</p>
            )}
          </div>

          {/* Orphan Modules Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-orange-400" />
              <span>Orphan Modules (In-Degree &gt; 0)</span>
            </h3>
            
            {analyzerResult.orphan_modules && analyzerResult.orphan_modules.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left font-mono text-xs text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase font-bold">
                      <th className="py-2.5">Module Path</th>
                      <th className="py-2.5">Last Connected Reachable Module</th>
                      <th className="py-2.5 text-center">Confidence</th>
                      <th className="py-2.5 text-center">Risk Level</th>
                      <th className="py-2.5">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {analyzerResult.orphan_modules.map((mod, idx) => (
                      <tr key={idx} className="hover:bg-slate-950/20">
                        <td className="py-3 pr-2 break-all text-slate-200">{mod.file_path}</td>
                        <td className="py-3 pr-2 break-all">
                          {mod.last_reachable_parent ? (
                            <span className="bg-slate-850 border border-slate-750 px-2 py-0.5 rounded text-[10px] text-slate-400">
                              {mod.last_reachable_parent}
                            </span>
                          ) : (
                            <span className="text-slate-550 italic text-[10px]">None (Fully Isolated Component)</span>
                          )}
                        </td>
                        <td className="py-3 text-center text-slate-400">{(mod.confidence * 100).toFixed(0)}%</td>
                        <td className="py-3 text-center">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${getRiskColorClass(mod.risk_level)}`}>
                            {mod.risk_level}
                          </span>
                        </td>
                        <td className="py-3 text-slate-300 font-sans text-xs">{mod.recommendation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs font-mono text-slate-500 italic">No orphaned modules found.</p>
            )}
          </div>

          {/* Dead Dependency Chains Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-emerald-400" />
              <span>Dead Dependency Chains (Length &ge; 2)</span>
            </h3>
            
            {analyzerResult.dead_dependency_chains && analyzerResult.dead_dependency_chains.length > 0 ? (
              <div className="flex flex-col gap-4">
                {analyzerResult.dead_dependency_chains.map((c, idx) => (
                  <div key={idx} className="bg-slate-950/50 border border-slate-800 rounded-lg p-4 font-mono text-xs space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-850 pb-2">
                      <div className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Dead Chain #{idx + 1} ({c.total_nodes} nodes, {c.length} hops)</span>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] text-slate-500 font-bold uppercase">
                        <span>Max Centrality: <span className="text-slate-300">{c.max_centrality}</span></span>
                        <span>Confidence: <span className="text-slate-300">{(c.confidence * 100).toFixed(0)}%</span></span>
                        <span>Risk: <span className={`border px-1.5 py-0.25 rounded ${getRiskColorClass(c.risk_level)}`}>{c.risk_level}</span></span>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-2 text-slate-200 pt-1">
                      {c.chain.map((node, nodeIdx) => (
                        <React.Fragment key={nodeIdx}>
                          <span className="bg-slate-900 px-2.5 py-1 rounded border border-slate-800 text-slate-300 break-all">{node}</span>
                          {nodeIdx < c.chain.length - 1 && <ArrowRight className="w-3.5 h-3.5 text-slate-650 shrink-0" />}
                        </React.Fragment>
                      ))}
                    </div>
                    
                    <p className="text-xs text-slate-400 font-sans italic pt-1">{c.recommendation}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs font-mono text-slate-500 italic">No unreachable dependency chains identified.</p>
            )}
          </div>

        </div>
      )}

    </div>
  );
};

export default DeadCodeAnalyzer;
