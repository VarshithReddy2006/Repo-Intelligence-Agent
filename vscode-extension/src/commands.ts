/**
 * Command registrations for the Repo Intelligence Agent extension.
 *
 * Each command is a thin orchestrator that delegates to the appropriate
 * panel, provider, or API client. No business logic here.
 */

import * as vscode from 'vscode';
import { client, extractErrorMessage } from './api';
import { RepositoryDashboardPanel } from './panels/repositoryDashboard';
import { DependencyGraphPanel } from './panels/dependencyGraphPanel';
import { CallGraphPanel } from './panels/callGraphPanel';
import { ArchitectureHealthPanel } from './panels/architectureHealthPanel';
import { ChatProvider } from './providers/chatProvider';
import { RepositoryExplorerProvider } from './providers/treeViewProvider';

// ---------------------------------------------------------------------------
// Repository picker helper
// ---------------------------------------------------------------------------

async function pickOrGetActiveRepo(prompt?: string): Promise<string | undefined> {
  const cfg = vscode.workspace.getConfiguration('repoIntelligence');
  const active = cfg.get<string>('activeRepository') ?? '';
  if (active) {
    return active;
  }

  // Try to load from recent repos
  let recentNames: string[] = [];
  try {
    const repos = await client.getRecentRepos();
    recentNames = repos.map((r) => r.name);
  } catch {
    // backend may be offline — fall through to manual input
  }

  if (recentNames.length > 0) {
    const picked = await vscode.window.showQuickPick(
      ['$(edit) Enter manually...', ...recentNames],
      { placeHolder: prompt ?? 'Select a repository' }
    );
    if (!picked) {
      return undefined;
    }
    if (picked === '$(edit) Enter manually...') {
      return vscode.window.showInputBox({
        prompt: 'Enter repository identifier (owner/repo)',
        placeHolder: 'e.g. fastapi/fastapi',
      });
    }
    return picked;
  }

  return vscode.window.showInputBox({
    prompt: prompt ?? 'Enter repository identifier (owner/repo)',
    placeHolder: 'e.g. fastapi/fastapi',
  });
}

/**
 * Split "owner/repo" into [owner, repo].
 * Throws if the format is invalid.
 */
function splitRepo(identifier: string): [string, string] {
  const parts = identifier.split('/');
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new Error(`Invalid repository identifier "${identifier}". Expected "owner/repo".`);
  }
  return [parts[0], parts[1]];
}

// ---------------------------------------------------------------------------
// Main registration function
// ---------------------------------------------------------------------------

export function registerCommands(
  context: vscode.ExtensionContext,
  explorerProvider: RepositoryExplorerProvider
): void {

  // ── Connect to backend ──────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.connectBackend', async () => {
      const url = await vscode.window.showInputBox({
        prompt: 'Backend URL',
        value: vscode.workspace.getConfiguration('repoIntelligence').get<string>('backendUrl'),
        placeHolder: 'http://127.0.0.1:8001',
      });
      if (!url) {
        return;
      }
      await vscode.workspace
        .getConfiguration('repoIntelligence')
        .update('backendUrl', url, vscode.ConfigurationTarget.Global);

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: 'Checking backend health…' },
        async () => {
          try {
            const health = await client.health();
            void vscode.window.showInformationMessage(
              `Connected — backend ${health.status}, model: ${health.llm_model}`
            );
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Backend unreachable: ${extractErrorMessage(err)}`
            );
          }
        }
      );
    })
  );

  // ── Set active repository ───────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.setActiveRepository', async () => {
      let recentNames: string[] = [];
      try {
        const repos = await client.getRecentRepos();
        recentNames = repos.map((r) => r.name);
      } catch {
        // backend offline
      }

      let identifier: string | undefined;
      if (recentNames.length > 0) {
        const picked = await vscode.window.showQuickPick(
          ['$(edit) Enter manually...', ...recentNames],
          { placeHolder: 'Select the active repository' }
        );
        if (!picked) {
          return;
        }
        identifier =
          picked === '$(edit) Enter manually...'
            ? await vscode.window.showInputBox({
                prompt: 'Enter repository identifier (owner/repo)',
                placeHolder: 'e.g. fastapi/fastapi',
              })
            : picked;
      } else {
        identifier = await vscode.window.showInputBox({
          prompt: 'Enter repository identifier (owner/repo)',
          placeHolder: 'e.g. fastapi/fastapi',
        });
      }

      if (!identifier) {
        return;
      }
      await vscode.workspace
        .getConfiguration('repoIntelligence')
        .update('activeRepository', identifier, vscode.ConfigurationTarget.Workspace);
      explorerProvider.refresh();
      void vscode.window.showInformationMessage(
        `Active repository set to "${identifier}"`
      );
    })
  );

  // ── Analyze repository ──────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.analyzeRepository', async () => {
      const repoUrl = await vscode.window.showInputBox({
        prompt: 'GitHub repository URL to analyze',
        placeHolder: 'https://github.com/owner/repo',
      });
      if (!repoUrl) {
        return;
      }

      const panel = vscode.window.createOutputChannel('Repo Intelligence — Analysis');
      panel.show();
      panel.appendLine(`Starting analysis for: ${repoUrl}`);

      const cancel = client.streamSse(
        '/api/analyze',
        { url: repoUrl, branch: 'main' },
        (event) => {
          const msg = typeof event.message === 'string' ? event.message : JSON.stringify(event);
          panel.appendLine(msg);
          if (event.status === 'done' && typeof event.repo === 'string') {
            void vscode.workspace
              .getConfiguration('repoIntelligence')
              .update('activeRepository', event.repo as string, vscode.ConfigurationTarget.Workspace);
            explorerProvider.refresh();
            void vscode.window.showInformationMessage(
              `Analysis complete for ${event.repo as string}`
            );
          }
          if (event.status === 'error') {
            void vscode.window.showErrorMessage(
              `Analysis error: ${String(event.message ?? 'Unknown error')}`
            );
          }
        },
        () => panel.appendLine('Stream closed.'),
        (err) => {
          panel.appendLine(`Error: ${err.message}`);
          void vscode.window.showErrorMessage(`Analysis failed: ${err.message}`);
        }
      );

      context.subscriptions.push({ dispose: () => cancel?.() });
    })
  );

  // ── Refresh analysis ────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.refreshAnalysis', () => {
      explorerProvider.refresh();
      void vscode.window.showInformationMessage('Repository explorer refreshed.');
    })
  );

  // ── Open Dashboard ──────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.openDashboard', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for the dashboard');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        RepositoryDashboardPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show Dependency Graph ───────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showDependencyGraph', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for the dependency graph');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        DependencyGraphPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show Call Graph ────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showCallGraph', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for the call graph');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        CallGraphPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show Architecture Health ───────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showArchitectureHealth', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for architecture health');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        ArchitectureHealthPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show Module Stability (re-uses dashboard) ──────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showModuleStability', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        RepositoryDashboardPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show API Surface ───────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showAPISurface', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for API surface');
      if (!repo) {
        return;
      }
      try {
        const [owner, repoName] = splitRepo(repo);
        ArchitectureHealthPanel.createOrShow(context.extensionUri, owner, repoName, client);
      } catch (err) {
        void vscode.window.showErrorMessage(extractErrorMessage(err));
      }
    })
  );

  // ── Show Repository Chat ───────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showRepositoryChat', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository to chat about');
      if (!repo) {
        return;
      }
      ChatProvider.createOrShow(context, repo, client);
    })
  );

  // ── Show Reading Path ──────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand('repoIntelligence.showReadingPath', async () => {
      const repo = await pickOrGetActiveRepo('Select a repository for reading path');
      if (!repo) {
        return;
      }
      await withProgress('Generating reading path…', async () => {
        try {
          const order = await client.getReadingOrder(repo);
          const panel = vscode.window.createOutputChannel('Repo Intelligence — Reading Path');
          panel.show();
          panel.appendLine(`Reading Path for ${repo}`);
          panel.appendLine('='.repeat(60));
          const entries: Array<{ file: string; score: number; reason: string }> =
            Array.isArray((order as { entries?: unknown }).entries)
              ? ((order as { entries: Array<{ file: string; score: number; reason: string }> }).entries)
              : [];
          entries.forEach((e, i) => {
            panel.appendLine(`\n${i + 1}. ${e.file}`);
            if (e.reason) {
              panel.appendLine(`   ${e.reason}`);
            }
          });
        } catch (err) {
          void vscode.window.showErrorMessage(
            `Reading path failed: ${extractErrorMessage(err)}`
          );
        }
      });
    })
  );

  // ── Show Reading Path for current file ────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'repoIntelligence.showReadingPathForFile',
      async (args?: { file?: string }) => {
        const repo = await pickOrGetActiveRepo('Select a repository');
        if (!repo) {
          return;
        }
        const filePath =
          args?.file ?? vscode.window.activeTextEditor?.document.uri.fsPath ?? '';

        await withProgress('Generating reading path…', async () => {
          try {
            const order = await client.getReadingOrder(repo);
            const panel = vscode.window.createOutputChannel(
              'Repo Intelligence — Reading Path'
            );
            panel.show();
            panel.appendLine(`Reading Path for ${repo} (starting from ${filePath})`);
            panel.appendLine('='.repeat(60));
            const entries: Array<{ file: string; score: number; reason: string }> =
              Array.isArray((order as { entries?: unknown }).entries)
                ? ((order as { entries: Array<{ file: string; score: number; reason: string }> }).entries)
                : [];
            entries.forEach((e, i) => {
              panel.appendLine(`\n${i + 1}. ${e.file}`);
            });
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Reading path failed: ${extractErrorMessage(err)}`
            );
          }
        });
      }
    )
  );

  // ── Show Callers (invoked by CodeLens) ─────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'repoIntelligence.showCallers',
      async (args: { owner: string; repo: string; functionId: string }) => {
        await withProgress('Fetching callers…', async () => {
          try {
            const result = await client.getCallers(args.owner, args.repo, args.functionId);
            const items = result.callers.map(
              (c) => `$(go-to-file) ${c.qualified} — ${c.file_path}:${c.line_number}`
            );
            if (items.length === 0) {
              void vscode.window.showInformationMessage(
                'No callers found for this function.'
              );
              return;
            }
            const picked = await vscode.window.showQuickPick(
              result.callers.map((c) => ({
                label: c.qualified,
                description: `${c.file_path}:${c.line_number}`,
                caller: c,
              })),
              { placeHolder: `Callers of ${args.functionId}` }
            );
            if (picked?.caller) {
              const uri = vscode.Uri.file(picked.caller.file_path);
              const doc = await vscode.workspace.openTextDocument(uri).then(
                (d) => d,
                () => undefined
              );
              if (doc) {
                await vscode.window.showTextDocument(doc, {
                  selection: new vscode.Range(
                    Math.max(0, picked.caller.line_number - 1),
                    0,
                    Math.max(0, picked.caller.line_number - 1),
                    0
                  ),
                });
              }
            }
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Callers lookup failed: ${extractErrorMessage(err)}`
            );
          }
        });
      }
    )
  );

  // ── Show Callees (invoked by CodeLens) ────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'repoIntelligence.showCallees',
      async (args: { owner: string; repo: string; functionId: string }) => {
        await withProgress('Fetching callees…', async () => {
          try {
            const result = await client.getCallees(args.owner, args.repo, args.functionId);
            if (result.callees.length === 0) {
              void vscode.window.showInformationMessage(
                'No callees found for this function.'
              );
              return;
            }
            await vscode.window.showQuickPick(
              result.callees.map((c) => ({
                label: c.qualified,
                description: `${c.file_path}:${c.line_number}`,
              })),
              { placeHolder: `Callees of ${args.functionId}` }
            );
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Callees lookup failed: ${extractErrorMessage(err)}`
            );
          }
        });
      }
    )
  );

  // ── Show Blast Radius (invoked by CodeLens) ───────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'repoIntelligence.showBlastRadius',
      async (args: { owner: string; repo: string; functionId: string }) => {
        await withProgress('Computing blast radius…', async () => {
          try {
            const result = await client.getBlastRadius(args.owner, args.repo, args.functionId);
            const lines = [
              `Blast Radius for: ${args.functionId}`,
              `Risk Level: ${result.risk_level.toUpperCase()}`,
              `Affected Functions: ${result.affected_functions.length}`,
              `Affected Files: ${result.affected_files.length}`,
              `Max Propagation Depth: ${result.depth}`,
              '',
              'Affected Files:',
              ...result.affected_files.map((f) => `  • ${f}`),
            ];
            const panel = vscode.window.createOutputChannel(
              'Repo Intelligence — Blast Radius'
            );
            panel.show();
            panel.appendLine(lines.join('\n'));
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Blast radius failed: ${extractErrorMessage(err)}`
            );
          }
        });
      }
    )
  );

  // ── Show Impact Analysis (invoked by CodeLens) ────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand(
      'repoIntelligence.showImpactAnalysis',
      async (args?: { repo?: string; issue?: string }) => {
        const repo = args?.repo ?? (await pickOrGetActiveRepo('Select a repository'));
        if (!repo) {
          return;
        }
        const issue =
          args?.issue ??
          (await vscode.window.showInputBox({
            prompt: 'Describe the change you are planning',
            placeHolder: 'e.g. Refactor authentication module',
          }));
        if (!issue) {
          return;
        }

        await withProgress('Analyzing impact…', async () => {
          try {
            const result = await client.getImpactAnalysis(repo, issue);
            const panel = vscode.window.createOutputChannel(
              'Repo Intelligence — Impact Analysis'
            );
            panel.show();
            panel.appendLine(`Impact Analysis: "${issue}"`);
            panel.appendLine(`Risk Level: ${String(result.risk_level ?? 'N/A')}`);
            panel.appendLine(
              `Affected Files (${result.affected_files?.length ?? 0}):`
            );
            (result.affected_files ?? []).forEach((f) =>
              panel.appendLine(`  • ${f}`)
            );
          } catch (err) {
            void vscode.window.showErrorMessage(
              `Impact analysis failed: ${extractErrorMessage(err)}`
            );
          }
        });
      }
    )
  );
}

// ---------------------------------------------------------------------------
// Tiny progress helper
// ---------------------------------------------------------------------------

async function withProgress<T>(title: string, task: () => Promise<T>): Promise<T> {
  return vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title },
    () => task()
  ) as Promise<T>;
}
