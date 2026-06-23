/**
 * API client for the Repo Intelligence Agent backend.
 *
 * All backend communication goes through this module. It reads the base URL
 * and optional token from VS Code settings so there is one place to change
 * the target. No analysis logic lives here — this is a pure HTTP client.
 */

import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';

// ---------------------------------------------------------------------------
// Types that mirror backend Pydantic models
// ---------------------------------------------------------------------------

export interface HealthResponse {
  backend: string;
  llm_provider: string;
  llm_model: string;
  embedding_provider: string;
  vector_db: string;
  status: string;
}

export interface RecentRepo {
  name: string;
  url: string;
  tech_stack: string[];
  analyzed_at: string;
}

export interface RepositoryAnalysis {
  structure: Record<string, string[]>;
  dependencies: string[];
  tech_stack: string[];
  metadata: Record<string, string>;
}

export interface ArchitectureSummary {
  summary: string;
  reading_order: string[];
  relationships: ComponentRelationship[];
}

export interface ComponentRelationship {
  source: string;
  target: string;
  relationship_type: string;
  description: string;
}

export interface AnalysisDetails {
  analysis: RepositoryAnalysis;
  architecture: ArchitectureSummary;
}

export interface Symbol {
  name: string;
  qualified: string;
  symbol_type: string;
  file_path: string;
  line_number: number;
  language: string;
  parent_class: string | null;
  fan_in?: number;
  fan_out?: number;
}

export interface FileSymbolsResponse {
  file: string;
  repo: string;
  symbol_count: number;
  symbols: Symbol[];
}

export interface SymbolDefinitionResponse {
  symbol: string;
  repo: string;
  definition: Symbol;
}

export interface SymbolReferencesResponse {
  symbol: string;
  repo: string;
  references: Symbol[];
  reference_count: number;
}

export interface GraphNode {
  id: string;
  data: {
    label: string;
    [key: string]: unknown;
  };
  position: { x: number; y: number };
  type?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CallNode {
  node_id: string;
  name: string;
  qualified: string;
  file_path: string;
  line_number: number;
  language: string;
  symbol_type: string;
  parent_class: string | null;
  is_entry: boolean;
  is_recursive: boolean;
  fan_in: number;
  fan_out: number;
}

export interface CallersResponse {
  function_id: string;
  callers: CallNode[];
}

export interface CalleesResponse {
  function_id: string;
  callees: CallNode[];
}

export interface BlastRadiusResult {
  function_id: string;
  affected_functions: string[];
  affected_files: string[];
  depth: number;
  risk_level: string;
  recursive_cycles: string[][];
}

export interface ClassifiedSymbol {
  name: string;
  qualified: string;
  symbol_type: string;
  file_path: string;
  line_number: number;
  language: string;
  visibility: string;
  api_kind: string;
  status: string;
  confidence: number;
  classification_reason: string;
  fan_in: number;
  is_orphan: boolean;
}

export interface APISurfaceStats {
  total_symbols: number;
  public_count: number;
  internal_count: number;
  private_count: number;
  deprecated_count: number;
  experimental_count: number;
  route_count: number;
  orphan_public_count: number;
  by_language: Record<string, number>;
}

export interface APISurface {
  repo: string;
  generated_at: string;
  symbols: ClassifiedSymbol[];
  stats: APISurfaceStats;
  warning?: string;
}

export interface ChurnHotspot {
  file_path: string;
  commit_count: number;
  churn_score: number;
  [key: string]: unknown;
}

export interface HotspotsResponse {
  hotspots: ChurnHotspot[];
}

export interface ReadingOrderEntry {
  file: string;
  score: number;
  reason: string;
  [key: string]: unknown;
}

export interface ReadingOrder {
  repo: string;
  entries: ReadingOrderEntry[];
  [key: string]: unknown;
}

export interface ImpactAnalysis {
  repo: string;
  issue: string;
  affected_files: string[];
  risk_level: string;
  risk_score: number;
  [key: string]: unknown;
}

export interface IssueMapResponse {
  issue_summary: string;
  issue_type: string;
  relevant_files: string[];
  affected_components: string[];
  implementation_plan: Array<Record<string, unknown>>;
  complexity: string;
  confidence: number;
  verified: boolean;
  sources: string[];
}

export interface ArchitectureBuildResponse {
  status: string;
  repo: string;
  files_parsed: number;
  dependencies_found: number;
  entry_points: string[];
}

// ---------------------------------------------------------------------------
// SSE helpers
// ---------------------------------------------------------------------------

export type SseEventHandler = (event: Record<string, unknown>) => void;

// ---------------------------------------------------------------------------
// Client class
// ---------------------------------------------------------------------------

export class RepoIntelligenceClient {
  private get baseUrl(): string {
    const cfg = vscode.workspace.getConfiguration('repoIntelligence');
    return (cfg.get<string>('backendUrl') ?? 'http://127.0.0.1:8001').replace(/\/$/, '');
  }

  private get timeoutMs(): number {
    const cfg = vscode.workspace.getConfiguration('repoIntelligence');
    return cfg.get<number>('requestTimeoutMs') ?? 15000;
  }

  private get authHeaders(): Record<string, string> {
    const cfg = vscode.workspace.getConfiguration('repoIntelligence');
    const token = cfg.get<string>('apiToken') ?? '';
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // ── Core fetch ──────────────────────────────────────────────────────────

  async fetchJson<T>(
    path: string,
    options: { method?: string; body?: unknown } = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const method = options.method ?? 'GET';
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...this.authHeaders,
    };

    return new Promise<T>((resolve, reject) => {
      const parsedUrl = new URL(url);
      const isHttps = parsedUrl.protocol === 'https:';
      const transport = isHttps ? https : http;

      const reqOptions: http.RequestOptions = {
        hostname: parsedUrl.hostname,
        port: parsedUrl.port || (isHttps ? 443 : 80),
        path: parsedUrl.pathname + parsedUrl.search,
        method,
        headers,
        timeout: this.timeoutMs,
      };

      const req = transport.request(reqOptions, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            if (res.statusCode && res.statusCode >= 400) {
              let detail = `HTTP ${res.statusCode}`;
              try {
                const parsed = JSON.parse(data);
                detail = parsed.detail ?? detail;
              } catch {
                // use status text
              }
              reject(new Error(detail));
              return;
            }
            resolve(JSON.parse(data) as T);
          } catch (e) {
            reject(new Error(`Failed to parse response: ${String(e)}`));
          }
        });
      });

      req.on('timeout', () => {
        req.destroy();
        reject(new Error(`Request to ${url} timed out after ${this.timeoutMs}ms`));
      });

      req.on('error', (e) => reject(new Error(`Request failed: ${e.message}`)));

      if (options.body !== undefined) {
        req.write(JSON.stringify(options.body));
      }
      req.end();
    });
  }

  // ── SSE streaming (uses Node http/https directly) ───────────────────────

  streamSse(
    path: string,
    body: Record<string, unknown>,
    onEvent: SseEventHandler,
    onDone: () => void,
    onError: (err: Error) => void
  ): () => void {
    const url = `${this.baseUrl}${path}`;
    const parsedUrl = new URL(url);
    const isHttps = parsedUrl.protocol === 'https:';
    const transport = isHttps ? https : http;

    const payload = JSON.stringify(body);
    const reqOptions: http.RequestOptions = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (isHttps ? 443 : 80),
      path: parsedUrl.pathname + parsedUrl.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        'Cache-Control': 'no-cache',
        ...this.authHeaders,
      },
    };

    const req = transport.request(reqOptions, (res) => {
      let buffer = '';
      res.on('data', (chunk: Buffer) => {
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) {
              continue;
            }
            try {
              const event = JSON.parse(jsonStr) as Record<string, unknown>;
              onEvent(event);
              if (event.status === 'done') {
                onDone();
              }
            } catch {
              // skip malformed SSE lines
            }
          }
        }
      });
      res.on('end', () => onDone());
      res.on('error', onError);
    });

    req.on('error', onError);
    req.write(payload);
    req.end();

    return () => req.destroy();
  }

  // ── Health ──────────────────────────────────────────────────────────────

  async health(): Promise<HealthResponse> {
    return this.fetchJson<HealthResponse>('/health');
  }

  // ── Repositories ────────────────────────────────────────────────────────

  async getRecentRepos(): Promise<RecentRepo[]> {
    return this.fetchJson<RecentRepo[]>('/api/repos/recent');
  }

  async getAnalysis(owner: string, repo: string): Promise<AnalysisDetails> {
    return this.fetchJson<AnalysisDetails>(`/api/analysis/${owner}/${repo}`);
  }

  // ── Symbols ─────────────────────────────────────────────────────────────

  async getFileSymbols(owner: string, repo: string, filePath: string): Promise<FileSymbolsResponse> {
    return this.fetchJson<FileSymbolsResponse>(
      `/api/symbols/${owner}/${repo}/file/${filePath}`
    );
  }

  async getSymbolDefinition(owner: string, repo: string, symbolName: string): Promise<SymbolDefinitionResponse> {
    return this.fetchJson<SymbolDefinitionResponse>(
      `/api/symbols/${owner}/${repo}/definition/${encodeURIComponent(symbolName)}`
    );
  }

  async getSymbolReferences(owner: string, repo: string, symbolName: string): Promise<SymbolReferencesResponse> {
    return this.fetchJson<SymbolReferencesResponse>(
      `/api/symbols/${owner}/${repo}/references/${encodeURIComponent(symbolName)}`
    );
  }

  // ── Architecture ────────────────────────────────────────────────────────

  async buildArchitecture(repo: string): Promise<ArchitectureBuildResponse> {
    return this.fetchJson<ArchitectureBuildResponse>('/api/architecture/build', {
      method: 'POST',
      body: { repo },
    });
  }

  async getArchitectureSummary(owner: string, repo: string): Promise<ArchitectureSummary> {
    return this.fetchJson<ArchitectureSummary>(`/api/architecture/${owner}/${repo}`);
  }

  async getReadingOrder(repo: string): Promise<ReadingOrder> {
    return this.fetchJson<ReadingOrder>('/api/reading-order', {
      method: 'POST',
      body: { repo },
    });
  }

  async getImpactAnalysis(repo: string, issue: string): Promise<ImpactAnalysis> {
    return this.fetchJson<ImpactAnalysis>('/api/impact-analysis', {
      method: 'POST',
      body: { repo, issue },
    });
  }

  // ── Graph ────────────────────────────────────────────────────────────────

  async getDependencyGraph(owner: string, repo: string, query?: string): Promise<GraphData> {
    const q = query ? `?q=${encodeURIComponent(query)}` : '';
    return this.fetchJson<GraphData>(`/api/graph/${owner}/${repo}/full${q}`);
  }

  async getGraphNeighbors(owner: string, repo: string, nodePath: string): Promise<GraphData> {
    return this.fetchJson<GraphData>(
      `/api/graph/${owner}/${repo}/neighbors/${nodePath}`
    );
  }

  async getGraphTrace(
    owner: string,
    repo: string,
    nodePath: string,
    direction = 'both',
    depth = 6
  ): Promise<GraphData> {
    return this.fetchJson<GraphData>(
      `/api/graph/${owner}/${repo}/trace/${nodePath}?direction=${direction}&depth=${depth}`
    );
  }

  // ── Call Graph ──────────────────────────────────────────────────────────

  async getCallGraph(owner: string, repo: string, query?: string): Promise<GraphData> {
    const q = query ? `?q=${encodeURIComponent(query)}` : '';
    return this.fetchJson<GraphData>(`/api/call-graph/${owner}/${repo}${q}`);
  }

  async getCallers(owner: string, repo: string, functionId: string): Promise<CallersResponse> {
    return this.fetchJson<CallersResponse>(
      `/api/call-graph/${owner}/${repo}/callers/${functionId}`
    );
  }

  async getCallees(owner: string, repo: string, functionId: string): Promise<CalleesResponse> {
    return this.fetchJson<CalleesResponse>(
      `/api/call-graph/${owner}/${repo}/callees/${functionId}`
    );
  }

  async getBlastRadius(owner: string, repo: string, functionId: string): Promise<BlastRadiusResult> {
    return this.fetchJson<BlastRadiusResult>(
      `/api/call-graph/${owner}/${repo}/blast-radius/${functionId}`
    );
  }

  // ── API Surface ──────────────────────────────────────────────────────────

  async getAPISurface(owner: string, repo: string): Promise<APISurface> {
    return this.fetchJson<APISurface>(`/api/api-surface/${owner}/${repo}`);
  }

  async getAPISurfaceStats(owner: string, repo: string): Promise<APISurfaceStats> {
    return this.fetchJson<APISurfaceStats>(`/api/api-surface/${owner}/${repo}/stats`);
  }

  async getPublicAPI(owner: string, repo: string, query?: string): Promise<{ symbols: ClassifiedSymbol[]; count: number }> {
    const q = query ? `?q=${encodeURIComponent(query)}` : '';
    return this.fetchJson(`/api/api-surface/${owner}/${repo}/public${q}`);
  }

  // ── Git Churn ───────────────────────────────────────────────────────────

  async getChurnHotspots(
    owner: string,
    repo: string,
    topN = 25,
    sinceDays = 365
  ): Promise<HotspotsResponse> {
    return this.fetchJson<HotspotsResponse>(
      `/api/churn/${owner}/${repo}/hotspots?top_n=${topN}&since_days=${sinceDays}`
    );
  }

  // ── Chat ────────────────────────────────────────────────────────────────

  streamChat(
    repo: string,
    message: string,
    history: Array<{ role: string; content: string }>,
    onToken: (text: string) => void,
    onDone: (sources: string[], confidence: number) => void,
    onError: (err: Error) => void
  ): () => void {
    return this.streamSse(
      '/api/chat',
      { repo, message, history },
      (event) => {
        if (typeof event.text === 'string') {
          onToken(event.text);
        }
        if (event.status === 'done') {
          onDone(
            (event.sources as string[]) ?? [],
            (event.confidence as number) ?? 0
          );
        }
      },
      () => { /* handled inside onEvent for status==done */ },
      onError
    );
  }
}

/**
 * Shared singleton client — imported by providers, commands, and panels.
 */
export const client = new RepoIntelligenceClient();

/**
 * Extract a user-friendly message from any error value.
 */
export function extractErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    return err.message;
  }
  if (typeof err === 'string') {
    return err;
  }
  return 'An unknown error occurred.';
}
