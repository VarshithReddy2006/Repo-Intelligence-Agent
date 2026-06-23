/**
 * Architecture Health & API Surface panel.
 *
 * Shows architecture summary, component relationships, API surface stats,
 * deprecated symbols, and orphan public APIs from the backend.
 */

import * as vscode from 'vscode';
import { RepoIntelligenceClient, extractErrorMessage } from '../api';
import { getNonce, BASE_CSS } from '../utils/webview';

export class ArchitectureHealthPanel {
  static readonly viewType = 'repoIntelligenceArchHealth';
  private static _panels = new Map<string, ArchitectureHealthPanel>();

  private readonly _panel: vscode.WebviewPanel;
  private readonly _owner: string;
  private readonly _repo: string;
  private readonly _client: RepoIntelligenceClient;

  static createOrShow(
    extensionUri: vscode.Uri,
    owner: string,
    repo: string,
    client: RepoIntelligenceClient
  ): void {
    const key = `${owner}/${repo}`;
    const existing = ArchitectureHealthPanel._panels.get(key);
    if (existing) {
      existing._panel.reveal(vscode.ViewColumn.One);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      ArchitectureHealthPanel.viewType,
      `Architecture — ${key}`,
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
      }
    );

    const instance = new ArchitectureHealthPanel(panel, owner, repo, client);
    ArchitectureHealthPanel._panels.set(key, instance);
    panel.onDidDispose(() => ArchitectureHealthPanel._panels.delete(key));
  }

  private constructor(
    panel: vscode.WebviewPanel,
    owner: string,
    repo: string,
    client: RepoIntelligenceClient
  ) {
    this._panel = panel;
    this._owner = owner;
    this._repo = repo;
    this._client = client;

    this._panel.webview.html = this._buildLoadingHtml();
    this._panel.webview.onDidReceiveMessage(this._handleMessage.bind(this));
    void this._loadData();
  }

  private async _loadData(): Promise<void> {
    const [summaryResult, surfaceResult, publicResult, deprecatedResult] =
      await Promise.allSettled([
        this._client.getArchitectureSummary(this._owner, this._repo),
        this._client.getAPISurfaceStats(this._owner, this._repo),
        this._client.getPublicAPI(this._owner, this._repo),
        this._client.fetchJson<{ symbols: Array<Record<string, unknown>>; count: number }>(
          `/api/api-surface/${this._owner}/${this._repo}/deprecated`
        ),
      ]);

    const summary =
      summaryResult.status === 'fulfilled' ? summaryResult.value : null;
    const surfaceStats =
      surfaceResult.status === 'fulfilled' ? surfaceResult.value : null;
    const publicSymbolsRaw =
      publicResult.status === 'fulfilled' ? publicResult.value.symbols : [];
    const publicSymbols: Array<Record<string, unknown>> = publicSymbolsRaw.map((s) => s as unknown as Record<string, unknown>);
    const deprecatedSymbols =
      deprecatedResult.status === 'fulfilled' ? deprecatedResult.value.symbols : [];

    const errors: string[] = [
      summaryResult.status === 'rejected'
        ? extractErrorMessage(summaryResult.reason)
        : null,
      surfaceResult.status === 'rejected'
        ? extractErrorMessage(surfaceResult.reason)
        : null,
    ].filter((e): e is string => e !== null);

    this._panel.webview.html = this._buildHtml({
      summary,
      surfaceStats,
      publicSymbols,
      deprecatedSymbols,
      errors,
    });
  }

  private _handleMessage(msg: { type: string }): void {
    if (msg.type === 'refresh') {
      this._panel.webview.html = this._buildLoadingHtml();
      void this._loadData();
    }
  }

  private _buildLoadingHtml(): string {
    return /* html */ `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
<style>${BASE_CSS}
.center{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:12px;color:var(--muted);}
.spinner{width:28px;height:28px;border:3px solid var(--border);border-top-color:var(--link);border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
</style></head>
<body><div class="center"><div class="spinner"></div><span>Loading architecture health…</span></div></body></html>`;
  }

  private _buildHtml(data: {
    summary: { summary: string; reading_order: string[]; relationships: Array<{ source: string; target: string; relationship_type: string; description: string }> } | null;
    surfaceStats: ReturnType<typeof Object.create> | null;
    publicSymbols: Array<Record<string, unknown>>;
    deprecatedSymbols: Array<Record<string, unknown>>;
    errors: string[];
  }): string {
    const nonce = getNonce();
    const csp = `default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;
    const repoId = `${this._owner}/${this._repo}`;

    const errorBanners = data.errors
      .map((e) => `<div class="error-banner">⚠ ${this._esc(e)}</div>`)
      .join('');

    const statsRows = data.surfaceStats
      ? [
          ['Total Symbols', data.surfaceStats.total_symbols],
          ['Public', data.surfaceStats.public_count],
          ['Internal', data.surfaceStats.internal_count],
          ['Deprecated', data.surfaceStats.deprecated_count],
          ['Orphan Public', data.surfaceStats.orphan_public_count],
          ['HTTP Routes', data.surfaceStats.route_count],
        ]
          .map(
            ([k, v]) =>
              `<tr><td>${k}</td><td><strong>${v}</strong></td></tr>`
          )
          .join('')
      : '';

    const relRows = (data.summary?.relationships ?? [])
      .slice(0, 40)
      .map(
        (r) =>
          `<tr>
            <td>${this._esc(r.source)}</td>
            <td><span class="badge">${this._esc(r.relationship_type)}</span></td>
            <td>${this._esc(r.target)}</td>
          </tr>`
      )
      .join('');

    const depRows = data.deprecatedSymbols
      .slice(0, 30)
      .map(
        (s) =>
          `<tr>
            <td>${this._esc(String(s.name ?? ''))}</td>
            <td>${this._esc(String(s.file_path ?? ''))}</td>
            <td><span class="badge">${this._esc(String(s.api_kind ?? ''))}</span></td>
          </tr>`
      )
      .join('');

    const publicRows = data.publicSymbols
      .filter((s) => s.is_orphan)
      .slice(0, 20)
      .map(
        (s) =>
          `<tr>
            <td>${this._esc(String(s.name ?? ''))}</td>
            <td>${this._esc(String(s.file_path ?? ''))}</td>
            <td><span class="badge">${this._esc(String(s.visibility ?? ''))}</span></td>
          </tr>`
      )
      .join('');

    return /* html */ `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<title>Architecture — ${this._esc(repoId)}</title>
<style>
${BASE_CSS}
body { overflow-y: auto; }
#header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
#header h1 { font-size: 15px; font-weight: 700; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
@media (max-width: 600px) { .two-col { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div id="header">
  <h1>🏗 Architecture Health — ${this._esc(repoId)}</h1>
  <button onclick="vscode.postMessage({type:'refresh'})">↻ Refresh</button>
</div>

${errorBanners}

${data.summary?.summary ? `
<div class="section">
  <div class="section-title">Architecture Summary</div>
  <p style="font-size:12px;line-height:1.6;color:var(--fg)">${this._esc(data.summary.summary)}</p>
</div>` : ''}

<div class="two-col">
  ${data.surfaceStats ? `
  <div class="section" style="border-right:1px solid var(--border)">
    <div class="section-title">API Surface Stats</div>
    <table><tbody>${statsRows}</tbody></table>
  </div>` : ''}

  ${data.summary?.reading_order?.length ? `
  <div class="section">
    <div class="section-title">Reading Order (top 10)</div>
    <ol style="font-size:11px;padding-left:18px;line-height:1.8">
      ${data.summary.reading_order
        .slice(0, 10)
        .map((f) => `<li>${this._esc(f)}</li>`)
        .join('')}
    </ol>
  </div>` : ''}
</div>

${relRows ? `
<div class="section">
  <div class="section-title">Component Relationships</div>
  <table>
    <thead><tr><th>Source</th><th>Type</th><th>Target</th></tr></thead>
    <tbody>${relRows}</tbody>
  </table>
</div>` : ''}

${depRows ? `
<div class="section">
  <div class="section-title">Deprecated Symbols (${data.deprecatedSymbols.length})</div>
  <table>
    <thead><tr><th>Symbol</th><th>File</th><th>Kind</th></tr></thead>
    <tbody>${depRows}</tbody>
  </table>
</div>` : ''}

${publicRows ? `
<div class="section">
  <div class="section-title">Orphan Public Symbols (unused public API)</div>
  <table>
    <thead><tr><th>Symbol</th><th>File</th><th>Visibility</th></tr></thead>
    <tbody>${publicRows}</tbody>
  </table>
</div>` : ''}

<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
</script>
</body></html>`;
  }

  private _esc(s: string): string {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
