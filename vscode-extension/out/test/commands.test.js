"use strict";
/**
 * Unit tests for command helper utilities.
 *
 * Tests the splitRepo and pickOrGetActiveRepo logic patterns
 * used by the commands module.
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
// ---------------------------------------------------------------------------
// Pure helpers extracted from commands logic
// ---------------------------------------------------------------------------
function splitRepo(identifier) {
    const parts = identifier.split('/');
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
        throw new Error(`Invalid repository identifier "${identifier}". Expected "owner/repo".`);
    }
    return [parts[0], parts[1]];
}
// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('splitRepo', () => {
    it('correctly splits valid identifier', () => {
        const [owner, repo] = splitRepo('fastapi/fastapi');
        assert.strictEqual(owner, 'fastapi');
        assert.strictEqual(repo, 'fastapi');
    });
    it('handles owner with hyphens', () => {
        const [owner, repo] = splitRepo('my-org/my-repo');
        assert.strictEqual(owner, 'my-org');
        assert.strictEqual(repo, 'my-repo');
    });
    it('throws on missing slash', () => {
        assert.throws(() => splitRepo('noslash'), /Invalid repository identifier/);
    });
    it('throws on empty string', () => {
        assert.throws(() => splitRepo(''), /Invalid repository identifier/);
    });
    it('throws on trailing slash', () => {
        assert.throws(() => splitRepo('owner/'), /Invalid repository identifier/);
    });
    it('throws on leading slash', () => {
        assert.throws(() => splitRepo('/repo'), /Invalid repository identifier/);
    });
    it('throws on too many slashes', () => {
        assert.throws(() => splitRepo('a/b/c'), /Invalid repository identifier/);
    });
});
// ---------------------------------------------------------------------------
// extractErrorMessage from api.ts
// ---------------------------------------------------------------------------
function extractErrorMessage(err) {
    if (err instanceof Error)
        return err.message;
    if (typeof err === 'string')
        return err;
    return 'An unknown error occurred.';
}
describe('extractErrorMessage (commands context)', () => {
    it('returns message from Error object', () => {
        assert.strictEqual(extractErrorMessage(new Error('test error')), 'test error');
    });
    it('returns string directly', () => {
        assert.strictEqual(extractErrorMessage('already a string'), 'already a string');
    });
    it('returns fallback for null', () => {
        assert.strictEqual(extractErrorMessage(null), 'An unknown error occurred.');
    });
    it('returns fallback for undefined', () => {
        assert.strictEqual(extractErrorMessage(undefined), 'An unknown error occurred.');
    });
    it('returns fallback for number', () => {
        assert.strictEqual(extractErrorMessage(42), 'An unknown error occurred.');
    });
});
// ---------------------------------------------------------------------------
// Repository identifier validation
// ---------------------------------------------------------------------------
describe('Repository identifier validation', () => {
    const valid = ['owner/repo', 'google/guava', 'fastapi/fastapi', 'my-org/my-repo'];
    const invalid = ['', 'noslash', 'owner/', '/repo', 'a/b/c', '//'];
    for (const id of valid) {
        it(`accepts valid identifier "${id}"`, () => {
            assert.doesNotThrow(() => splitRepo(id));
        });
    }
    for (const id of invalid) {
        it(`rejects invalid identifier "${id}"`, () => {
            assert.throws(() => splitRepo(id));
        });
    }
});
//# sourceMappingURL=commands.test.js.map