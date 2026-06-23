"use strict";
/**
 * Unit tests for settings/configuration defaults and validation.
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
const DEFAULT_CONFIG = {
    backendUrl: 'http://127.0.0.1:8001',
    apiToken: '',
    activeRepository: '',
    autoRefresh: false,
    requestTimeoutMs: 15000,
    graphLayout: 'dagre',
    theme: 'auto',
    'codeLens.enabled': true,
    'hover.enabled': true,
};
function normalizeBackendUrl(url) {
    return url.replace(/\/$/, '');
}
function validateConfig(cfg) {
    const errors = [];
    if (cfg.backendUrl !== undefined) {
        try {
            new URL(cfg.backendUrl);
        }
        catch {
            errors.push(`backendUrl "${cfg.backendUrl}" is not a valid URL`);
        }
    }
    if (cfg.requestTimeoutMs !== undefined) {
        if (cfg.requestTimeoutMs < 1000) {
            errors.push('requestTimeoutMs must be at least 1000ms');
        }
        if (cfg.requestTimeoutMs > 120000) {
            errors.push('requestTimeoutMs must be at most 120000ms (2 minutes)');
        }
    }
    if (cfg.graphLayout !== undefined) {
        if (!['dagre', 'force', 'radial'].includes(cfg.graphLayout)) {
            errors.push(`graphLayout "${cfg.graphLayout}" is not a valid layout`);
        }
    }
    if (cfg.theme !== undefined) {
        if (!['auto', 'dark', 'light'].includes(cfg.theme)) {
            errors.push(`theme "${cfg.theme}" is not a valid theme`);
        }
    }
    return { valid: errors.length === 0, errors };
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('Default configuration', () => {
    it('has valid default backend URL', () => {
        const result = validateConfig({ backendUrl: DEFAULT_CONFIG.backendUrl });
        assert.ok(result.valid, result.errors.join(', '));
    });
    it('has valid default timeout', () => {
        const result = validateConfig({ requestTimeoutMs: DEFAULT_CONFIG.requestTimeoutMs });
        assert.ok(result.valid, result.errors.join(', '));
    });
    it('has valid default graph layout', () => {
        const result = validateConfig({ graphLayout: DEFAULT_CONFIG.graphLayout });
        assert.ok(result.valid, result.errors.join(', '));
    });
    it('has valid default theme', () => {
        const result = validateConfig({ theme: DEFAULT_CONFIG.theme });
        assert.ok(result.valid, result.errors.join(', '));
    });
    it('autoRefresh defaults to false', () => {
        assert.strictEqual(DEFAULT_CONFIG.autoRefresh, false);
    });
    it('codeLens.enabled defaults to true', () => {
        assert.strictEqual(DEFAULT_CONFIG['codeLens.enabled'], true);
    });
    it('hover.enabled defaults to true', () => {
        assert.strictEqual(DEFAULT_CONFIG['hover.enabled'], true);
    });
});
describe('normalizeBackendUrl', () => {
    it('removes trailing slash', () => {
        assert.strictEqual(normalizeBackendUrl('http://127.0.0.1:8001/'), 'http://127.0.0.1:8001');
    });
    it('leaves URL without trailing slash unchanged', () => {
        assert.strictEqual(normalizeBackendUrl('http://127.0.0.1:8001'), 'http://127.0.0.1:8001');
    });
    it('handles HTTPS URL', () => {
        assert.strictEqual(normalizeBackendUrl('https://api.example.com/'), 'https://api.example.com');
    });
});
describe('Configuration validation', () => {
    it('accepts valid HTTP URL', () => {
        const { valid } = validateConfig({ backendUrl: 'http://localhost:8001' });
        assert.ok(valid);
    });
    it('accepts valid HTTPS URL', () => {
        const { valid } = validateConfig({ backendUrl: 'https://api.example.com' });
        assert.ok(valid);
    });
    it('rejects invalid URL', () => {
        const { valid, errors } = validateConfig({ backendUrl: 'not-a-url' });
        assert.strictEqual(valid, false);
        assert.ok(errors.length > 0);
    });
    it('rejects timeout below 1000ms', () => {
        const { valid, errors } = validateConfig({ requestTimeoutMs: 500 });
        assert.strictEqual(valid, false);
        assert.ok(errors.some((e) => e.includes('1000ms')));
    });
    it('rejects timeout above 120000ms', () => {
        const { valid, errors } = validateConfig({ requestTimeoutMs: 999999 });
        assert.strictEqual(valid, false);
        assert.ok(errors.some((e) => e.includes('120000ms')));
    });
    it('rejects invalid graph layout', () => {
        const { valid, errors } = validateConfig({
            graphLayout: 'invalid',
        });
        assert.strictEqual(valid, false);
        assert.ok(errors.some((e) => e.includes('graphLayout')));
    });
    it('rejects invalid theme', () => {
        const { valid, errors } = validateConfig({ theme: 'rainbow' });
        assert.strictEqual(valid, false);
        assert.ok(errors.some((e) => e.includes('theme')));
    });
    it('accepts all valid graph layouts', () => {
        for (const layout of ['dagre', 'force', 'radial']) {
            const { valid } = validateConfig({ graphLayout: layout });
            assert.ok(valid, `Layout "${layout}" should be valid`);
        }
    });
    it('accepts all valid themes', () => {
        for (const theme of ['auto', 'dark', 'light']) {
            const { valid } = validateConfig({ theme });
            assert.ok(valid, `Theme "${theme}" should be valid`);
        }
    });
});
//# sourceMappingURL=settings.test.js.map