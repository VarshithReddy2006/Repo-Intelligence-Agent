"use strict";
/**
 * Repository Explorer tree view provider.
 *
 * Renders a structured tree in the Activity Bar panel with the following shape:
 *
 *   📁 <owner/repo>
 *     ├── 📋 Overview
 *     ├── 🏗  Architecture Health
 *     ├── 📊 Module Stability
 *     ├── 🔌 API Surface
 *     ├── 📈 Git Churn
 *     ├── ☠  Dead Code
 *     └── 📞 Call Graph
 *
 * All data is fetched lazily when the node is expanded for the first time.
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
exports.RepositoryExplorerProvider = exports.ExplorerNode = void 0;
const vscode = __importStar(require("vscode"));
const api_1 = require("../api");
class ExplorerNode extends vscode.TreeItem {
    constructor(kind, label, collapsible, repoId, meta) {
        super(label, collapsible);
        this.kind = kind;
        this.repoId = repoId;
        this.meta = meta;
        this.contextValue = kind;
        this._applyIcon();
        this._applyCommand();
    }
    _applyIcon() {
        const iconMap = {
            root: 'library',
            section: 'folder',
            repo: 'repo',
            overview: 'info',
            architecture: 'type-hierarchy',
            stability: 'shield',
            'api-surface': 'symbol-interface',
            'git-churn': 'history',
            'dead-code': 'trash',
            'call-graph': 'call-outgoing',
            stat: 'dash',
            error: 'error',
            loading: 'loading~spin',
            empty: 'circle-slash',
        };
        this.iconPath = new vscode.ThemeIcon(iconMap[this.kind] ?? 'circle');
    }
    _applyCommand() {
        if (this.kind === 'architecture') {
            this.command = {
                command: 'repoIntelligence.showArchitectureHealth',
                title: 'Show Architecture Health',
            };
        }
        else if (this.kind === 'api-surface') {
            this.command = {
                command: 'repoIntelligence.showAPISurface',
                title: 'Show API Surface',
            };
        }
        else if (this.kind === 'call-graph') {
            this.command = {
                command: 'repoIntelligence.showCallGraph',
                title: 'Show Call Graph',
            };
        }
        else if (this.kind === 'overview') {
            this.command = {
                command: 'repoIntelligence.openDashboard',
                title: 'Open Dashboard',
            };
        }
    }
}
exports.ExplorerNode = ExplorerNode;
// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
class RepositoryExplorerProvider {
    constructor(_context) {
        this._context = _context;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        // Lazy-load cache per repo section
        this._cache = new Map();
        this._recentRepos = [];
        this._loadingRepos = false;
    }
    refresh() {
        this._cache.clear();
        this._recentRepos = [];
        this._loadingRepos = false;
        this._onDidChangeTreeData.fire();
    }
    getTreeItem(element) {
        return element;
    }
    async getChildren(element) {
        // ── Root ──────────────────────────────────────────────────────────────
        if (!element) {
            return this._getRootNodes();
        }
        // ── Repo node → sections ──────────────────────────────────────────────
        if (element.kind === 'repo' && element.repoId) {
            return this._getSections(element.repoId);
        }
        // ── Section nodes → stats ─────────────────────────────────────────────
        if (element.repoId && element.kind !== 'repo') {
            return this._getSectionChildren(element);
        }
        return [];
    }
    // ── Root ───────────────────────────────────────────────────────────────
    async _getRootNodes() {
        const cfg = vscode.workspace.getConfiguration('repoIntelligence');
        const activeRepo = cfg.get('activeRepository') ?? '';
        if (!this._loadingRepos && this._recentRepos.length === 0) {
            this._loadingRepos = true;
            try {
                this._recentRepos = await api_1.client.getRecentRepos();
            }
            catch {
                this._recentRepos = [];
            }
        }
        const nodes = [];
        if (activeRepo) {
            const node = new ExplorerNode('repo', `$(star) ${activeRepo}`, vscode.TreeItemCollapsibleState.Expanded, activeRepo);
            node.description = 'active';
            nodes.push(node);
        }
        for (const r of this._recentRepos) {
            if (r.name === activeRepo) {
                continue;
            }
            const node = new ExplorerNode('repo', r.name, vscode.TreeItemCollapsibleState.Collapsed, r.name);
            node.description = r.tech_stack.slice(0, 3).join(', ');
            nodes.push(node);
        }
        if (nodes.length === 0) {
            const empty = new ExplorerNode('empty', 'No repositories connected', vscode.TreeItemCollapsibleState.None);
            empty.description = 'Run "Repo Intelligence: Set Active Repository"';
            return [empty];
        }
        return nodes;
    }
    // ── Sections for a repo ──────────────────────────────────────────────
    _getSections(repoId) {
        const sections = [
            ['overview', '$(info) Overview'],
            ['architecture', '$(type-hierarchy) Architecture Health'],
            ['stability', '$(shield) Module Stability'],
            ['api-surface', '$(symbol-interface) API Surface'],
            ['git-churn', '$(history) Git Churn'],
            ['dead-code', '$(trash) Dead Code'],
            ['call-graph', '$(call-outgoing) Call Graph'],
        ];
        return sections.map(([kind, label]) => {
            const node = new ExplorerNode(kind, label, vscode.TreeItemCollapsibleState.Collapsed, repoId);
            return node;
        });
    }
    // ── Section children (stat rows) ─────────────────────────────────────
    async _getSectionChildren(section) {
        const cacheKey = `${section.repoId}::${section.kind}`;
        if (this._cache.has(cacheKey)) {
            return this._cache.get(cacheKey);
        }
        const repoId = section.repoId;
        const parts = repoId.split('/');
        if (parts.length !== 2) {
            return [];
        }
        const [owner, repo] = parts;
        const loading = new ExplorerNode('loading', 'Loading…', vscode.TreeItemCollapsibleState.None);
        // Fire async, update cache when done
        void this._loadSectionData(section.kind, owner, repo, cacheKey);
        return [loading];
    }
    async _loadSectionData(kind, owner, repo, cacheKey) {
        try {
            let nodes = [];
            switch (kind) {
                case 'overview':
                    nodes = await this._loadOverview(owner, repo);
                    break;
                case 'architecture':
                    nodes = await this._loadArchitecture(owner, repo);
                    break;
                case 'api-surface':
                    nodes = await this._loadAPISurface(owner, repo);
                    break;
                case 'git-churn':
                    nodes = await this._loadChurn(owner, repo);
                    break;
                case 'call-graph':
                    nodes = await this._loadCallGraphStats(owner, repo);
                    break;
                default:
                    nodes = [
                        this._makeStatNode(`${kind} data available via Dashboard`, '$(arrow-right)'),
                    ];
            }
            this._cache.set(cacheKey, nodes);
        }
        catch (err) {
            const errorNode = new ExplorerNode('error', `Error: ${(0, api_1.extractErrorMessage)(err)}`, vscode.TreeItemCollapsibleState.None);
            this._cache.set(cacheKey, [errorNode]);
        }
        this._onDidChangeTreeData.fire();
    }
    // ── Section data loaders ─────────────────────────────────────────────
    async _loadOverview(owner, repo) {
        const details = await api_1.client.getAnalysis(owner, repo);
        const analysis = details.analysis;
        const nodes = [];
        nodes.push(this._makeStatNode(`Tech: ${(analysis.tech_stack ?? []).slice(0, 4).join(', ') || 'N/A'}`));
        nodes.push(this._makeStatNode(`Dependencies: ${(analysis.dependencies ?? []).length}`));
        const arch = details.architecture;
        if (arch?.summary) {
            const summaryNode = new ExplorerNode('stat', 'Architecture Summary', vscode.TreeItemCollapsibleState.None);
            summaryNode.description = arch.summary.slice(0, 80);
            summaryNode.tooltip = arch.summary;
            nodes.push(summaryNode);
        }
        return nodes;
    }
    async _loadArchitecture(owner, repo) {
        try {
            const summary = await api_1.client.getArchitectureSummary(owner, repo);
            const nodes = [];
            nodes.push(this._makeStatNode(`Reading order entries: ${(summary.reading_order ?? []).length}`));
            nodes.push(this._makeStatNode(`Component relationships: ${(summary.relationships ?? []).length}`));
            return nodes;
        }
        catch {
            return [
                this._makeStatNode('Not analyzed yet — run Architecture Build', '$(warning)'),
            ];
        }
    }
    async _loadAPISurface(owner, repo) {
        try {
            const stats = await api_1.client.getAPISurfaceStats(owner, repo);
            return [
                this._makeStatNode(`Total symbols: ${stats.total_symbols}`),
                this._makeStatNode(`Public: ${stats.public_count}`),
                this._makeStatNode(`Internal: ${stats.internal_count}`),
                this._makeStatNode(`Deprecated: ${stats.deprecated_count}`),
                this._makeStatNode(`Orphan public: ${stats.orphan_public_count}`),
                this._makeStatNode(`Routes: ${stats.route_count}`),
            ];
        }
        catch {
            return [this._makeStatNode('API Surface not built yet', '$(warning)')];
        }
    }
    async _loadChurn(owner, repo) {
        try {
            const hotspots = await api_1.client.getChurnHotspots(owner, repo, 10, 365);
            const nodes = [
                this._makeStatNode(`Top ${hotspots.hotspots.length} hotspot files:`),
            ];
            for (const h of hotspots.hotspots.slice(0, 10)) {
                const n = this._makeStatNode(h.file_path, '$(file-code)');
                n.description = `commits: ${h.commit_count}`;
                n.tooltip = `Churn score: ${h.churn_score}`;
                nodes.push(n);
            }
            return nodes;
        }
        catch {
            return [this._makeStatNode('Churn data not available', '$(warning)')];
        }
    }
    async _loadCallGraphStats(owner, repo) {
        try {
            const stats = await api_1.client.fetchJson(`/api/call-graph/${owner}/${repo}/stats`);
            return [
                this._makeStatNode(`Functions: ${String(stats.node_count ?? 'N/A')}`),
                this._makeStatNode(`Call edges: ${String(stats.edge_count ?? 'N/A')}`),
                this._makeStatNode(`Entry points: ${String(stats.entry_count ?? 'N/A')}`),
            ];
        }
        catch {
            return [this._makeStatNode('Call graph not built yet', '$(warning)')];
        }
    }
    // ── Helpers ─────────────────────────────────────────────────────────
    _makeStatNode(label, icon) {
        const node = new ExplorerNode('stat', label, vscode.TreeItemCollapsibleState.None);
        if (icon) {
            node.iconPath = new vscode.ThemeIcon(icon.replace(/^\$\(/, '').replace(/\)$/, ''));
        }
        return node;
    }
}
exports.RepositoryExplorerProvider = RepositoryExplorerProvider;
//# sourceMappingURL=treeViewProvider.js.map