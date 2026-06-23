"use strict";
/**
 * Unit tests for the chat SSE streaming logic.
 *
 * Tests SSE event parsing, history normalization, and error handling patterns
 * without requiring a real VS Code webview or running backend.
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
// ---------------------------------------------------------------------------
// VS Code stub
// ---------------------------------------------------------------------------
const mockConfig = {
    backendUrl: '',
    apiToken: '',
    requestTimeoutMs: 5000,
};
global.vscode = {
    workspace: {
        getConfiguration: () => ({
            get: (key) => mockConfig[key],
        }),
    },
};
const api_1 = require("../api");
// ---------------------------------------------------------------------------
// SSE server helper
// ---------------------------------------------------------------------------
function startSseServer(events) {
    return new Promise((resolve, reject) => {
        const server = http.createServer((_req, res) => {
            res.writeHead(200, {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                Connection: 'keep-alive',
            });
            for (const event of events) {
                res.write(`data: ${event}\n\n`);
            }
            res.end();
        });
        server.listen(0, '127.0.0.1', () => {
            const port = server.address().port;
            resolve({ server, url: `http://127.0.0.1:${port}` });
        });
        server.on('error', reject);
    });
}
function stopServer(server) {
    return new Promise((resolve, reject) => server.close((err) => (err ? reject(err) : resolve())));
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('Chat SSE streaming', () => {
    let server;
    let client;
    afterEach(async () => {
        if (server)
            await stopServer(server);
    });
    it('receives text tokens from SSE stream', (done) => {
        const events = [
            JSON.stringify({ text: 'Hello ' }),
            JSON.stringify({ text: 'world' }),
            JSON.stringify({ sources: ['a.py'], confidence: 90, status: 'done' }),
        ];
        void startSseServer(events).then(({ server: s, url }) => {
            server = s;
            mockConfig.backendUrl = url;
            client = new api_1.RepoIntelligenceClient();
            const tokens = [];
            let doneCalled = false;
            client.streamChat('owner/repo', 'Hello?', [], (token) => tokens.push(token), (sources, confidence) => {
                doneCalled = true;
                assert.deepStrictEqual(tokens, ['Hello ', 'world']);
                assert.deepStrictEqual(sources, ['a.py']);
                assert.strictEqual(confidence, 90);
                done();
            }, (err) => done(err));
        });
    });
    it('calls onError when connection is refused', (done) => {
        // No server started — connection will be refused
        mockConfig.backendUrl = 'http://127.0.0.1:1'; // Port 1 is always refused
        client = new api_1.RepoIntelligenceClient();
        client.streamChat('owner/repo', 'test', [], () => { }, () => done(new Error('onDone should not be called on error')), (err) => {
            assert.ok(err instanceof Error);
            done();
        });
    });
    it('handles empty SSE stream (no events)', (done) => {
        void startSseServer([]).then(({ server: s, url }) => {
            server = s;
            mockConfig.backendUrl = url;
            client = new api_1.RepoIntelligenceClient();
            const tokens = [];
            // Stream ends immediately — onDone should be called
            const cancel = client.streamChat('owner/repo', 'empty', [], (t) => tokens.push(t), (_sources, _confidence) => {
                assert.strictEqual(tokens.length, 0);
                done();
            }, (err) => done(err));
            void cancel; // suppress unused warning
        });
    });
});
// ---------------------------------------------------------------------------
// History normalization tests
// ---------------------------------------------------------------------------
describe('Chat history normalization', () => {
    function normalizeHistory(history) {
        return history
            .map((turn) => {
            let role = turn.role;
            if (role === 'model') {
                role = 'assistant';
            }
            const parts = turn.parts;
            let content;
            if (parts && parts.length > 0) {
                content = typeof parts[0] === 'string' ? parts[0] : String(parts[0]);
            }
            else if (turn.content) {
                content = turn.content;
            }
            else {
                return null;
            }
            return { role, content };
        })
            .filter((t) => t !== null);
    }
    it('converts model role to assistant', () => {
        const normalized = normalizeHistory([
            { role: 'model', parts: ['I am the assistant.'] },
        ]);
        assert.strictEqual(normalized[0].role, 'assistant');
    });
    it('preserves user role', () => {
        const normalized = normalizeHistory([
            { role: 'user', content: 'Hello' },
        ]);
        assert.strictEqual(normalized[0].role, 'user');
    });
    it('extracts content from parts array', () => {
        const normalized = normalizeHistory([
            { role: 'user', parts: ['What does this function do?'] },
        ]);
        assert.strictEqual(normalized[0].content, 'What does this function do?');
    });
    it('extracts content from content field', () => {
        const normalized = normalizeHistory([
            { role: 'assistant', content: 'This function handles auth.' },
        ]);
        assert.strictEqual(normalized[0].content, 'This function handles auth.');
    });
    it('filters out turns with neither parts nor content', () => {
        const normalized = normalizeHistory([
            { role: 'user' },
        ]);
        assert.strictEqual(normalized.length, 0);
    });
    it('handles mixed history', () => {
        const normalized = normalizeHistory([
            { role: 'user', content: 'Q1' },
            { role: 'model', parts: ['A1'] },
            { role: 'user', content: 'Q2' },
        ]);
        assert.strictEqual(normalized.length, 3);
        assert.strictEqual(normalized[1].role, 'assistant');
        assert.strictEqual(normalized[1].content, 'A1');
    });
});
//# sourceMappingURL=chat.test.js.map