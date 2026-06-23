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
import * as vscode from 'vscode';
export type ExplorerNodeKind = 'root' | 'section' | 'repo' | 'overview' | 'architecture' | 'stability' | 'api-surface' | 'git-churn' | 'dead-code' | 'call-graph' | 'stat' | 'error' | 'loading' | 'empty';
export declare class ExplorerNode extends vscode.TreeItem {
    readonly kind: ExplorerNodeKind;
    readonly repoId?: string | undefined;
    readonly meta?: Record<string, unknown> | undefined;
    constructor(kind: ExplorerNodeKind, label: string, collapsible: vscode.TreeItemCollapsibleState, repoId?: string | undefined, meta?: Record<string, unknown> | undefined);
    private _applyIcon;
    private _applyCommand;
}
export declare class RepositoryExplorerProvider implements vscode.TreeDataProvider<ExplorerNode> {
    private readonly _context;
    private readonly _onDidChangeTreeData;
    readonly onDidChangeTreeData: vscode.Event<void | ExplorerNode | undefined>;
    private readonly _cache;
    private _recentRepos;
    private _loadingRepos;
    constructor(_context: vscode.ExtensionContext);
    refresh(): void;
    getTreeItem(element: ExplorerNode): vscode.TreeItem;
    getChildren(element?: ExplorerNode): Promise<ExplorerNode[]>;
    private _getRootNodes;
    private _getSections;
    private _getSectionChildren;
    private _loadSectionData;
    private _loadOverview;
    private _loadArchitecture;
    private _loadAPISurface;
    private _loadChurn;
    private _loadCallGraphStats;
    private _makeStatNode;
}
//# sourceMappingURL=treeViewProvider.d.ts.map