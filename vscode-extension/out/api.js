"use strict";
/**
 * API client for the Repo Intelligence Agent backend.
 *
 * All backend communication goes through this module. It reads the base URL
 * and optional token from VS Code settings so there is one place to change
 * the target. No analysis logic lives here — this is a pure HTTP client.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.client = exports.RepoIntelligenceClient = void 0;
exports.extractErrorMessage = extractErrorMessage;
const vscode = __importStar(require("vscode"));
const https = __importStar(require("https"));
const http = __importStar(require("http"));
// ---------------------------------------------------------------------------
// Client class
// ---------------------------------------------------------------------------
class RepoIntelligenceClient {
    get baseUrl() {
        const cfg = vscode.workspace.getConfiguration('repoIntelligence');
        return (cfg.get('backendUrl') ?? 'http://127.0.0.1:8001').replace(/\/$/, '');
    }
    get timeoutMs() {
        const cfg = vscode.workspace.getConfiguration('repoIntelligence');
        return cfg.get('requestTimeoutMs') ?? 15000;
    }
    get authHeaders() {
        const cfg = vscode.workspace.getConfiguration('repoIntelligence');
        const token = cfg.get('apiToken') ?? '';
        return token ? { Authorization: `Bearer ${token}` } : {};
    }
    // ── Core fetch ──────────────────────────────────────────────────────────
    async fetchJson(path, options = {}) {
        const url = `${this.baseUrl}${path}`;
        const method = options.method ?? 'GET';
        const headers = {
            'Content-Type': 'application/json',
            Accept: 'application/json',
            ...this.authHeaders,
        };
        return new Promise((resolve, reject) => {
            const parsedUrl = new URL(url);
            const isHttps = parsedUrl.protocol === 'https:';
            const transport = isHttps ? https : http;
            const reqOptions = {
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
                            }
                            catch {
                                // use status text
                            }
                            reject(new Error(detail));
                            return;
                        }
                        resolve(JSON.parse(data));
                    }
                    catch (e) {
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
    streamSse(path, body, onEvent, onDone, onError) {
        const url = `${this.baseUrl}${path}`;
        const parsedUrl = new URL(url);
        const isHttps = parsedUrl.protocol === 'https:';
        const transport = isHttps ? https : http;
        const payload = JSON.stringify(body);
        const reqOptions = {
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
            res.on('data', (chunk) => {
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
                            const event = JSON.parse(jsonStr);
                            onEvent(event);
                            if (event.status === 'done') {
                                onDone();
                            }
                        }
                        catch {
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
    async health() {
        return this.fetchJson('/health');
    }
    // ── Repositories ────────────────────────────────────────────────────────
    async getRecentRepos() {
        return this.fetchJson('/api/repos/recent');
    }
    async getAnalysis(owner, repo) {
        return this.fetchJson(`/api/analysis/${owner}/${repo}`);
    }
    // ── Symbols ─────────────────────────────────────────────────────────────
    async getFileSymbols(owner, repo, filePath) {
        return this.fetchJson(`/api/symbols/${owner}/${repo}/file/${filePath}`);
    }
    async getSymbolDefinition(owner, repo, symbolName) {
        return this.fetchJson(`/api/symbols/${owner}/${repo}/definition/${encodeURIComponent(symbolName)}`);
    }
    async getSymbolReferences(owner, repo, symbolName) {
        return this.fetchJson(`/api/symbols/${owner}/${repo}/references/${encodeURIComponent(symbolName)}`);
    }
    // ── Architecture ────────────────────────────────────────────────────────
    async buildArchitecture(repo) {
        return this.fetchJson('/api/architecture/build', {
            method: 'POST',
            body: { repo },
        });
    }
    async getArchitectureSummary(owner, repo) {
        return this.fetchJson(`/api/architecture/${owner}/${repo}`);
    }
    async getReadingOrder(repo) {
        return this.fetchJson('/api/reading-order', {
            method: 'POST',
            body: { repo },
        });
    }
    async getImpactAnalysis(repo, issue) {
        return this.fetchJson('/api/impact-analysis', {
            method: 'POST',
            body: { repo, issue },
        });
    }
    // ── Graph ────────────────────────────────────────────────────────────────
    async getDependencyGraph(owner, repo, query) {
        const q = query ? `?q=${encodeURIComponent(query)}` : '';
        return this.fetchJson(`/api/graph/${owner}/${repo}/full${q}`);
    }
    async getGraphNeighbors(owner, repo, nodePath) {
        return this.fetchJson(`/api/graph/${owner}/${repo}/neighbors/${nodePath}`);
    }
    async getGraphTrace(owner, repo, nodePath, direction = 'both', depth = 6) {
        return this.fetchJson(`/api/graph/${owner}/${repo}/trace/${nodePath}?direction=${direction}&depth=${depth}`);
    }
    // ── Call Graph ──────────────────────────────────────────────────────────
    async getCallGraph(owner, repo, query) {
        const q = query ? `?q=${encodeURIComponent(query)}` : '';
        return this.fetchJson(`/api/call-graph/${owner}/${repo}${q}`);
    }
    async getCallers(owner, repo, functionId) {
        return this.fetchJson(`/api/call-graph/${owner}/${repo}/callers/${functionId}`);
    }
    async getCallees(owner, repo, functionId) {
        return this.fetchJson(`/api/call-graph/${owner}/${repo}/callees/${functionId}`);
    }
    async getBlastRadius(owner, repo, functionId) {
        return this.fetchJson(`/api/call-graph/${owner}/${repo}/blast-radius/${functionId}`);
    }
    // ── API Surface ──────────────────────────────────────────────────────────
    async getAPISurface(owner, repo) {
        return this.fetchJson(`/api/api-surface/${owner}/${repo}`);
    }
    async getAPISurfaceStats(owner, repo) {
        return this.fetchJson(`/api/api-surface/${owner}/${repo}/stats`);
    }
    async getPublicAPI(owner, repo, query) {
        const q = query ? `?q=${encodeURIComponent(query)}` : '';
        return this.fetchJson(`/api/api-surface/${owner}/${repo}/public${q}`);
    }
    // ── Git Churn ───────────────────────────────────────────────────────────
    async getChurnHotspots(owner, repo, topN = 25, sinceDays = 365) {
        return this.fetchJson(`/api/churn/${owner}/${repo}/hotspots?top_n=${topN}&since_days=${sinceDays}`);
    }
    // ── Chat ────────────────────────────────────────────────────────────────
    streamChat(repo, message, history, onToken, onDone, onError) {
        return this.streamSse('/api/chat', { repo, message, history }, (event) => {
            if (typeof event.text === 'string') {
                onToken(event.text);
            }
            if (event.status === 'done') {
                onDone(event.sources ?? [], event.confidence ?? 0);
            }
        }, () => { }, onError);
    }
}
exports.RepoIntelligenceClient = RepoIntelligenceClient;
/**
 * Shared singleton client — imported by providers, commands, and panels.
 */
exports.client = new RepoIntelligenceClient();
/**
 * Extract a user-friendly message from any error value.
 */
function extractErrorMessage(err) {
    if (err instanceof Error) {
        return err.message;
    }
    if (typeof err === 'string') {
        return err;
    }
    return 'An unknown error occurred.';
}
//# sourceMappingURL=api.js.map