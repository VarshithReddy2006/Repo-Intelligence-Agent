"use strict";
/**
 * Hover provider — shows symbol intelligence cards when the developer hovers
 * over a function or class name.
 *
 * Data is fetched from the backend symbol index and call graph.
 * Results are cached per file to avoid hammering the backend on every mouseover.
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
exports.RepoIntelligenceHoverProvider = void 0;
const vscode = __importStar(require("vscode"));
const api_1 = require("../api");
// Cache: repoKey -> filePath -> symbols[]
const symbolCache = new Map();
// Track in-flight requests to debounce
const inFlight = new Set();
function getActiveRepo() {
    return (vscode.workspace.getConfiguration('repoIntelligence').get('activeRepository') ?? '');
}
function repoToOwnerRepo(identifier) {
    const parts = identifier.split('/');
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
        return null;
    }
    return [parts[0], parts[1]];
}
/**
 * Get the relative file path of the document within the workspace.
 */
function getRelativePath(document) {
    const wsFolder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (wsFolder) {
        return vscode.workspace.asRelativePath(document.uri, false);
    }
    return document.uri.fsPath;
}
/**
 * Fetch and cache symbols for a file. Returns null when the backend is
 * unreachable or no symbol index exists yet.
 */
async function getSymbolsForFile(owner, repo, filePath) {
    const repoKey = `${owner}/${repo}`;
    const fileCache = symbolCache.get(repoKey) ?? new Map();
    symbolCache.set(repoKey, fileCache);
    if (fileCache.has(filePath)) {
        return fileCache.get(filePath);
    }
    const cacheKey = `${repoKey}::${filePath}`;
    if (inFlight.has(cacheKey)) {
        return null; // debounce concurrent requests
    }
    inFlight.add(cacheKey);
    try {
        const result = await api_1.client.getFileSymbols(owner, repo, filePath);
        fileCache.set(filePath, result.symbols);
        return result.symbols;
    }
    catch {
        // Return null silently — hover should never surface errors to the user
        return null;
    }
    finally {
        inFlight.delete(cacheKey);
    }
}
/**
 * Find the symbol whose definition range contains the hover position.
 */
function findSymbolAtPosition(symbols, word) {
    // First try exact name match, then qualified name match
    return (symbols.find((s) => s.name === word) ??
        symbols.find((s) => s.qualified.endsWith(`.${word}`) || s.qualified === word) ??
        null);
}
/**
 * Build a rich Markdown hover card from a symbol and optional API surface info.
 */
function buildHoverContent(symbol) {
    const md = new vscode.MarkdownString();
    md.isTrusted = true;
    md.supportHtml = false;
    const typeIcon = symbol.symbol_type === 'class'
        ? '$(symbol-class)'
        : symbol.symbol_type === 'method'
            ? '$(symbol-method)'
            : '$(symbol-function)';
    md.appendMarkdown(`**${typeIcon} \`${symbol.qualified}\`**\n\n`);
    md.appendMarkdown(`| Property | Value |\n|---|---|\n`);
    md.appendMarkdown(`| Type | \`${symbol.symbol_type}\` |\n`);
    md.appendMarkdown(`| File | \`${symbol.file_path}\` |\n`);
    md.appendMarkdown(`| Line | ${symbol.line_number} |\n`);
    md.appendMarkdown(`| Language | ${symbol.language} |\n`);
    if (symbol.parent_class) {
        md.appendMarkdown(`| Class | \`${symbol.parent_class}\` |\n`);
    }
    if (typeof symbol.fan_in === 'number') {
        md.appendMarkdown(`| Fan-in (callers) | ${symbol.fan_in} |\n`);
    }
    if (typeof symbol.fan_out === 'number') {
        md.appendMarkdown(`| Fan-out (callees) | ${symbol.fan_out} |\n`);
    }
    md.appendMarkdown('\n---\n');
    md.appendMarkdown('_Repo Intelligence Agent_');
    return md;
}
// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
class RepoIntelligenceHoverProvider {
    async provideHover(document, position, _token) {
        const repoId = getActiveRepo();
        if (!repoId) {
            return null; // not connected to a repository
        }
        const ownerRepo = repoToOwnerRepo(repoId);
        if (!ownerRepo) {
            return null;
        }
        const [owner, repo] = ownerRepo;
        const wordRange = document.getWordRangeAtPosition(position, /[\w$]+/);
        if (!wordRange) {
            return null;
        }
        const word = document.getText(wordRange);
        if (!word || word.length < 2) {
            return null;
        }
        const filePath = getRelativePath(document);
        const symbols = await getSymbolsForFile(owner, repo, filePath);
        if (!symbols) {
            return null;
        }
        const symbol = findSymbolAtPosition(symbols, word);
        if (!symbol) {
            return null;
        }
        const content = buildHoverContent(symbol);
        return new vscode.Hover(content, wordRange);
    }
}
exports.RepoIntelligenceHoverProvider = RepoIntelligenceHoverProvider;
//# sourceMappingURL=hoverProvider.js.map