/**
 * Interactive Call Graph panel.
 *
 * Renders function-level call relationships from
 * GET /api/call-graph/{owner}/{repo}
 *
 * Reuses the same canvas-based graph renderer as DependencyGraphPanel.
 * Supports search, node selection showing callers/callees, and blast radius.
 */
import * as vscode from 'vscode';
import { RepoIntelligenceClient } from '../api';
export declare class CallGraphPanel {
    static readonly viewType = "repoIntelligenceCallGraph";
    private static _panels;
    private readonly _panel;
    private readonly _owner;
    private readonly _repo;
    private readonly _client;
    static createOrShow(extensionUri: vscode.Uri, owner: string, repo: string, client: RepoIntelligenceClient): void;
    private constructor();
    private _loadGraph;
    private _handleMessage;
    private _buildHtml;
}
//# sourceMappingURL=callGraphPanel.d.ts.map