import React, { useState, useEffect } from 'react';
import FileTree from './FileTree';
import { Layers, Box, Code2, BookOpen, Cpu, Info, CheckCircle2 } from 'lucide-react';

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
  repoParam: string;
}

export const AnalysisDashboard: React.FC<DashboardProps> = ({ repoParam }) => {
  const [data, setData] = useState<AnalysisData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  // Decode route parameter (e.g., owner-repo to owner/repo)
  const repoName = repoParam ? repoParam.replace('-', '/') : 'unknown/repo';

  useEffect(() => {
    const [owner, name] = repoName.split('/');
    fetch(`/api/analysis/${owner}/${name}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch repository details");
        return res.json();
      })
      .then((resData) => {
        setData(resData);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [repoName]);

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
        <span>Failed to load repository metadata. Make sure python API server is running on port 8000.</span>
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
      </div>
    </div>
  );
};

export default AnalysisDashboard;
