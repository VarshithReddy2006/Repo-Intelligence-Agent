/**
 * Architecture Health & API Surface panel.
 *
 * Shows architecture summary, component relationships, API surface stats,
 * deprecated symbols, and orphan public APIs from the backend.
 */
import * as vscode from 'vscode';
import { RepoIntelligenceClient } from '../api';
export declare class ArchitectureHealthPanel {
    static readonly viewType = "repoIntelligenceArchHealth";
    private static _panels;
    private readonly _panel;
    private readonly _owner;
    private readonly _repo;
    private readonly _client;
    static createOrShow(extensionUri: vscode.Uri, owner: string, repo: string, client: RepoIntelligenceClient): void;
    private constructor();
    private _loadData;
    private _handleMessage;
    private _buildLoadingHtml;
    private _buildHtml;
    private _esc;
}
//# sourceMappingURL=architectureHealthPanel.d.ts.map