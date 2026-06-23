/**
 * CodeLens provider — renders action links above every function and class
 * definition in the active file.
 *
 * Each lens triggers one of the registered extension commands with pre-filled
 * arguments derived from the current file's symbol index.
 */
import * as vscode from 'vscode';
export declare class RepoIntelligenceCodeLensProvider implements vscode.CodeLensProvider, vscode.Disposable {
    private readonly _onDidChangeCodeLenses;
    readonly onDidChangeCodeLenses: vscode.Event<void>;
    private readonly _configWatcher;
    constructor();
    dispose(): void;
    provideCodeLenses(document: vscode.TextDocument, token: vscode.CancellationToken): Promise<vscode.CodeLens[]>;
    resolveCodeLens(lens: vscode.CodeLens): vscode.CodeLens;
}
//# sourceMappingURL=codeLensProvider.d.ts.map