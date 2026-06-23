/**
 * Repository Dashboard panel.
 *
 * Full-width webview showing KPIs, architecture health, API surface stats,
 * git churn hotspots, and recent analysis. All data is fetched from the
 * existing backend APIs — no analysis logic here.
 */
import * as vscode from 'vscode';
import { RepoIntelligenceClient } from '../api';
export declare class RepositoryDashboardPanel {
    static readonly viewType = "repoIntelligenceDashboard";
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
    private _buildErrorHtml;
    private _buildDashboardHtml;
    private _escHtml;
    private _shortPath;
}
//# sourceMappingURL=repositoryDashboard.d.ts.map