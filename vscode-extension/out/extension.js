"use strict";
/**
 * Extension entry point — activate and deactivate lifecycle hooks.
 *
 * Responsibilities:
 *  - Register all commands
 *  - Register language providers (hover, CodeLens)
 *  - Register tree-view data providers
 *  - Check backend health on activation
 *
 * No analysis logic lives here. Every feature delegates to a dedicated
 * provider, panel, or API client module.
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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const commands_1 = require("./commands");
const hoverProvider_1 = require("./providers/hoverProvider");
const codeLensProvider_1 = require("./providers/codeLensProvider");
const treeViewProvider_1 = require("./providers/treeViewProvider");
const api_1 = require("./api");
// Status bar item shared across the extension
let statusBarItem;
function activate(context) {
    // ── Status bar ─────────────────────────────────────────────────────────
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBarItem.command = 'repoIntelligence.openDashboard';
    statusBarItem.text = '$(repo) Repo Intelligence';
    statusBarItem.tooltip = 'Open Repo Intelligence Dashboard';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // ── Language providers ─────────────────────────────────────────────────
    const cfg = vscode.workspace.getConfiguration('repoIntelligence');
    if (cfg.get('hover.enabled') !== false) {
        const hoverProvider = new hoverProvider_1.RepoIntelligenceHoverProvider();
        context.subscriptions.push(vscode.languages.registerHoverProvider([
            { language: 'python' },
            { language: 'javascript' },
            { language: 'typescript' },
            { language: 'javascriptreact' },
            { language: 'typescriptreact' },
        ], hoverProvider));
    }
    if (cfg.get('codeLens.enabled') !== false) {
        const codeLensProvider = new codeLensProvider_1.RepoIntelligenceCodeLensProvider();
        context.subscriptions.push(vscode.languages.registerCodeLensProvider([
            { language: 'python' },
            { language: 'javascript' },
            { language: 'typescript' },
            { language: 'javascriptreact' },
            { language: 'typescriptreact' },
        ], codeLensProvider));
    }
    // ── Tree view ──────────────────────────────────────────────────────────
    const explorerProvider = new treeViewProvider_1.RepositoryExplorerProvider(context);
    const treeView = vscode.window.createTreeView('repoIntelligenceExplorer', {
        treeDataProvider: explorerProvider,
        showCollapseAll: true,
    });
    context.subscriptions.push(treeView);
    // Allow commands to refresh the tree
    context.subscriptions.push(vscode.commands.registerCommand('repoIntelligence.explorerRefresh', () => {
        explorerProvider.refresh();
    }));
    // ── All other commands ─────────────────────────────────────────────────
    (0, commands_1.registerCommands)(context, explorerProvider);
    // ── Configuration changes ──────────────────────────────────────────────
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('repoIntelligence')) {
            explorerProvider.refresh();
        }
    }));
    // ── Auto-refresh on save ───────────────────────────────────────────────
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(() => {
        const autoCfg = vscode.workspace.getConfiguration('repoIntelligence');
        if (autoCfg.get('autoRefresh')) {
            explorerProvider.refresh();
        }
    }));
    // ── Initial health probe ───────────────────────────────────────────────
    void checkBackendHealth(statusBarItem);
}
function deactivate() {
    // Dispose is handled automatically via subscriptions
}
/**
 * Probe the backend on startup and update the status bar.
 * Never throws — failure just changes the status bar icon.
 */
async function checkBackendHealth(bar) {
    try {
        const health = await api_1.client.health();
        if (health.status === 'healthy') {
            bar.text = '$(check) Repo Intelligence';
            bar.tooltip = `Backend online — ${health.llm_model}`;
            bar.backgroundColor = undefined;
        }
        else {
            bar.text = '$(warning) Repo Intelligence';
            bar.tooltip = 'Backend reachable but reported unhealthy status.';
        }
    }
    catch (err) {
        bar.text = '$(circle-slash) Repo Intelligence';
        bar.tooltip = `Backend offline: ${(0, api_1.extractErrorMessage)(err)}. Click to open dashboard.`;
        bar.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }
}
//# sourceMappingURL=extension.js.map