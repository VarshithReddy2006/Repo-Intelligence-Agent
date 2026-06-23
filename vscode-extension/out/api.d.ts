/**
 * API client for the Repo Intelligence Agent backend.
 *
 * All backend communication goes through this module. It reads the base URL
 * and optional token from VS Code settings so there is one place to change
 * the target. No analysis logic lives here — this is a pure HTTP client.
 */
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
    position: {
        x: number;
        y: number;
    };
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
export type SseEventHandler = (event: Record<string, unknown>) => void;
export declare class RepoIntelligenceClient {
    private get baseUrl();
    private get timeoutMs();
    private get authHeaders();
    fetchJson<T>(path: string, options?: {
        method?: string;
        body?: unknown;
    }): Promise<T>;
    streamSse(path: string, body: Record<string, unknown>, onEvent: SseEventHandler, onDone: () => void, onError: (err: Error) => void): () => void;
    health(): Promise<HealthResponse>;
    getRecentRepos(): Promise<RecentRepo[]>;
    getAnalysis(owner: string, repo: string): Promise<AnalysisDetails>;
    getFileSymbols(owner: string, repo: string, filePath: string): Promise<FileSymbolsResponse>;
    getSymbolDefinition(owner: string, repo: string, symbolName: string): Promise<SymbolDefinitionResponse>;
    getSymbolReferences(owner: string, repo: string, symbolName: string): Promise<SymbolReferencesResponse>;
    buildArchitecture(repo: string): Promise<ArchitectureBuildResponse>;
    getArchitectureSummary(owner: string, repo: string): Promise<ArchitectureSummary>;
    getReadingOrder(repo: string): Promise<ReadingOrder>;
    getImpactAnalysis(repo: string, issue: string): Promise<ImpactAnalysis>;
    getDependencyGraph(owner: string, repo: string, query?: string): Promise<GraphData>;
    getGraphNeighbors(owner: string, repo: string, nodePath: string): Promise<GraphData>;
    getGraphTrace(owner: string, repo: string, nodePath: string, direction?: string, depth?: number): Promise<GraphData>;
    getCallGraph(owner: string, repo: string, query?: string): Promise<GraphData>;
    getCallers(owner: string, repo: string, functionId: string): Promise<CallersResponse>;
    getCallees(owner: string, repo: string, functionId: string): Promise<CalleesResponse>;
    getBlastRadius(owner: string, repo: string, functionId: string): Promise<BlastRadiusResult>;
    getAPISurface(owner: string, repo: string): Promise<APISurface>;
    getAPISurfaceStats(owner: string, repo: string): Promise<APISurfaceStats>;
    getPublicAPI(owner: string, repo: string, query?: string): Promise<{
        symbols: ClassifiedSymbol[];
        count: number;
    }>;
    getChurnHotspots(owner: string, repo: string, topN?: number, sinceDays?: number): Promise<HotspotsResponse>;
    streamChat(repo: string, message: string, history: Array<{
        role: string;
        content: string;
    }>, onToken: (text: string) => void, onDone: (sources: string[], confidence: number) => void, onError: (err: Error) => void): () => void;
}
/**
 * Shared singleton client — imported by providers, commands, and panels.
 */
export declare const client: RepoIntelligenceClient;
/**
 * Extract a user-friendly message from any error value.
 */
export declare function extractErrorMessage(err: unknown): string;
//# sourceMappingURL=api.d.ts.map