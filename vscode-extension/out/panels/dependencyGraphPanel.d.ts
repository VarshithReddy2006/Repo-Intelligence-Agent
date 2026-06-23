/**
 * Interactive Dependency Graph panel.
 *
 * Renders the React Flow compatible graph data returned by
 * GET /api/graph/{owner}/{repo}/full using a lightweight Canvas/SVG
 * implementation inside the webview (no React needed — just the raw data).
 *
 * Features: Pan, Zoom, Search, Highlight neighbors, Focus selected node.
 */
import * as vscode from 'vscode';
import { RepoIntelligenceClient } from '../api';
export declare class DependencyGraphPanel {
    static readonly viewType = "repoIntelligenceDepGraph";
    private static _panels;
    private readonly _panel;
    private readonly _owner;
    private readonly _repo;
    private readonly _client;
    static createOrShow(extensionUri: vscode.Uri, owner: string, repo: string, client: RepoIntelligenceClient): void;
    private constructor();
    private _loadGraph;
    private _handleMessage;
    private _loadSearch;
    private _loadNeighbors;
    private _buildHtml;
}
//# sourceMappingURL=dependencyGraphPanel.d.ts.map