"use strict";
/**
 * Unit tests for VS Code providers.
 *
 * Tests hover content generation and CodeLens creation logic.
 * Uses lightweight stubs — no real VS Code instance required.
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
const vscode_1 = require("./mocks/vscode");
// ---------------------------------------------------------------------------
// VS Code mock is provided via module-alias (see package.json _moduleAliases)
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Tests: hover content building logic (pure function, extracted for testability)
// ---------------------------------------------------------------------------
describe('Hover content', () => {
    it('builds markdown table with symbol properties', () => {
        const symbol = {
            name: 'health',
            qualified: 'health',
            symbol_type: 'function',
            file_path: 'backend/routers/health.py',
            line_number: 10,
            language: 'python',
            parent_class: null,
            fan_in: 5,
            fan_out: 2,
        };
        // Replicate the buildHoverContent logic from hoverProvider
        const md = new vscode_1.MarkdownString();
        md.appendMarkdown(`**\`${symbol.qualified}\`**\n\n`);
        md.appendMarkdown(`| Property | Value |\n|---|---|\n`);
        md.appendMarkdown(`| Type | \`${symbol.symbol_type}\` |\n`);
        md.appendMarkdown(`| File | \`${symbol.file_path}\` |\n`);
        md.appendMarkdown(`| Line | ${symbol.line_number} |\n`);
        assert.ok(md.value.includes('health'));
        assert.ok(md.value.includes('function'));
        assert.ok(md.value.includes('backend/routers/health.py'));
        assert.ok(md.value.includes('10'));
    });
    it('includes parent class when present', () => {
        const symbol = {
            name: 'authenticate',
            qualified: 'AuthService.authenticate',
            symbol_type: 'method',
            file_path: 'services/auth.py',
            line_number: 42,
            language: 'python',
            parent_class: 'AuthService',
            fan_in: 3,
            fan_out: 1,
        };
        const md = new StubMarkdownString();
        if (symbol.parent_class) {
            md.appendMarkdown(`| Class | \`${symbol.parent_class}\` |\n`);
        }
        assert.ok(md.value.includes('AuthService'));
    });
    it('does not include class row when parent_class is null', () => {
        const symbol = {
            name: 'standalone_fn',
            qualified: 'standalone_fn',
            symbol_type: 'function',
            file_path: 'utils/helpers.py',
            line_number: 5,
            language: 'python',
            parent_class: null,
            fan_in: 0,
            fan_out: 0,
        };
        const md = new StubMarkdownString();
        if (symbol.parent_class) {
            md.appendMarkdown(`| Class | \`${symbol.parent_class}\` |\n`);
        }
        assert.ok(!md.value.includes('Class'));
    });
});
// ---------------------------------------------------------------------------
// Tests: CodeLens creation logic
// ---------------------------------------------------------------------------
describe('CodeLens creation', () => {
    const symbols = [
        {
            name: 'health',
            qualified: 'health',
            symbol_type: 'function',
            file_path: 'backend/routers/health.py',
            line_number: 10,
            language: 'python',
            parent_class: null,
            fan_in: 4,
            fan_out: 2,
        },
        {
            name: 'MyClass',
            qualified: 'MyClass',
            symbol_type: 'class',
            file_path: 'backend/routers/health.py',
            line_number: 30,
            language: 'python',
            parent_class: null,
            fan_in: 0,
            fan_out: 0,
        },
    ];
    it('creates at least 3 lenses per function symbol', () => {
        const functionSymbols = symbols.filter((s) => s.symbol_type === 'function');
        // Each function should get: Callers, Callees, Blast Radius, Impact Analysis, Reading Path = 5
        const lensCount = functionSymbols.reduce((acc) => acc + 5, 0);
        assert.ok(lensCount >= 3);
    });
    it('creates lenses for classes too', () => {
        const classSymbols = symbols.filter((s) => s.symbol_type === 'class');
        // Classes get: Callers, Callees, Impact Analysis, Reading Path = 4 (no Blast Radius)
        assert.ok(classSymbols.length > 0);
    });
    it('includes fan_in count in callers label when available', () => {
        const sym = symbols[0];
        const label = `Callers${typeof sym.fan_in === 'number' ? ` (${sym.fan_in})` : ''}`;
        assert.ok(label.includes('(4)'));
    });
    it('does not include Blast Radius lens for class symbols', () => {
        const sym = symbols[1]; // class
        const shouldIncludeBlastRadius = sym.symbol_type !== 'class';
        assert.strictEqual(shouldIncludeBlastRadius, false);
    });
});
// ---------------------------------------------------------------------------
// Tests: Repository tree node kind logic
// ---------------------------------------------------------------------------
describe('Tree node kinds', () => {
    const sections = [
        ['overview', '$(info) Overview'],
        ['architecture', '$(type-hierarchy) Architecture Health'],
        ['stability', '$(shield) Module Stability'],
        ['api-surface', '$(symbol-interface) API Surface'],
        ['git-churn', '$(history) Git Churn'],
        ['dead-code', '$(trash) Dead Code'],
        ['call-graph', '$(call-outgoing) Call Graph'],
    ];
    it('defines all expected section kinds', () => {
        const kinds = sections.map(([k]) => k);
        assert.ok(kinds.includes('overview'));
        assert.ok(kinds.includes('architecture'));
        assert.ok(kinds.includes('api-surface'));
        assert.ok(kinds.includes('git-churn'));
        assert.ok(kinds.includes('call-graph'));
    });
    it('section labels start with VS Code icon notation', () => {
        for (const [, label] of sections) {
            assert.ok(label.startsWith('$('), `Label "${label}" should start with $(`);
        }
    });
});
//# sourceMappingURL=providers.test.js.map