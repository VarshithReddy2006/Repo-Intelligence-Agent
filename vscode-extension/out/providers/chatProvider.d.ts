/**
 * Repository Chat — embedded webview panel.
 *
 * Streams responses from POST /api/chat using the same SSE pipeline as the
 * frontend. No AI logic is implemented here — this is a pure client.
 */
import * as vscode from 'vscode';
import { RepoIntelligenceClient } from '../api';
export declare class ChatProvider {
    private static _panels;
    private readonly _panel;
    private readonly _repo;
    private readonly _client;
    private readonly _history;
    private _cancelStream?;
    static createOrShow(context: vscode.ExtensionContext, repo: string, client: RepoIntelligenceClient): void;
    private constructor();
    private _handleMessage;
    private _sendMessage;
    private _buildHtml;
}
//# sourceMappingURL=chatProvider.d.ts.map