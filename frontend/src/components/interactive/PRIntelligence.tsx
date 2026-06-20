import React, { useState, useEffect } from 'react';
import { apiUrl, extractErrorMessage } from '../../lib/api';
import { 
  GitPullRequest, 
  AlertTriangle, 
  Loader2, 
  CheckCircle2, 
  HelpCircle, 
  ShieldCheck, 
  ShieldAlert, 
  FileCode, 
  Code2, 
  TrendingUp, 
  Activity, 
  CornerDownRight, 
  Layers, 
  BookOpen, 
  Settings, 
  AlertOctagon 
} from 'lucide-react';

interface ChangedFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
}

interface SymbolChange {
  name: string;
  type: string;
  file_path: string;
  line_number: number;
  language: string;
  change_type: string;
  parent_class?: string;
}

interface PropagationPath {
  source: string;
  target: string;
  path: string[];
  depth: number;
}

interface RiskBreakdown {
  factor: string;
  score: number;
  detail: string;
}

interface ReviewFocusArea {
  area: string;
  reason: string;
  files: string[];
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
}

interface PRAnalysisResult {
  repo: string;
  pr_number: number;
  pr_url: string;
  pr_title: string;
  pr_state: string;
  pr_size: 'XS' | 'S' | 'M' | 'L' | 'XL';
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  risk_breakdown: RiskBreakdown[];
  top_risks: string[];
  changed_files: ChangedFile[];
  total_additions: number;
  total_deletions: number;
  added_symbols: SymbolChange[];
  modified_symbols: SymbolChange[];
  removed_symbols: SymbolChange[];
  affected_files: string[];
  impact_radius: number;
  blast_radius: 'LOW' | 'MEDIUM' | 'HIGH' | 'EXTREME';
  max_depth: number;
  propagation_paths: PropagationPath[];
  affected_components: string[];
  changed_entry_points: string[];
  changed_core_files: string[];
  changed_high_coupling_files: string[];
  review_focus_areas: ReviewFocusArea[];
  analyzed_at: string;
}

interface PRIntelligenceProps {
  repoName?: string;
}

export const PRIntelligence: React.FC<PRIntelligenceProps> = ({ repoName }) => {
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
  const [analysisResult, setAnalysisResult] = useState<PRAnalysisResult | null>(null);
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

  // Load diagnostics status on mount
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
    setAnalysisResult(null);

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
      const res = await fetch(apiUrl('/api/pr/analyze'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(extractErrorMessage(errorData));
      }

      const data = await res.json();
      setAnalysisResult(data);
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
    switch (level) {
      case 'CRITICAL': return 'bg-red-500/10 text-red-500 border-red-500/30';
      case 'HIGH': return 'bg-orange-500/10 text-orange-500 border-orange-500/30';
      case 'MEDIUM': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/30';
      default: return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30';
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL': return 'text-red-500';
      case 'HIGH': return 'text-orange-500';
      case 'MEDIUM': return 'text-yellow-500';
      default: return 'text-emerald-500';
    }
  };

  const getSizeBadgeColor = (size: string) => {
    switch (size) {
      case 'XL': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'L': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'M': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'S': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      default: return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  const hasPrerequisites = healthStatus
    ? healthStatus.analysis_exists && healthStatus.graph_available && healthStatus.symbol_index_available
    : true;

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto px-4 py-6 text-slate-100">
      
      {/* Upper diagnostics & inputs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Form panel */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
          <div className="flex items-center gap-3 mb-6">
            <GitPullRequest className="w-6 h-6 text-indigo-400" />
            <h2 className="text-xl font-bold tracking-tight text-white">Pull Request Intelligence</h2>
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
                  className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 placeholder-slate-600"
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
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-slate-400">Repository</label>
                  <input
                    type="text"
                    placeholder="Repo-Intelligence-Agent"
                    value={repoInput}
                    onChange={(e) => setRepoInput(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <label className="text-xs font-semibold text-slate-400">PR Number</label>
                  <input
                    type="text"
                    placeholder="1"
                    value={prNumberInput}
                    onChange={(e) => setPrNumberInput(e.target.value)}
                    className="bg-slate-950 border border-slate-800 text-slate-100 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-indigo-500 placeholder-slate-600"
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
                  Analyzing Pull Request...
                </>
              ) : 'Analyze Pull Request'}
            </button>
          </form>

          {errorMsg && (
            <div className="mt-4 flex gap-2.5 items-start bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-400">
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Health / Diagnostics panel */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4">
          <div className="flex items-center gap-2.5">
            <Settings className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold text-white">Diagnostics & Status</h3>
          </div>
          
          <div className="flex flex-col gap-3.5 text-sm">
            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
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

            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400 font-medium">GitHub Rate Limit</span>
              <span className="text-slate-200 font-semibold">
                {healthStatus?.rate_limit_remaining ?? '—'} left
              </span>
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400 font-medium">Dependency Graph</span>
              {healthStatus?.graph_available ? (
                <span className="text-emerald-400 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">Available</span>
              ) : (
                <span className="text-slate-400 font-semibold text-xs bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">Unavailable</span>
              )}
            </div>

            <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
              <span className="text-slate-400 font-medium">Symbol Index</span>
              {healthStatus?.symbol_index_available ? (
                <span className="text-emerald-400 font-semibold text-xs bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">Available</span>
              ) : (
                <span className="text-slate-400 font-semibold text-xs bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">Unavailable</span>
              )}
            </div>
            
            <div className="text-xs text-slate-500 leading-relaxed mt-1">
              Ensure the target repository is loaded and indexed via the main Repository Analysis page before requesting PR reports.
            </div>
          </div>
        </div>

      </div>

      {/* Main Analysis Results */}
      {analysisResult && (
        <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
          
          {/* PR Title Header */}
          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
            <div>
              <div className="flex items-center gap-2.5 mb-1.5">
                <span className="text-indigo-400 font-bold text-lg">#{analysisResult.pr_number}</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  {analysisResult.pr_state}
                </span>
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight">{analysisResult.pr_title}</h1>
              <p className="text-xs text-slate-500 mt-2 font-mono">Analyzed at {new Date(analysisResult.analyzed_at).toLocaleString()}</p>
            </div>
            <a
              href={analysisResult.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 border border-slate-700 hover:border-slate-500 hover:bg-slate-800/50 text-slate-300 font-semibold text-sm rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <GitPullRequest className="w-4 h-4" />
              View on GitHub
            </a>
          </div>

          {/* Grid for Risk Score, Level, Top Risks, Blast Radius & Size */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Risk Gauge Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between items-center text-center relative overflow-hidden">
              <div className="text-slate-400 font-semibold text-sm mb-4">Risk Assessment</div>
              
              <div className="relative flex items-center justify-center w-36 h-36 mb-4">
                {/* Simplified gauge stroke */}
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="72"
                    cy="72"
                    r="60"
                    className="stroke-slate-800 fill-transparent"
                    strokeWidth="8"
                  />
                  <circle
                    cx="72"
                    cy="72"
                    r="60"
                    className={`fill-transparent transition-all duration-1000 ${
                      analysisResult.risk_level === 'CRITICAL' ? 'stroke-red-500' :
                      analysisResult.risk_level === 'HIGH' ? 'stroke-orange-500' :
                      analysisResult.risk_level === 'MEDIUM' ? 'stroke-yellow-500' : 'stroke-emerald-500'
                    }`}
                    strokeWidth="8"
                    strokeDasharray={376.8}
                    strokeDashoffset={376.8 - (376.8 * analysisResult.risk_score) / 100}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="text-4xl font-extrabold text-white tracking-tight">{analysisResult.risk_score}</span>
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mt-0.5">out of 100</span>
                </div>
              </div>

              <div className={`px-4 py-1.5 border rounded-full text-xs font-bold uppercase tracking-wider ${getRiskColorClass(analysisResult.risk_level)}`}>
                {analysisResult.risk_level} Risk
              </div>
            </div>

            {/* Top Risks Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4 md:col-span-2">
              <div className="text-slate-400 font-semibold text-sm flex items-center gap-2">
                <AlertOctagon className="w-4 h-4 text-orange-400" />
                Key Risk Explanations
              </div>
              
              <div className="flex flex-col gap-3.5 my-auto">
                {analysisResult.top_risks.length > 0 ? (
                  analysisResult.top_risks.map((risk, idx) => (
                    <div key={idx} className="flex items-start gap-3 bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-sm">
                      <AlertTriangle className="w-4 h-4 text-orange-500 shrink-0 mt-0.5" />
                      <span className="text-slate-200 font-medium">{risk}</span>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-slate-500 gap-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500/60" />
                    <span className="text-sm font-medium">No critical risks detected in this change payload.</span>
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Size & Blast Radius Stat Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center gap-4">
              <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">PR Size</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xl font-bold text-white">{analysisResult.pr_size}</span>
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border uppercase ${getSizeBadgeColor(analysisResult.pr_size)}`}>
                    Score Model
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center gap-4">
              <div className="p-3 bg-orange-500/10 border border-orange-500/20 text-orange-400 rounded-lg">
                <Activity className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Blast Radius</div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xl font-bold text-white">{analysisResult.blast_radius}</span>
                  <span className="text-xs text-slate-400">({analysisResult.impact_radius} downstream)</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center gap-4">
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
                <FileCode className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Files Modified</div>
                <div className="text-xl font-bold text-white mt-1">
                  {analysisResult.changed_files.length} <span className="text-xs text-slate-400 font-normal">files touched</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex items-center gap-4">
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg">
                <Code2 className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Diff Summary</div>
                <div className="text-xl font-bold text-white mt-1">
                  <span className="text-emerald-400">+{analysisResult.total_additions}</span>
                  <span className="text-slate-400 mx-1">/</span>
                  <span className="text-red-400">-{analysisResult.total_deletions}</span>
                </div>
              </div>
            </div>

          </div>

          {/* Critical Architecture Changes Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4">
            <div className="text-slate-300 font-semibold text-sm flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <BookOpen className="w-4 h-4 text-indigo-400" />
              Critical Architecture Detections
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Entry points */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4 flex flex-col gap-2.5">
                <div className="text-xs font-bold uppercase tracking-wider text-red-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                  Entry Points Changed ({analysisResult.changed_entry_points.length})
                </div>
                <div className="flex flex-col gap-1.5 mt-1">
                  {analysisResult.changed_entry_points.length > 0 ? (
                    analysisResult.changed_entry_points.map((file, idx) => (
                      <span key={idx} className="font-mono text-xs text-slate-300 bg-slate-900 border border-slate-800/80 px-2.5 py-1.5 rounded break-all">{file}</span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic py-2">No entry point files modified.</span>
                  )}
                </div>
              </div>

              {/* Core modules */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4 flex flex-col gap-2.5">
                <div className="text-xs font-bold uppercase tracking-wider text-orange-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-400" />
                  Core Files Changed ({analysisResult.changed_core_files.length})
                </div>
                <div className="flex flex-col gap-1.5 mt-1">
                  {analysisResult.changed_core_files.length > 0 ? (
                    analysisResult.changed_core_files.map((file, idx) => (
                      <span key={idx} className="font-mono text-xs text-slate-300 bg-slate-900 border border-slate-800/80 px-2.5 py-1.5 rounded break-all">{file}</span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic py-2">No core modules modified.</span>
                  )}
                </div>
              </div>

              {/* High coupling modules */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-4 flex flex-col gap-2.5">
                <div className="text-xs font-bold uppercase tracking-wider text-yellow-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
                  High-Coupling Changed ({analysisResult.changed_high_coupling_files.length})
                </div>
                <div className="flex flex-col gap-1.5 mt-1">
                  {analysisResult.changed_high_coupling_files.length > 0 ? (
                    analysisResult.changed_high_coupling_files.map((file, idx) => (
                      <span key={idx} className="font-mono text-xs text-slate-300 bg-slate-900 border border-slate-800/80 px-2.5 py-1.5 rounded break-all">{file}</span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-500 italic py-2">No high-coupling files modified.</span>
                  )}
                </div>
              </div>

            </div>
          </div>

          {/* Review Focus Areas Checklist */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-4">
            <div className="text-slate-300 font-semibold text-sm flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Prioritized Review Focus Areas
            </div>
            
            <div className="flex flex-col gap-4">
              {analysisResult.review_focus_areas.length > 0 ? (
                analysisResult.review_focus_areas.map((area, idx) => (
                  <div key={idx} className="bg-slate-950/50 border border-slate-800 rounded-lg p-4 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-2.5">
                        <span className="font-bold text-white text-sm">{area.area}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          area.priority === 'HIGH' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                          area.priority === 'MEDIUM' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
                          'bg-slate-500/10 text-slate-400 border-slate-500/20'
                        }`}>
                          {area.priority}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">{area.reason}</p>
                    </div>
                    {area.files.length > 0 && (
                      <div className="flex flex-col gap-1 shrink-0 max-w-xs">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Target Files</span>
                        {area.files.map((file, fIdx) => (
                          <span key={fIdx} className="font-mono text-[10px] text-indigo-300 bg-slate-900 border border-slate-800/60 px-1.5 py-0.5 rounded truncate max-w-[200px]" title={file}>
                            {file.split('/').pop()}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center py-6 text-slate-500 text-sm italic">
                  No critical review checklist items triggered.
                </div>
              )}
            </div>
          </div>

          {/* Changed Files & Symbol Diffs Details Tab Section */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col gap-5">
            <h3 className="text-lg font-bold text-white pb-3 border-b border-slate-800">Files and Symbol Modificative Details</h3>
            
            <div className="flex flex-col gap-6">
              
              {/* Changed Files list */}
              <div>
                <div className="text-slate-400 font-semibold text-xs uppercase tracking-wider mb-3">Changed Files List ({analysisResult.changed_files.length})</div>
                <div className="max-h-72 overflow-y-auto border border-slate-800/80 rounded-lg bg-slate-950/40">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-900 border-b border-slate-800 text-slate-400">
                        <th className="p-3">File Path</th>
                        <th className="p-3 text-center">Status</th>
                        <th className="p-3 text-right">Additions</th>
                        <th className="p-3 text-right">Deletions</th>
                        <th className="p-3 text-right">Changes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {analysisResult.changed_files.map((file, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/50">
                          <td className="p-3 font-mono text-slate-300 truncate max-w-md">{file.filename}</td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              file.status === 'added' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                              file.status === 'removed' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                              'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                            }`}>
                              {file.status}
                            </span>
                          </td>
                          <td className="p-3 text-right text-emerald-400 font-medium">+{file.additions}</td>
                          <td className="p-3 text-right text-red-400 font-medium">-{file.deletions}</td>
                          <td className="p-3 text-right text-slate-300 font-semibold">{file.changes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Collapsible Symbols Panels */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Added symbols */}
                <div className="border border-slate-800 rounded-lg p-4 bg-slate-950/30 flex flex-col gap-3">
                  <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex justify-between items-center pb-2 border-b border-slate-800/80">
                    <span>Symbols Added</span>
                    <span className="bg-emerald-500/10 px-2 py-0.5 rounded text-[10px]">{analysisResult.added_symbols.length}</span>
                  </div>
                  <div className="max-h-56 overflow-y-auto flex flex-col gap-2 mt-1">
                    {analysisResult.added_symbols.length > 0 ? (
                      analysisResult.added_symbols.map((sym, idx) => (
                        <div key={idx} className="bg-slate-900 border border-slate-850 px-2.5 py-2 rounded text-xs flex flex-col gap-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white font-mono break-all">{sym.name}</span>
                            <span className="text-[9px] text-slate-500 uppercase">{sym.type}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono truncate">{sym.file_path.split('/').pop()}:{sym.line_number}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-600 text-xs italic py-2">No added symbols extracted.</div>
                    )}
                  </div>
                </div>

                {/* Modified symbols */}
                <div className="border border-slate-800 rounded-lg p-4 bg-slate-950/30 flex flex-col gap-3">
                  <div className="text-xs font-bold text-indigo-400 uppercase tracking-wider flex justify-between items-center pb-2 border-b border-slate-800/80">
                    <span>Symbols Modified</span>
                    <span className="bg-indigo-500/10 px-2 py-0.5 rounded text-[10px]">{analysisResult.modified_symbols.length}</span>
                  </div>
                  <div className="max-h-56 overflow-y-auto flex flex-col gap-2 mt-1">
                    {analysisResult.modified_symbols.length > 0 ? (
                      analysisResult.modified_symbols.map((sym, idx) => (
                        <div key={idx} className="bg-slate-900 border border-slate-850 px-2.5 py-2 rounded text-xs flex flex-col gap-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white font-mono break-all">{sym.name}</span>
                            <span className="text-[9px] text-slate-500 uppercase">{sym.type}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono truncate">{sym.file_path.split('/').pop()}:{sym.line_number}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-600 text-xs italic py-2">No modified symbols found.</div>
                    )}
                  </div>
                </div>

                {/* Removed symbols */}
                <div className="border border-slate-800 rounded-lg p-4 bg-slate-950/30 flex flex-col gap-3">
                  <div className="text-xs font-bold text-red-400 uppercase tracking-wider flex justify-between items-center pb-2 border-b border-slate-800/80">
                    <span>Symbols Removed</span>
                    <span className="bg-red-500/10 px-2 py-0.5 rounded text-[10px]">{analysisResult.removed_symbols.length}</span>
                  </div>
                  <div className="max-h-56 overflow-y-auto flex flex-col gap-2 mt-1">
                    {analysisResult.removed_symbols.length > 0 ? (
                      analysisResult.removed_symbols.map((sym, idx) => (
                        <div key={idx} className="bg-slate-900 border border-slate-850 px-2.5 py-2 rounded text-xs flex flex-col gap-0.5">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-white font-mono break-all">{sym.name}</span>
                            <span className="text-[9px] text-slate-500 uppercase">{sym.type}</span>
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono truncate">{sym.file_path.split('/').pop()}:{sym.line_number}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-600 text-xs italic py-2">No removed symbols detected.</div>
                    )}
                  </div>
                </div>

              </div>

              {/* Transit Paths section */}
              <div>
                <div className="text-slate-400 font-semibold text-xs uppercase tracking-wider mb-3">Dependency Propagation Paths ({analysisResult.propagation_paths.length})</div>
                <div className="flex flex-col gap-2">
                  {analysisResult.propagation_paths.length > 0 ? (
                    analysisResult.propagation_paths.map((path, idx) => (
                      <div key={idx} className="bg-slate-950/40 border border-slate-800 rounded-lg p-3 text-xs">
                        <div className="flex justify-between items-center mb-2.5 text-slate-500 font-semibold">
                          <span className="flex items-center gap-1">Path #{idx + 1}</span>
                          <span>{path.depth} hops</span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          {path.path.map((node, nIdx) => (
                            <React.Fragment key={nIdx}>
                              {nIdx > 0 && <CornerDownRight className="w-3.5 h-3.5 text-indigo-400 shrink-0 transform -rotate-90" />}
                              <span className={`font-mono px-2 py-1 rounded text-[10px] ${
                                nIdx === 0 ? 'bg-slate-900 border border-slate-700 text-slate-300 font-bold' :
                                nIdx === path.path.length - 1 ? 'bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-bold' :
                                'bg-slate-950 border border-slate-850 text-slate-400'
                              }`}>
                                {node.split('/').pop()}
                              </span>
                            </React.Fragment>
                          ))}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-500 text-xs italic py-3 text-center border border-dashed border-slate-800 rounded-lg bg-slate-950/20">
                      No multi-level import cascades found.
                    </div>
                  )}
                </div>
              </div>

            </div>
          </div>

        </div>
      )}

    </div>
  );
};
