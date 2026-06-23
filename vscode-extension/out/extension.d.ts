/**
 * Extension entry point — activate and deactivate lifecycle hooks.
 *
 * Responsibilities:
 *  - Register all commands
 *  - Register language providers (hover, CodeLens)
 *  - Register tree-view data providers
 *  - Check backend health on activation
 *
 * No analysis logic lives here. Every feature delegates to a dedicated
 * provider, panel, or API client module.
 */
import * as vscode from 'vscode';
export declare function activate(context: vscode.ExtensionContext): void;
export declare function deactivate(): void;
//# sourceMappingURL=extension.d.ts.map