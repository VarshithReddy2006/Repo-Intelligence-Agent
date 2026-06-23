"use strict";
/**
 * CodeLens provider — renders action links above every function and class
 * definition in the active file.
 *
 * Each lens triggers one of the registered extension commands with pre-filled
 * arguments derived from the current file's symbol index.
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
exports.RepoIntelligenceCodeLensProvider = void 0;
const vscode = __importStar(require("vscode"));
const api_1 = require("../api");
// Simple LRU cache: one entry per open document
const symbolCache = new Map();
function getActiveRepo() {
    return (vscode.workspace.getConfiguration('repoIntelligence').get('activeRepository') ?? '');
}
function repoToOwnerRepo(id) {
    const p = id.split('/');
    return p.length === 2 && p[0] && p[1] ? [p[0], p[1]] : null;
}
function getRelativePath(document) {
    const ws = vscode.workspace.getWorkspaceFolder(document.uri);
    return ws ? vscode.workspace.asRelativePath(document.uri, false) : document.uri.fsPath;
}
// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
class RepoIntelligenceCodeLensProvider {
    constructor() {
        this._onDidChangeCodeLenses = new vscode.EventEmitter();
        this.onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
        this._configWatcher = vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('repoIntelligence')) {
                this._onDidChangeCodeLenses.fire();
            }
        });
    }
    dispose() {
        this._configWatcher.dispose();
        this._onDidChangeCodeLenses.dispose();
    }
    async provideCodeLenses(document, token) {
        if (!vscode.workspace.getConfiguration('repoIntelligence').get('codeLens.enabled')) {
            return [];
        }
        const repoId = getActiveRepo();
        if (!repoId) {
            return [];
        }
        const ownerRepo = repoToOwnerRepo(repoId);
        if (!ownerRepo) {
            return [];
        }
        const [owner, repo] = ownerRepo;
        const filePath = getRelativePath(document);
        // Invalidate stale cache
        const cached = symbolCache.get(document.uri.toString());
        let symbols;
        if (cached && cached.version === document.version) {
            symbols = cached.symbols;
        }
        else {
            try {
                const result = await api_1.client.getFileSymbols(owner, repo, filePath);
                symbols = result.symbols;
                symbolCache.set(document.uri.toString(), {
                    symbols,
                    version: document.version,
                });
            }
            catch {
                return [];
            }
        }
        if (token.isCancellationRequested) {
            return [];
        }
        const lenses = [];
        for (const symbol of symbols) {
            if (symbol.symbol_type !== 'function' &&
                symbol.symbol_type !== 'method' &&
                symbol.symbol_type !== 'class') {
                continue;
            }
            const lineIndex = Math.max(0, symbol.line_number - 1);
            const range = new vscode.Range(lineIndex, 0, lineIndex, 0);
            const functionId = encodeURIComponent(`${filePath}::${symbol.qualified}`);
            // ── Show Callers ───────────────────────────────────────────────────
            lenses.push(new vscode.CodeLens(range, {
                title: `$(arrow-left) Callers${typeof symbol.fan_in === 'number' ? ` (${symbol.fan_in})` : ''}`,
                command: 'repoIntelligence.showCallers',
                arguments: [{ owner, repo, functionId }],
                tooltip: 'Show all functions that call this one',
            }));
            // ── Show Callees ───────────────────────────────────────────────────
            lenses.push(new vscode.CodeLens(range, {
                title: `$(arrow-right) Callees${typeof symbol.fan_out === 'number' ? ` (${symbol.fan_out})` : ''}`,
                command: 'repoIntelligence.showCallees',
                arguments: [{ owner, repo, functionId }],
                tooltip: 'Show all functions called by this one',
            }));
            // ── Blast Radius (functions and methods only) ──────────────────────
            if (symbol.symbol_type !== 'class') {
                lenses.push(new vscode.CodeLens(range, {
                    title: '$(pulse) Blast Radius',
                    command: 'repoIntelligence.showBlastRadius',
                    arguments: [{ owner, repo, functionId }],
                    tooltip: 'Compute the change impact radius of this function',
                }));
            }
            // ── Impact Analysis (classes only, or any symbol) ──────────────────
            lenses.push(new vscode.CodeLens(range, {
                title: '$(beaker) Impact Analysis',
                command: 'repoIntelligence.showImpactAnalysis',
                arguments: [
                    {
                        repo: `${owner}/${repo}`,
                        issue: `Change to ${symbol.qualified}`,
                    },
                ],
                tooltip: 'Predict impact of modifying this symbol',
            }));
            // ── Reading Path ──────────────────────────────────────────────────
            lenses.push(new vscode.CodeLens(range, {
                title: '$(book) Reading Path',
                command: 'repoIntelligence.showReadingPathForFile',
                arguments: [{ file: filePath }],
                tooltip: 'Generate recommended reading order from this file',
            }));
        }
        return lenses;
    }
    resolveCodeLens(lens) {
        return lens;
    }
}
exports.RepoIntelligenceCodeLensProvider = RepoIntelligenceCodeLensProvider;
//# sourceMappingURL=codeLensProvider.js.map