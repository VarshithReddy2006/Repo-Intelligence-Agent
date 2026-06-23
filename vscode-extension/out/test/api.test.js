"use strict";
/**
 * Unit tests for the API client.
 *
 * Uses a mock HTTP server to avoid requiring a running backend.
 * Tests cover: health, getRecentRepos, getAnalysis, getFileSymbols,
 * getDependencyGraph, getCallGraph, getAPISurface, and error handling.
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
const assert = __importStar(require("assert"));
const http = __importStar(require("http"));
// We need to test the client without a real VS Code instance.
// The vscode module is aliased to ./mocks/vscode in package.json
// Set config overrides per test via global.__vscodeConfig__
const mockConfig = {
    backendUrl: '', // set per test
    apiToken: '',
    requestTimeoutMs: 5000,
};
// Override vscode config for this test suite
global.__vscodeConfig__ = mockConfig;
const api_1 = require("../api");
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function startMockServer(handler) {
    return new Promise((resolve, reject) => {
        const server = http.createServer(handler);
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            resolve({ server, url: `http://127.0.0.1:${port}` });
        });
        server.on('error', reject);
    });
}
function stopServer(server) {
    return new Promise((resolve, reject) => {
        server.close((err) => (err ? reject(err) : resolve()));
    });
}
function jsonResponse(res, body, status = 200) {
    res.writeHead(status, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(body));
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('RepoIntelligenceClient', () => {
    let server;
    let client;
    afterEach(async () => {
        if (server) {
            await stopServer(server);
        }
    });
    // ── health ──────────────────────────────────────────────────────────────
    it('health() returns parsed response', async () => {
        const body = {
            backend: 'online',
            llm_provider: 'deepseek',
            llm_model: 'deepseek-ai/deepseek-v4-flash',
            embedding_provider: 'BAAI/bge-small-en-v1.5',
            vector_db: 'chromadb',
            status: 'healthy',
        };
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        const result = await client.health();
        assert.strictEqual(result.status, 'healthy');
        assert.strictEqual(result.llm_provider, 'deepseek');
    });
    // ── getRecentRepos ──────────────────────────────────────────────────────
    it('getRecentRepos() returns array of repos', async () => {
        const body = [
            { name: 'owner/repo', url: 'https://github.com/owner/repo', tech_stack: ['Python'], analyzed_at: 'Just now' },
        ];
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        const repos = await client.getRecentRepos();
        assert.strictEqual(repos.length, 1);
        assert.strictEqual(repos[0].name, 'owner/repo');
    });
    // ── getFileSymbols ──────────────────────────────────────────────────────
    it('getFileSymbols() returns symbols for a file', async () => {
        const body = {
            file: 'backend/api.py',
            repo: 'owner/repo',
            symbol_count: 2,
            symbols: [
                { name: 'health', qualified: 'health', symbol_type: 'function', file_path: 'backend/api.py', line_number: 10, language: 'python', parent_class: null },
                { name: 'MyClass', qualified: 'MyClass', symbol_type: 'class', file_path: 'backend/api.py', line_number: 20, language: 'python', parent_class: null },
            ],
        };
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        const result = await client.getFileSymbols('owner', 'repo', 'backend/api.py');
        assert.strictEqual(result.symbol_count, 2);
        assert.strictEqual(result.symbols[0].name, 'health');
    });
    // ── getDependencyGraph ──────────────────────────────────────────────────
    it('getDependencyGraph() returns nodes and edges', async () => {
        const body = {
            nodes: [
                { id: 'a.py', data: { label: 'a.py' }, position: { x: 0, y: 0 } },
                { id: 'b.py', data: { label: 'b.py' }, position: { x: 100, y: 0 } },
            ],
            edges: [{ id: 'e1', source: 'a.py', target: 'b.py' }],
        };
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        const graph = await client.getDependencyGraph('owner', 'repo');
        assert.strictEqual(graph.nodes.length, 2);
        assert.strictEqual(graph.edges.length, 1);
    });
    // ── getAPISurfaceStats ──────────────────────────────────────────────────
    it('getAPISurfaceStats() returns stats object', async () => {
        const body = {
            total_symbols: 100,
            public_count: 40,
            internal_count: 30,
            private_count: 20,
            deprecated_count: 5,
            experimental_count: 2,
            route_count: 8,
            orphan_public_count: 3,
            by_language: { python: 90, typescript: 10 },
        };
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        const stats = await client.getAPISurfaceStats('owner', 'repo');
        assert.strictEqual(stats.total_symbols, 100);
        assert.strictEqual(stats.public_count, 40);
    });
    // ── Error handling ──────────────────────────────────────────────────────
    it('rejects with error message on HTTP 404', async () => {
        const body = { detail: 'Repository not found' };
        ({ server } = await startMockServer((_req, res) => jsonResponse(res, body, 404)));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        client = new api_1.RepoIntelligenceClient();
        await assert.rejects(() => client.getAnalysis('owner', 'nonexistent'), (err) => {
            assert.ok(err.message.includes('Repository not found') || err.message.includes('404'));
            return true;
        });
    });
    it('rejects with timeout error when server hangs', async () => {
        ({ server } = await startMockServer((_req, _res) => {
            // Never respond
        }));
        mockConfig.backendUrl = `http://127.0.0.1:${server.address().port}`;
        mockConfig.requestTimeoutMs = 200;
        client = new api_1.RepoIntelligenceClient();
        await assert.rejects(() => client.health(), (err) => {
            assert.ok(err.message.toLowerCase().includes('timed out'));
            return true;
        });
        mockConfig.requestTimeoutMs = 5000;
    });
});
// ---------------------------------------------------------------------------
// extractErrorMessage tests
// ---------------------------------------------------------------------------
describe('extractErrorMessage', () => {
    it('handles Error instances', () => {
        assert.strictEqual((0, api_1.extractErrorMessage)(new Error('boom')), 'boom');
    });
    it('handles string input', () => {
        assert.strictEqual((0, api_1.extractErrorMessage)('oops'), 'oops');
    });
    it('handles unknown input gracefully', () => {
        const msg = (0, api_1.extractErrorMessage)(null);
        assert.ok(typeof msg === 'string' && msg.length > 0);
    });
    it('handles undefined input gracefully', () => {
        const msg = (0, api_1.extractErrorMessage)(undefined);
        assert.ok(typeof msg === 'string' && msg.length > 0);
    });
});
//# sourceMappingURL=api.test.js.map