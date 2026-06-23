/**
 * CodeLens provider — renders action links above every function and class
 * definition in the active file.
 *
 * Each lens triggers one of the registered extension commands with pre-filled
 * arguments derived from the current file's symbol index.
 */

import * as vscode from 'vscode';
import { client, Symbol as RepoSymbol } from '../api';

// Simple LRU cache: one entry per open document
const symbolCache = new Map<string, { symbols: RepoSymbol[]; version: number }>();

function getActiveRepo(): string {
  return (
    vscode.workspace.getConfiguration('repoIntelligence').get<string>('activeRepository') ?? ''
  );
}

function repoToOwnerRepo(id: string): [string, string] | null {
  const p = id.split('/');
  return p.length === 2 && p[0] && p[1] ? [p[0], p[1]] : null;
}

function getRelativePath(document: vscode.TextDocument): string {
  const ws = vscode.workspace.getWorkspaceFolder(document.uri);
  return ws ? vscode.workspace.asRelativePath(document.uri, false) : document.uri.fsPath;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export class RepoIntelligenceCodeLensProvider
  implements vscode.CodeLensProvider, vscode.Disposable
{
  private readonly _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

  private readonly _configWatcher: vscode.Disposable;

  constructor() {
    this._configWatcher = vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('repoIntelligence')) {
        this._onDidChangeCodeLenses.fire();
      }
    });
  }

  dispose(): void {
    this._configWatcher.dispose();
    this._onDidChangeCodeLenses.dispose();
  }

  async provideCodeLenses(
    document: vscode.TextDocument,
    token: vscode.CancellationToken
  ): Promise<vscode.CodeLens[]> {
    if (!vscode.workspace.getConfiguration('repoIntelligence').get<boolean>('codeLens.enabled')) {
      return [];
    }

    const repoId = getActiveRepo();
    if (!repoId) {
      return [];
    }
    const ownerRepo = repoToOwnerRepo(repoId);
    if (!ownerRepo) {
      return [];
    }
    const [owner, repo] = ownerRepo;
    const filePath = getRelativePath(document);

    // Invalidate stale cache
    const cached = symbolCache.get(document.uri.toString());
    let symbols: RepoSymbol[];
    if (cached && cached.version === document.version) {
      symbols = cached.symbols;
    } else {
      try {
        const result = await client.getFileSymbols(owner, repo, filePath);
        symbols = result.symbols;
        symbolCache.set(document.uri.toString(), {
          symbols,
          version: document.version,
        });
      } catch {
        return [];
      }
    }

    if (token.isCancellationRequested) {
      return [];
    }

    const lenses: vscode.CodeLens[] = [];

    for (const symbol of symbols) {
      if (
        symbol.symbol_type !== 'function' &&
        symbol.symbol_type !== 'method' &&
        symbol.symbol_type !== 'class'
      ) {
        continue;
      }

      const lineIndex = Math.max(0, symbol.line_number - 1);
      const range = new vscode.Range(lineIndex, 0, lineIndex, 0);
      const functionId = encodeURIComponent(`${filePath}::${symbol.qualified}`);

      // ── Show Callers ───────────────────────────────────────────────────
      lenses.push(
        new vscode.CodeLens(range, {
          title: `$(arrow-left) Callers${typeof symbol.fan_in === 'number' ? ` (${symbol.fan_in})` : ''}`,
          command: 'repoIntelligence.showCallers',
          arguments: [{ owner, repo, functionId }],
          tooltip: 'Show all functions that call this one',
        })
      );

      // ── Show Callees ───────────────────────────────────────────────────
      lenses.push(
        new vscode.CodeLens(range, {
          title: `$(arrow-right) Callees${typeof symbol.fan_out === 'number' ? ` (${symbol.fan_out})` : ''}`,
          command: 'repoIntelligence.showCallees',
          arguments: [{ owner, repo, functionId }],
          tooltip: 'Show all functions called by this one',
        })
      );

      // ── Blast Radius (functions and methods only) ──────────────────────
      if (symbol.symbol_type !== 'class') {
        lenses.push(
          new vscode.CodeLens(range, {
            title: '$(pulse) Blast Radius',
            command: 'repoIntelligence.showBlastRadius',
            arguments: [{ owner, repo, functionId }],
            tooltip: 'Compute the change impact radius of this function',
          })
        );
      }

      // ── Impact Analysis (classes only, or any symbol) ──────────────────
      lenses.push(
        new vscode.CodeLens(range, {
          title: '$(beaker) Impact Analysis',
          command: 'repoIntelligence.showImpactAnalysis',
          arguments: [
            {
              repo: `${owner}/${repo}`,
              issue: `Change to ${symbol.qualified}`,
            },
          ],
          tooltip: 'Predict impact of modifying this symbol',
        })
      );

      // ── Reading Path ──────────────────────────────────────────────────
      lenses.push(
        new vscode.CodeLens(range, {
          title: '$(book) Reading Path',
          command: 'repoIntelligence.showReadingPathForFile',
          arguments: [{ file: filePath }],
          tooltip: 'Generate recommended reading order from this file',
        })
      );
    }

    return lenses;
  }

  resolveCodeLens(lens: vscode.CodeLens): vscode.CodeLens {
    return lens;
  }
}
