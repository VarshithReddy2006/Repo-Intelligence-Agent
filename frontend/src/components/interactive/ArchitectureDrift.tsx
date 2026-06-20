import React, { useState, useEffect } from 'react';
import { apiUrl, extractErrorMessage } from '../../lib/api';
import {
  GitPullRequest,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  ShieldCheck,
  ShieldAlert,
  Settings,
  Activity,
  Award,
  Zap,
  RefreshCw,
  Plus,
  Minus,
  DoorOpen,
  ArrowRight,
  Sparkles
} from 'lucide-react';

interface DependencyEdge {
  source: string;
  target: string;
}

interface CouplingChange {
  file: string;
  before: number;
  after: number;
}

interface PRDriftResult {
  repo: string;
  pr_number: number;
  architecture_risk_score: number;
  architecture_risk_level: string;
  architecture_improvement_score: number;
  top_findings: string[];
  drift_categories: string[];
  architectural_hotspots: string[];
  added_dependencies: DependencyEdge[];
  removed_dependencies: DependencyEdge[];
  new_cycles: string[][];
  resolved_cycles: string[][];
  coupling_increase: CouplingChange[];
  coupling_decrease: CouplingChange[];
  new_entry_points: string[];
  removed_entry_points: string[];
  analyzed_at: string;
}

interface ArchitectureDriftProps {
  repoName?: string;
}

export const ArchitectureDrift: React.FC<ArchitectureDriftProps> = ({ repoName }) => {
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

  const [prUrlInput, setPrUrlInput] = useState('');
  const [ownerInput, setOwnerInput] = useState('');
  const [repoInput, setRepoInput] = useState('');
  const [prNumberInput, setPrNumberInput] = useState('');
  const [useUrl, setUseUrl] = useState(true);

  const [isLoading, setIsLoading] = useState(false);
  const [driftResult, setDriftResult] = useState<PRDriftResult | null>(null);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');
    setDriftResult(null);

    const payload: any = {};
    if (useUrl) {
      if (!prUrlInput.trim()) {
        setErrorMsg('Please enter a GitHub Pull Request URL.');
        setIsLoading(false);
        return;
      }
      payload.pr_url = prUrlInput.trim();
    } else {
      if (!ownerInput.trim() || !repoInput.trim() || !prNumberInput.trim()) {
        setErrorMsg('Please fill in Owner, Repo, and PR Number.');
        setIsLoading(false);
        return;
      }
      payload.owner = ownerInput.trim();
      payload.repo = repoInput.trim();
      payload.pr_number = parseInt(prNumberInput.trim());
    }

    try {
      const res = await fetch(apiUrl('/api/architecture/drift'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(extractErrorMessage(errorData));
      }

      const data = await res.json();
      setDriftResult(data);
      if (data.repo) {
        setActiveRepo(data.repo);
      }
    } catch (err: any) {
      setErrorMsg(extractErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColorClass = (level: string) => {
    switch (level.toUpperCase()) {
      case 'CRITICAL': return 'bg-red-500/10 text-red-500 border-red-500/30';
      case 'HIGH': return 'bg-orange-500/10 text-orange-500 border-orange-500/30';
      case 'MEDIUM': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30';
      default: return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30';
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'CRITICAL': return 'text-red-500';
      case 'HIGH': return 'text-orange-500';
      case 'MEDIUM': return 'text-yellow-500';
      default: return 'text-emerald-500';
    }
  };

  const getCategoryLabelAndStyle = (cat: string) => {
    switch (cat.toUpperCase()) {
      case 'CYCLE_INTRODUCED': return { label: 'Cycle Introduced', style: 'bg-red-500/10 text-red-400 border-red-500/30' };
      case 'CYCLE_RESOLVED': return { label: 'Cycle Resolved', style: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' };
      case 'COUPLING_INCREASED': return { label: 'Coupling Increased', style: 'bg-orange-500/10 text-orange-400 border-orange-500/30' };
      case 'COUPLING_DECREASED': return { label: 'Coupling Decreased', style: 'bg-teal-500/10 text-teal-400 border-teal-500/30' };
      case 'ENTRY_POINT_ADDED': return { label: 'Entry Point Added', style: 'bg-blue-500/10 text-blue-400 border-blue-500/30' };
      case 'ENTRY_POINT_REMOVED': return { label: 'Entry Point Removed', style: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30' };
      case 'DEPENDENCY_ADDED': return { label: 'Dependency Added', style: 'bg-purple-500/10 text-purple-400 border-purple-500/30' };
      case 'DEPENDENCY_REMOVED': return { label: 'Dependency Removed', style: 'bg-slate-500/10 text-slate-400 border-slate-500/30' };
      default: return { label: cat.replace('_', ' '), style: 'bg-slate-500/10 text-slate-400 border-slate-500/30' };
    }
  };

  const hasPrerequisites = healthStatus
    ? healthStatus.analysis_exists && healthStatus.graph_available && healthStatus.symbol_index_available
    : true;

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto px-4 py-6 text-slate-100">
      
      {/* Input panel & Diagnostics panel side-by-side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Form panel */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-6">
            <GitPullRequest className="w-6 h-6 text-indigo-400" />
            <h2 className="text-xl font-bold tracking-tight text-white">Architecture Drift Detection</h2>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex gap-4 border-b border-slate-800 pb-3">
              <button
                type="button"
                onClick={() => setUseUrl(true)}
                className={`text-sm font-semibold pb-2 border-b-2 transition-colors ${
                  useUrl ? 'text-indigo-400 border-indigo-400' : 'text-slate-400 border-transparent hover:text-slate-200'
                }`}
              >
                PR URL
              </button>
              <button
                type="button"
                onClick={() => setUseUrl(false)}
                className={`text-sm font-semibold pb-2 border-b-2 transition-colors ${
                  !useUrl ? 'text-indigo-400 border-indigo-400' : 'text-slate-400 border-transparent hover:text-slate-200'
                }`}
              >
                Repository Coordinates
              </button>
            </div>

            {useUrl ? (
              <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-slate-400">GitHub Pull Request URL</label>
                <input
                  type="text"
                  placeholder="https://github.com/VarshithReddy2006/Repo-Intelligence-Agent/pull/1"
                  value={prUrlInput}
                  onChange={(e) => setPrUrlInput(e.target.value)}
                  className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 placeholder-slate-600 font-mono"
                />
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-4">
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-slate-400">Owner</label>
                  <input
                    type="text"
                    placeholder="VarshithReddy2006"
                    value={ownerInput}
                    onChange={(e) => setOwnerInput(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600 font-mono"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-slate-400">Repository</label>
                  <input
                    type="text"
                    placeholder="Repo-Intelligence-Agent"
                    value={repoInput}
                    onChange={(e) => setRepoInput(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600 font-mono"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-slate-400">PR Number</label>
                  <input
                    type="text"
                    placeholder="1"
                    value={prNumberInput}
                    onChange={(e) => setPrNumberInput(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600 font-mono"
                  />
                </div>
              </div>
            )}

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

            <button
              type="submit"
              disabled={isLoading || !hasPrerequisites}
              className="mt-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:bg-indigo-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-lg py-2.5 flex items-center justify-center gap-2 transition-all shadow-md shadow-indigo-600/10 cursor-pointer"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Analyzing Architecture Drift...
                </>
              ) : 'Analyze Drift'}
            </button>
          </form>

          {errorMsg && (
            <div className="mt-4 flex gap-2.5 items-start bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400 font-mono">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Health / Diagnostics panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <Settings className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold text-white">System Diagnostics</h3>
          </div>
          
          <div className="flex flex-col gap-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60 font-mono text-xs">
              <span className="text-slate-400 font-medium">GitHub Token Status</span>
              {healthStatus?.github_token ? (
                <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  <ShieldCheck className="w-3.5 h-3.5" /> Active
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-red-400 font-semibold text-xs bg-red-500/10 border border-red-500/30 px-2 py-0.5 rounded-full">
                  <ShieldAlert className="w-3.5 h-3.5" /> Inactive
                </span>
              )}
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60 font-mono text-xs">
              <span className="text-slate-400 font-medium">GitHub Rate Limit</span>
              <span className="text-slate-200 font-semibold">
                {healthStatus?.rate_limit_remaining ?? '—'} remaining
              </span>
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60 font-mono text-xs">
              <span className="text-slate-400 font-medium">Dependency Graph</span>
              {healthStatus?.graph_available ? (
                <span className="text-emerald-400 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">Available</span>
              ) : (
                <span className="text-slate-400 font-semibold text-xs bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">Unavailable</span>
              )}
            </div>

            <div className="text-xs text-slate-500 leading-relaxed mt-1 font-sans">
              Architecture drift detects cycles, coupling changes, and structural degradation by comparing the baseline indexed graph against modifications in this PR.
            </div>
          </div>
        </div>

      </div>

      {/* Main Analysis Results */}
      {driftResult && (
        <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          
          {/* PR Info Header */}
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <div>
              <div className="flex items-center gap-2.5 mb-1.5">
                <span className="text-indigo-400 font-bold text-lg">#{driftResult.pr_number}</span>
                <span className="text-xs font-mono bg-slate-800 border border-slate-700 px-2.5 py-0.5 rounded-full">
                  Architecture Drift Delta
                </span>
              </div>
              <h1 className="text-xl font-bold text-white tracking-tight font-mono">{driftResult.repo}</h1>
              <p className="text-xs text-slate-500 mt-2 font-mono">Analyzed at {new Date(driftResult.analyzed_at).toLocaleString()}</p>
            </div>

            {/* Badges container */}
            <div className="flex flex-wrap gap-2 sm:max-w-md justify-start sm:justify-end">
              {driftResult.drift_categories && driftResult.drift_categories.map((cat, idx) => {
                const badge = getCategoryLabelAndStyle(cat);
                return (
                  <span key={idx} className={`text-xs font-semibold px-2.5 py-1 rounded-md border font-mono ${badge.style}`}>
                    {badge.label}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Grid for Risk Score Gauge and Improvement Score Gauge */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Risk Gauge Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between items-center text-center relative overflow-hidden">
              <div className="text-slate-400 font-bold text-sm mb-4 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-orange-400" />
                <span>Architecture Risk Score</span>
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
                      driftResult.architecture_risk_score > 75 ? '#ef4444' :
                      driftResult.architecture_risk_score > 50 ? '#f97316' :
                      driftResult.architecture_risk_score > 25 ? '#eab308' : '#10b981'
                    }
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray={376.8}
                    strokeDashoffset={376.8 - (376.8 * driftResult.architecture_risk_score) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-white tracking-tighter font-mono">
                    {driftResult.architecture_risk_score}
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    of 100
                  </span>
                </div>
              </div>

              <div className="mt-2 font-mono">
                <span className="text-xs text-slate-400">Risk Severity: </span>
                <span className={`text-sm font-extrabold ${getRiskLevelColor(driftResult.architecture_risk_level)}`}>
                  {driftResult.architecture_risk_level}
                </span>
              </div>
            </div>

            {/* Improvement Gauge Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between items-center text-center relative overflow-hidden">
              <div className="text-slate-400 font-bold text-sm mb-4 uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Award className="w-4 h-4 text-emerald-400" />
                <span>Architecture Improvement Score</span>
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
                    stroke="#10b981"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray={376.8}
                    strokeDashoffset={376.8 - (376.8 * driftResult.architecture_improvement_score) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-3xl font-extrabold text-white tracking-tighter font-mono">
                    {driftResult.architecture_improvement_score}
                  </span>
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                    of 100
                  </span>
                </div>
              </div>

              <div className="mt-2 font-mono flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                <span className="text-xs text-slate-400">
                  {driftResult.architecture_improvement_score > 50 ? 'High Refactor Quality' : 
                   driftResult.architecture_improvement_score > 20 ? 'Moderate Improvements' : 'No Significant Improvements'}
                </span>
              </div>
            </div>

          </div>

          {/* Top Findings Panel */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-white mb-4 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <Zap className="w-5 h-5 text-indigo-400" />
              <span>Prioritized Top Findings</span>
            </h3>

            {driftResult.top_findings && driftResult.top_findings.length > 0 ? (
              <ul className="flex flex-col gap-2.5">
                {driftResult.top_findings.map((finding, idx) => (
                  <li key={idx} className="flex gap-2.5 items-start font-mono text-xs bg-slate-950/40 border border-slate-800/80 p-3 rounded-lg hover:border-slate-700 transition-colors">
                    <span className="text-indigo-400 font-bold shrink-0 mt-0.5">[{idx + 1}]</span>
                    <span className="text-slate-200">{finding}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs font-mono text-slate-500 italic">No significant architectural changes detected.</p>
            )}
          </div>

          {/* Architectural Hotspots */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <span>Architectural Hotspots Impacted</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4 font-sans">
              Hotspots represent key modules at the intersection of entry points, core codebases, high centrality nodes, and top coupling nodes. Changes in these files increase regression risk.
            </p>

            {driftResult.architectural_hotspots && driftResult.architectural_hotspots.length > 0 ? (
              <div className="flex flex-wrap gap-2.5">
                {driftResult.architectural_hotspots.map((hotspot, idx) => (
                  <div key={idx} className="flex items-center gap-2 font-mono text-xs bg-red-950/20 border border-red-900/40 px-3 py-2 rounded-lg text-red-300">
                    <Zap className="w-3.5 h-3.5 text-red-400 shrink-0" />
                    <span>{hotspot}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs font-mono text-slate-500 italic">No modified architectural hotspots impacted by this PR.</p>
            )}
          </div>

          {/* Cycles Panel (New vs Resolved) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* New Cycles */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-red-400 animate-spin-slow" />
                <span className="text-red-400">New Cycles Introduced</span>
              </h3>
              
              {driftResult.new_cycles && driftResult.new_cycles.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {driftResult.new_cycles.map((cycle, idx) => (
                    <div key={idx} className="bg-slate-950/50 border border-slate-800 rounded-lg p-3 font-mono text-xs">
                      <div className="text-[10px] text-red-400 font-bold uppercase tracking-wider mb-2">Cycle Loop #{idx + 1}</div>
                      <div className="flex flex-wrap items-center gap-1.5 text-slate-200">
                        {cycle.map((node, nIdx) => (
                          <React.Fragment key={nIdx}>
                            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-300 break-all">{node}</span>
                            {nIdx < cycle.length - 1 && <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />}
                          </React.Fragment>
                        ))}
                        <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-300 break-all">{cycle[0]}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">Clean build. No new dependency cycles introduced.</p>
              )}
            </div>

            {/* Resolved Cycles */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400">Resolved Cycles (Cleaned Up)</span>
              </h3>
              
              {driftResult.resolved_cycles && driftResult.resolved_cycles.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {driftResult.resolved_cycles.map((cycle, idx) => (
                    <div key={idx} className="bg-slate-950/50 border border-slate-800 rounded-lg p-3 font-mono text-xs">
                      <div className="text-[10px] text-emerald-400 font-bold uppercase tracking-wider mb-2">Resolved Loop #{idx + 1}</div>
                      <div className="flex flex-wrap items-center gap-1.5 text-slate-200">
                        {cycle.map((node, nIdx) => (
                          <React.Fragment key={nIdx}>
                            <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-300 break-all">{node}</span>
                            {nIdx < cycle.length - 1 && <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />}
                          </React.Fragment>
                        ))}
                        <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                        <span className="bg-slate-900 px-2 py-1 rounded border border-slate-800 text-slate-300 break-all">{cycle[0]}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No existing dependency cycles resolved.</p>
              )}
            </div>

          </div>

          {/* Coupling Changes Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Coupling Increases */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Plus className="w-4 h-4 text-orange-400" />
                <span className="text-orange-400 font-bold">Node Coupling Increases</span>
              </h3>
              
              {driftResult.coupling_increase && driftResult.coupling_increase.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-xs text-slate-300">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase font-bold">
                        <th className="py-2.5">Affected File</th>
                        <th className="py-2.5 text-center">Degree Before</th>
                        <th className="py-2.5 text-center">Degree After</th>
                        <th className="py-2.5 text-center">Shift</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {driftResult.coupling_increase.map((c, idx) => (
                        <tr key={idx} className="hover:bg-slate-950/20">
                          <td className="py-3 pr-2 break-all text-slate-200">{c.file}</td>
                          <td className="py-3 text-center">{c.before}</td>
                          <td className="py-3 text-center text-orange-400 font-semibold">{c.after}</td>
                          <td className="py-3 text-center font-bold text-orange-400">+{c.after - c.before}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No significant coupling increases detected.</p>
              )}
            </div>

            {/* Coupling Decreases */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Minus className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 font-bold">Node Coupling Decreases</span>
              </h3>
              
              {driftResult.coupling_decrease && driftResult.coupling_decrease.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left font-mono text-xs text-slate-300">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-500 text-[10px] uppercase font-bold">
                        <th className="py-2.5">Cleaned File</th>
                        <th className="py-2.5 text-center">Degree Before</th>
                        <th className="py-2.5 text-center">Degree After</th>
                        <th className="py-2.5 text-center">Shift</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/40">
                      {driftResult.coupling_decrease.map((c, idx) => (
                        <tr key={idx} className="hover:bg-slate-950/20">
                          <td className="py-3 pr-2 break-all text-slate-200">{c.file}</td>
                          <td className="py-3 text-center">{c.before}</td>
                          <td className="py-3 text-center text-emerald-400 font-semibold">{c.after}</td>
                          <td className="py-3 text-center font-bold text-emerald-400">-{c.before - c.after}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No coupling decreases (cleanups) observed.</p>
              )}
            </div>

          </div>

          {/* Dependency Delta (Added vs Removed edges) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Added dependencies */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Plus className="w-4 h-4 text-purple-400" />
                <span className="text-purple-400">Dependency Links Added</span>
              </h3>
              
              {driftResult.added_dependencies && driftResult.added_dependencies.length > 0 ? (
                <div className="flex flex-col gap-2.5 max-h-96 overflow-y-auto pr-1">
                  {driftResult.added_dependencies.map((edge, idx) => (
                    <div key={idx} className="bg-slate-950/30 border border-slate-850 p-2.5 rounded-lg flex items-center justify-between gap-4 font-mono text-xs">
                      <div className="break-all text-slate-300">{edge.source}</div>
                      <ArrowRight className="w-4 h-4 text-slate-500 shrink-0" />
                      <div className="break-all text-slate-300 text-right">{edge.target}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No new dependency edges established.</p>
              )}
            </div>

            {/* Removed dependencies */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Minus className="w-4 h-4 text-slate-400" />
                <span className="text-slate-400">Dependency Links Removed</span>
              </h3>
              
              {driftResult.removed_dependencies && driftResult.removed_dependencies.length > 0 ? (
                <div className="flex flex-col gap-2.5 max-h-96 overflow-y-auto pr-1">
                  {driftResult.removed_dependencies.map((edge, idx) => (
                    <div key={idx} className="bg-slate-950/30 border border-slate-850 p-2.5 rounded-lg flex items-center justify-between gap-4 font-mono text-xs">
                      <div className="break-all text-slate-400">{edge.source}</div>
                      <ArrowRight className="w-4 h-4 text-slate-600 shrink-0" />
                      <div className="break-all text-slate-400 text-right">{edge.target}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No dependency edges deleted.</p>
              )}
            </div>

          </div>

          {/* Entry Point Changes */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Added Entry Points */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <DoorOpen className="w-4 h-4 text-blue-400 animate-pulse" />
                <span className="text-blue-400">New Entry Points Added</span>
              </h3>
              
              {driftResult.new_entry_points && driftResult.new_entry_points.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {driftResult.new_entry_points.map((ep, idx) => (
                    <li key={idx} className="font-mono text-xs bg-slate-950/40 border border-slate-850 p-2.5 rounded-lg text-slate-200 break-all">
                      {ep}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No new modules qualified as application entry points.</p>
              )}
            </div>

            {/* Removed Entry Points */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
              <h3 className="text-base font-bold text-white mb-3 font-mono uppercase tracking-wider border-b border-slate-800 pb-2 flex items-center gap-2">
                <Minus className="w-4 h-4 text-slate-400" />
                <span className="text-slate-400 font-bold">Entry Points Removed</span>
              </h3>
              
              {driftResult.removed_entry_points && driftResult.removed_entry_points.length > 0 ? (
                <ul className="flex flex-col gap-2">
                  {driftResult.removed_entry_points.map((ep, idx) => (
                    <li key={idx} className="font-mono text-xs bg-slate-950/40 border border-slate-850 p-2.5 rounded-lg text-slate-400 break-all">
                      {ep}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs font-mono text-slate-500 italic">No existing application entry points were removed.</p>
              )}
            </div>

          </div>

        </div>
      )}

    </div>
  );
};

export default ArchitectureDrift;
