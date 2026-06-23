/**
 * Hover provider — shows symbol intelligence cards when the developer hovers
 * over a function or class name.
 *
 * Data is fetched from the backend symbol index and call graph.
 * Results are cached per file to avoid hammering the backend on every mouseover.
 */
import * as vscode from 'vscode';
export declare class RepoIntelligenceHoverProvider implements vscode.HoverProvider {
    provideHover(document: vscode.TextDocument, position: vscode.Position, _token: vscode.CancellationToken): Promise<vscode.Hover | null>;
}
//# sourceMappingURL=hoverProvider.d.ts.map