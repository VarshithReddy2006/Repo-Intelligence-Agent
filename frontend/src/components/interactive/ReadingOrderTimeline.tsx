import React, { useState, useEffect } from 'react';
import { apiUrl } from '../../lib/api';
import { 
  BookOpen, 
  Clock, 
  CheckCircle2, 
  Circle, 
  ArrowDown, 
  Layers, 
  Info, 
  X, 
  ExternalLink, 
  MessageSquare, 
  GitMerge,
  ChevronRight
} from 'lucide-react';

interface ReadingOrderEntry {
  rank: number;
  file_path: string;
  reason: string;
  tier: string;
  score: number;
}

interface ReadingOrder {
  repo: string;
  ordered_files: ReadingOrderEntry[];
  reasoning: string[];
  estimated_reading_time: number;
  total_files_ranked: number;
}

interface TimelineProps {
  repoName: string;
}

export const ReadingOrderTimeline: React.FC<TimelineProps> = ({ repoName }) => {
  const [readingPath, setReadingPath] = useState<ReadingOrder | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Progress tracking states
  const [completedFiles, setCompletedFiles] = useState<Record<string, boolean>>({});
  const [selectedFile, setSelectedFile] = useState<ReadingOrderEntry | null>(null);

  // 1. Fetch reading order data (lazy loaded on mount)
  useEffect(() => {
    const fetchReadingOrder = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(apiUrl('/api/reading-order'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ repo: repoName })
        });
        
        if (!response.ok) {
          throw new Error(await response.text() || 'Failed to fetch reading path');
        }
        
        const data = await response.json();
        setReadingPath(data);
        
        // 2. Load completed progress from localStorage
        const storageKey = `reading-path-${repoName}`;
        const storedProgress = localStorage.getItem(storageKey);
        if (storedProgress) {
          try {
            setCompletedFiles(JSON.parse(storedProgress));
          } catch (e) {
            console.error('Failed to parse progress from localStorage', e);
          }
        } else {
          setCompletedFiles({});
        }
      } catch (err: any) {
        console.error(err);
        setError(err.message || 'An error occurred generating the reading order.');
      } finally {
        setLoading(false);
      }
    };

    if (repoName) {
      fetchReadingOrder();
    }
  }, [repoName]);

  // Handle step completion toggle
  const handleToggleComplete = (filePath: string) => {
    const updated = {
      ...completedFiles,
      [filePath]: !completedFiles[filePath]
    };
    setCompletedFiles(updated);
    
    // Persist to localStorage
    const storageKey = `reading-path-${repoName}`;
    localStorage.setItem(storageKey, JSON.stringify(updated));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 font-mono text-xs text-text-muted gap-3">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
        <span>Generating Reading Path...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 font-mono text-xs text-text-muted gap-3 border border-border bg-card/5 rounded-lg p-6 text-center">
        <Info className="h-6 w-6 text-primary animate-pulse" />
        <span>{error}</span>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 text-primary border border-primary/20 px-3 py-1.5 rounded hover:bg-primary/5 transition-colors"
        >
          Retry Loading
        </button>
      </div>
    );
  }

  if (!readingPath || !readingPath.ordered_files || readingPath.ordered_files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 font-mono text-xs text-text-muted border border-border bg-card/5 rounded-lg p-6">
        <Info className="h-5 w-5 text-primary mb-2" />
        <span>No ranked source code files found for this repository.</span>
      </div>
    );
  }

  const { ordered_files, estimated_reading_time } = readingPath;
  const totalFiles = ordered_files.length;
  
  // Calculate completed counts
  const completedCount = Object.keys(completedFiles).filter(
    (key) => completedFiles[key] && ordered_files.some((f) => f.file_path === key)
  ).length;

  const progressPct = totalFiles > 0 ? (completedCount / totalFiles) * 100 : 0;

  // Generate ASCII retro progress bar (15 character width)
  const totalBlocks = 15;
  const filledBlocks = Math.round((completedCount / totalFiles) * totalBlocks);
  const emptyBlocks = totalBlocks - filledBlocks;
  const asciiProgress = '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);

  // Count metrics
  const entryPointsCount = ordered_files.filter((f) => f.tier === 'entry_point').length;
  const coreModulesCount = ordered_files.filter((f) => f.tier === 'core').length;

  // Dynamic estimated minutes per file calculation
  const getFileReadingTime = (score: number) => {
    return Math.max(1, Math.round(score / 20));
  };

  // Importance tier categorization
  const getImportanceLevel = (score: number) => {
    if (score > 100) return { label: 'Critical', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10' };
    if (score > 50) return { label: 'Important', color: 'text-blue-400 border-blue-500/20 bg-blue-500/10' };
    return { label: 'Optional', color: 'text-zinc-400 border-zinc-700 bg-zinc-800/50' };
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 relative">
      <div className={`${selectedFile ? 'lg:col-span-8' : 'lg:col-span-12'} space-y-6 transition-all duration-300`}>
        {/* Onboarding Guide Summary Panel */}
        <div className="border border-border bg-card/10 rounded-lg p-5 space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-border/40 pb-3">
            <div>
              <h2 className="text-xs font-bold text-text-muted uppercase tracking-wider font-mono flex items-center gap-1.5">
                <BookOpen className="h-4 w-4 text-primary" /> Repository Onboarding Guide
              </h2>
              <p className="text-[10px] text-text-muted font-sans mt-0.5">
                Calculated step-by-step reading flow prioritizing entry points and core library modules.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono bg-primary/10 border border-primary/20 px-2 py-0.5 rounded text-primary flex items-center gap-1">
                <Clock className="h-3.5 w-3.5" />
                <span>{estimated_reading_time} MIN TOTAL</span>
              </span>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs text-center">
            <div className="border border-border bg-canvas/30 rounded p-3">
              <span className="text-text-muted block text-[9px] uppercase">Recommended Files</span>
              <span className="text-text text-base font-bold block mt-1">{totalFiles}</span>
            </div>
            <div className="border border-border bg-canvas/30 rounded p-3">
              <span className="text-text-muted block text-[9px] uppercase">Est. Reading Time</span>
              <span className="text-text text-base font-bold block mt-1">{estimated_reading_time}m</span>
            </div>
            <div className="border border-border bg-canvas/30 rounded p-3">
              <span className="text-text-muted block text-[9px] uppercase">Entry Points</span>
              <span className="text-text text-base font-bold block mt-1 text-emerald-400">{entryPointsCount}</span>
            </div>
            <div className="border border-border bg-canvas/30 rounded p-3">
              <span className="text-text-muted block text-[9px] uppercase">Core Modules</span>
              <span className="text-text text-base font-bold block mt-1 text-blue-400">{coreModulesCount}</span>
            </div>
          </div>

          {/* Progress Tracker UX */}
          <div className="border-t border-border/40 pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider block font-mono">Progress Tracking</span>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-primary font-semibold">{asciiProgress}</span>
                <span className="text-text-muted">{completedCount} / {totalFiles} Files Completed</span>
              </div>
            </div>

            {/* Visual HTML Progress Bar */}
            <div className="flex-grow max-w-xs bg-zinc-800 border border-border h-3.5 rounded overflow-hidden relative self-center w-full hidden sm:block">
              <div 
                className="bg-primary h-full transition-all duration-500 ease-out" 
                style={{ width: `${progressPct}%` }}
              ></div>
              <span className="absolute inset-0 flex items-center justify-center text-[9px] font-mono text-text font-bold mix-blend-difference">
                {Math.round(progressPct)}%
              </span>
            </div>
          </div>
        </div>

        {/* Dynamic Timeline steps */}
        <div className="space-y-4 relative pl-6 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-zinc-800">
          {ordered_files.map((entry, idx) => {
            const isCompleted = !!completedFiles[entry.file_path];
            const estMinutes = getFileReadingTime(entry.score);
            const importance = getImportanceLevel(entry.score);
            
            return (
              <div key={entry.file_path} className="relative space-y-2 group">
                {/* Timeline node circle indicator */}
                <div 
                  className={`absolute -left-[24px] top-1.5 h-[16px] w-[16px] rounded-full border-2 bg-canvas transition-colors z-10 flex items-center justify-center cursor-pointer ${
                    isCompleted 
                      ? 'border-primary bg-primary/20 text-primary scale-110' 
                      : 'border-zinc-700 hover:border-primary text-zinc-600'
                  }`}
                  onClick={() => handleToggleComplete(entry.file_path)}
                >
                  {isCompleted && <div className="h-1.5 w-1.5 rounded-full bg-primary" />}
                </div>

                {/* Timeline Step Header */}
                <div className="flex items-center justify-between text-[10px] font-mono text-text-muted pl-2">
                  <span>Step {idx + 1}</span>
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded border uppercase text-[8px] font-bold ${importance.color}`}>
                      {importance.label}
                    </span>
                    <span className="text-zinc-500">Score: {entry.score.toFixed(2)}</span>
                  </div>
                </div>

                {/* Timeline card panel */}
                <div 
                  className={`border rounded-lg bg-card/5 p-4 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition-all duration-200 cursor-pointer ${
                    isCompleted ? 'border-primary/20 bg-primary/5 opacity-80' : 'border-border hover:border-primary/40'
                  } ${selectedFile?.file_path === entry.file_path ? 'ring-1 ring-primary border-primary' : ''}`}
                  onClick={() => setSelectedFile(entry)}
                >
                  <div className="flex items-start gap-3 flex-grow min-w-0">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleComplete(entry.file_path);
                      }}
                      className="text-text-muted hover:text-text mt-0.5 shrink-0"
                    >
                      {isCompleted ? (
                        <CheckCircle2 className="h-4.5 w-4.5 text-primary" />
                      ) : (
                        <Circle className="h-4.5 w-4.5 text-zinc-600 hover:text-primary transition-colors" />
                      )}
                    </button>
                    
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-semibold text-text truncate break-all block">
                          {entry.file_path}
                        </span>
                        {entry.tier !== 'other' && (
                          <span className={`text-[8px] px-1.5 py-0.5 rounded border uppercase font-bold shrink-0 ${
                            entry.tier === 'entry_point' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                            entry.tier === 'core' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                            entry.tier === 'service' ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' :
                            entry.tier === 'utility' ? 'bg-teal-500/10 border-teal-500/20 text-teal-400' :
                            'bg-zinc-800 border-zinc-700 text-zinc-400'
                          }`}>
                            {entry.tier.replace('_', ' ')}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-text-muted font-sans line-clamp-2 leading-relaxed">
                        {entry.reason}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 self-end sm:self-center pl-8 sm:pl-0 font-mono text-[10px]">
                    <div className="flex items-center gap-1 text-text-muted bg-canvas border border-border px-2 py-1 rounded">
                      <Clock className="h-3 w-3" />
                      <span>{estMinutes} min</span>
                    </div>
                    <ChevronRight className="h-4 w-4 text-text-muted group-hover:text-text group-hover:translate-x-0.5 transition-all" />
                  </div>
                </div>

                {/* Connecting Arrow (omitted on the last element) */}
                {idx < totalFiles - 1 && (
                  <div className="flex justify-center w-full py-1.5">
                    <ArrowDown className="h-4 w-4 text-zinc-800 animate-pulse" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* File Intelligence Drawer Panel */}
      {selectedFile && (
        <div className="lg:col-span-4 bg-zinc-950 border border-border rounded-lg p-5 flex flex-col justify-between shadow-2xl h-fit sticky top-6 animate-in slide-in-from-right duration-200">
          <div className="space-y-5">
            <div className="flex justify-between items-start border-b border-border/40 pb-3">
              <div className="space-y-0.5">
                <span className="text-[10px] font-bold text-primary uppercase tracking-wider font-mono">
                  File Intelligence
                </span>
                <h3 className="text-xs font-mono font-semibold text-text truncate break-all block max-w-[200px]">
                  {selectedFile.file_path.split('/').pop()}
                </h3>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-text-muted hover:text-text rounded p-0.5"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 font-mono text-xs">
              <div>
                <span className="text-text-muted block text-[10px] uppercase">Path</span>
                <span className="text-text font-semibold break-all text-xs block mt-1">{selectedFile.file_path}</span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Importance Score</span>
                <span className="text-text text-sm font-bold block mt-1">{selectedFile.score.toFixed(2)}</span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Estimated Read Time</span>
                <span className="text-text text-xs font-semibold block mt-1">{getFileReadingTime(selectedFile.score)} minutes</span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Category Tier</span>
                <span className={`inline-block text-[9px] font-bold uppercase px-2 py-0.5 rounded border mt-1.5 ${
                  selectedFile.tier === 'entry_point' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                  selectedFile.tier === 'core' ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' :
                  selectedFile.tier === 'service' ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' :
                  selectedFile.tier === 'utility' ? 'bg-teal-500/10 border-teal-500/20 text-teal-400' :
                  'bg-zinc-800 border-zinc-700 text-zinc-300'
                }`}>
                  {selectedFile.tier.replace('_', ' ')}
                </span>
              </div>

              <div>
                <span className="text-text-muted block text-[10px] uppercase">Architectural Context</span>
                <p className="text-text-muted leading-relaxed font-sans mt-1 bg-canvas/30 border border-border p-2.5 rounded">
                  {selectedFile.reason}
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons for Future Compatibility */}
          <div className="border-t border-border/40 pt-4 mt-6 space-y-2">
            <button
              disabled
              className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-2 rounded text-xs font-mono opacity-60 cursor-not-allowed"
            >
              <span className="flex items-center gap-1.5">
                <ExternalLink className="h-3.5 w-3.5" />
                <span>Open File</span>
              </span>
              <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
            </button>
            <button
              disabled
              className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-2 rounded text-xs font-mono opacity-60 cursor-not-allowed"
            >
              <span className="flex items-center gap-1.5">
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Ask About File</span>
              </span>
              <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
            </button>
            <button
              disabled
              className="w-full flex items-center justify-between bg-zinc-900 border border-border text-zinc-500 px-3 py-2 rounded text-xs font-mono opacity-60 cursor-not-allowed"
            >
              <span className="flex items-center gap-1.5">
                <GitMerge className="h-3.5 w-3.5" />
                <span>View Dependencies</span>
              </span>
              <span className="text-[8px] bg-zinc-800 px-1 py-0.5 rounded">Future</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
