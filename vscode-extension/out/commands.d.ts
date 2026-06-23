/**
 * Command registrations for the Repo Intelligence Agent extension.
 *
 * Each command is a thin orchestrator that delegates to the appropriate
 * panel, provider, or API client. No business logic here.
 */
import * as vscode from 'vscode';
import { RepositoryExplorerProvider } from './providers/treeViewProvider';
export declare function registerCommands(context: vscode.ExtensionContext, explorerProvider: RepositoryExplorerProvider): void;
//# sourceMappingURL=commands.d.ts.map