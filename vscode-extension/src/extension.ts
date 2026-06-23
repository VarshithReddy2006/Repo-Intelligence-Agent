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
import { registerCommands } from './commands';
import { RepoIntelligenceHoverProvider } from './providers/hoverProvider';
import { RepoIntelligenceCodeLensProvider } from './providers/codeLensProvider';
import { RepositoryExplorerProvider } from './providers/treeViewProvider';
import { client, extractErrorMessage } from './api';

// Status bar item shared across the extension
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext): void {
  // ── Status bar ─────────────────────────────────────────────────────────
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  statusBarItem.command = 'repoIntelligence.openDashboard';
  statusBarItem.text = '$(repo) Repo Intelligence';
  statusBarItem.tooltip = 'Open Repo Intelligence Dashboard';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // ── Language providers ─────────────────────────────────────────────────
  const cfg = vscode.workspace.getConfiguration('repoIntelligence');

  if (cfg.get<boolean>('hover.enabled') !== false) {
    const hoverProvider = new RepoIntelligenceHoverProvider();
    context.subscriptions.push(
      vscode.languages.registerHoverProvider(
        [
          { language: 'python' },
          { language: 'javascript' },
          { language: 'typescript' },
          { language: 'javascriptreact' },
          { language: 'typescriptreact' },
        ],
        hoverProvider
      )
    );
  }

  if (cfg.get<boolean>('codeLens.enabled') !== false) {
    const codeLensProvider = new RepoIntelligenceCodeLensProvider();
    context.subscriptions.push(
      vscode.languages.registerCodeLensProvider(
        [
          { language: 'python' },
          { language: 'javascript' },
          { language: 'typescript' },
          { language: 'javascriptreact' },
          { language: 'typescriptreact' },
        ],
        codeLensProvider
      )
    );
  }

  // ── Tree view ──────────────────────────────────────────────────────────
  const explorerProvider = new RepositoryExplorerProvider(context);
  const treeView = vscode.window.createTreeView('repoIntelligenceExplorer', {
    treeDataProvider: explorerProvider,
    showCollapseAll: true,
  });
  context.subscriptions.push(treeView);

  // Allow commands to refresh the tree
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.explorerRefresh', () => {
      explorerProvider.refresh();
    })
  );

  // ── All other commands ─────────────────────────────────────────────────
  registerCommands(context, explorerProvider);

  // ── Configuration changes ──────────────────────────────────────────────
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('repoIntelligence')) {
        explorerProvider.refresh();
      }
    })
  );

  // ── Auto-refresh on save ───────────────────────────────────────────────
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(() => {
      const autoCfg = vscode.workspace.getConfiguration('repoIntelligence');
      if (autoCfg.get<boolean>('autoRefresh')) {
        explorerProvider.refresh();
      }
    })
  );

  // ── Initial health probe ───────────────────────────────────────────────
  void checkBackendHealth(statusBarItem);
}

export function deactivate(): void {
  // Dispose is handled automatically via subscriptions
}

/**
 * Probe the backend on startup and update the status bar.
 * Never throws — failure just changes the status bar icon.
 */
async function checkBackendHealth(bar: vscode.StatusBarItem): Promise<void> {
  try {
    const health = await client.health();
    if (health.status === 'healthy') {
      bar.text = '$(check) Repo Intelligence';
      bar.tooltip = `Backend online — ${health.llm_model}`;
      bar.backgroundColor = undefined;
    } else {
      bar.text = '$(warning) Repo Intelligence';
      bar.tooltip = 'Backend reachable but reported unhealthy status.';
    }
  } catch (err) {
    bar.text = '$(circle-slash) Repo Intelligence';
    bar.tooltip = `Backend offline: ${extractErrorMessage(err)}. Click to open dashboard.`;
    bar.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
  }
}
