"use strict";
/**
 * Repository Dashboard panel.
 *
 * Full-width webview showing KPIs, architecture health, API surface stats,
 * git churn hotspots, and recent analysis. All data is fetched from the
 * existing backend APIs — no analysis logic here.
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.RepositoryDashboardPanel = void 0;
const vscode = __importStar(require("vscode"));
const api_1 = require("../api");
const webview_1 = require("../utils/webview");
class RepositoryDashboardPanel {
    static createOrShow(extensionUri, owner, repo, client) {
        const key = `${owner}/${repo}`;
        const existing = RepositoryDashboardPanel._panels.get(key);
        if (existing) {
            existing._panel.reveal(vscode.ViewColumn.One);
            return;
        }
        const panel = vscode.window.createWebviewPanel(RepositoryDashboardPanel.viewType, `Dashboard — ${key}`, vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true,
            localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
        });
        const instance = new RepositoryDashboardPanel(panel, owner, repo, client);
        RepositoryDashboardPanel._panels.set(key, instance);
        panel.onDidDispose(() => RepositoryDashboardPanel._panels.delete(key));
    }
    constructor(panel, owner, repo, client) {
        this._panel = panel;
        this._owner = owner;
        this._repo = repo;
        this._client = client;
        this._panel.webview.html = this._buildLoadingHtml();
        this._panel.webview.onDidReceiveMessage(this._handleMessage.bind(this));
        void this._loadData();
    }
    async _loadData() {
        try {
            const [analysis, apiSurfaceStats, churnHotspots] = await Promise.allSettled([
                this._client.getAnalysis(this._owner, this._repo),
                this._client.getAPISurfaceStats(this._owner, this._repo),
                this._client.getChurnHotspots(this._owner, this._repo, 10, 365),
            ]);
            this._panel.webview.html = this._buildDashboardHtml({
                analysis: analysis.status === 'fulfilled' ? analysis.value : null,
                apiSurfaceStats: apiSurfaceStats.status === 'fulfilled' ? apiSurfaceStats.value : null,
                churnHotspots: churnHotspots.status === 'fulfilled' ? churnHotspots.value.hotspots : [],
                errors: [
                    analysis.status === 'rejected' ? (0, api_1.extractErrorMessage)(analysis.reason) : null,
                    apiSurfaceStats.status === 'rejected'
                        ? (0, api_1.extractErrorMessage)(apiSurfaceStats.reason)
                        : null,
                ].filter((e) => e !== null),
            });
        }
        catch (err) {
            this._panel.webview.html = this._buildErrorHtml((0, api_1.extractErrorMessage)(err));
        }
    }
    _handleMessage(msg) {
        if (msg.type === 'refresh') {
            this._panel.webview.html = this._buildLoadingHtml();
            void this._loadData();
        }
        if (msg.type === 'openDependencyGraph') {
            void vscode.commands.executeCommand('repoIntelligence.showDependencyGraph');
        }
        if (msg.type === 'openCallGraph') {
            void vscode.commands.executeCommand('repoIntelligence.showCallGraph');
        }
        if (msg.type === 'openChat') {
            void vscode.commands.executeCommand('repoIntelligence.showRepositoryChat');
        }
    }
    // ── HTML builders ────────────────────────────────────────────────────
    _buildLoadingHtml() {
        const nonce = (0, webview_1.getNonce)();
        return /* html */ `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
<style>${webview_1.BASE_CSS}
  .spinner {
    width: 32px; height: 32px;
    border: 3px solid var(--border);
    border-top-color: var(--link);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: auto;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .center { display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:12px;color:var(--muted); }
</style>
</head><body>
  <div class="center">
    <div class="spinner"></div>
    <span>Loading dashboard for ${this._owner}/${this._repo}…</span>
  </div>
</body></html>`;
    }
    _buildErrorHtml(error) {
        const nonce = (0, webview_1.getNonce)();
        return /* html */ `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
<style>${webview_1.BASE_CSS}</style>
</head><body style="padding:20px">
  <div class="error-banner">⚠ ${this._escHtml(error)}</div>
  <p style="color:var(--muted);margin-top:8px;font-size:12px">
    Make sure the backend is running and the repository has been analyzed.
  </p>
</body></html>`;
    }
    _buildDashboardHtml(data) {
        const nonce = (0, webview_1.getNonce)();
        const { analysis, apiSurfaceStats, churnHotspots, errors } = data;
        const repoId = `${this._owner}/${this._repo}`;
        const techStack = analysis?.analysis.tech_stack ?? [];
        const deps = analysis?.analysis.dependencies ?? [];
        const archSummary = analysis?.architecture?.summary ?? '';
        const totalSymbols = apiSurfaceStats?.total_symbols ?? '—';
        const publicSymbols = apiSurfaceStats?.public_count ?? '—';
        const deprecatedSymbols = apiSurfaceStats?.deprecated_count ?? '—';
        const orphanSymbols = apiSurfaceStats?.orphan_public_count ?? '—';
        const errorBanners = errors
            .map((e) => `<div class="error-banner">⚠ ${this._escHtml(e)}</div>`)
            .join('');
        const hotspotRows = churnHotspots
            .slice(0, 10)
            .map((h) => `<tr>
            <td title="${this._escHtml(h.file_path)}">${this._escHtml(this._shortPath(h.file_path))}</td>
            <td>${h.commit_count}</td>
            <td>${typeof h.churn_score === 'number' ? h.churn_score.toFixed(1) : '—'}</td>
          </tr>`)
            .join('');
        return /* html */ `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
<title>Dashboard — ${this._escHtml(repoId)}</title>
<style>
${webview_1.BASE_CSS}
body { overflow-y: auto; }
#header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
#header h1 { font-size: 15px; font-weight: 700; }
#actions { display: flex; gap: 8px; }
#content { padding: 0; }
.tech-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.tech-tag {
  background: var(--badge-bg);
  color: var(--badge-fg);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
}
.hotspot-table { font-size: 12px; }
</style>
</head>
<body>
  <div id="header">
    <h1>📊 ${this._escHtml(repoId)}</h1>
    <div id="actions">
      <button onclick="sendMsg('openDependencyGraph')">Dep Graph</button>
      <button onclick="sendMsg('openCallGraph')">Call Graph</button>
      <button onclick="sendMsg('openChat')">Chat</button>
      <button onclick="sendMsg('refresh')" title="Reload dashboard">↻</button>
    </div>
  </div>

  <div id="content">
    ${errorBanners}

    <div class="section">
      <div class="section-title">Repository KPIs</div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-value">${totalSymbols}</div>
          <div class="kpi-label">Total Symbols</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${publicSymbols}</div>
          <div class="kpi-label">Public API</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${deprecatedSymbols}</div>
          <div class="kpi-label">Deprecated</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${orphanSymbols}</div>
          <div class="kpi-label">Orphan Public</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${deps.length}</div>
          <div class="kpi-label">Dependencies</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${churnHotspots.length}</div>
          <div class="kpi-label">Churn Hotspots</div>
        </div>
      </div>
    </div>

    ${techStack.length > 0 ? /* html */ `
    <div class="section">
      <div class="section-title">Tech Stack</div>
      <div class="tech-tags">
        ${techStack.map((t) => `<span class="tech-tag">${this._escHtml(t)}</span>`).join('')}
      </div>
    </div>` : ''}

    ${archSummary ? /* html */ `
    <div class="section">
      <div class="section-title">Architecture Summary</div>
      <p style="font-size:12px;color:var(--fg);line-height:1.6">${this._escHtml(archSummary)}</p>
    </div>` : ''}

    ${churnHotspots.length > 0 ? /* html */ `
    <div class="section">
      <div class="section-title">Top Git Churn Hotspots</div>
      <table class="hotspot-table">
        <thead><tr><th>File</th><th>Commits</th><th>Churn Score</th></tr></thead>
        <tbody>${hotspotRows}</tbody>
      </table>
    </div>` : ''}

    ${apiSurfaceStats ? /* html */ `
    <div class="section">
      <div class="section-title">API Surface Breakdown</div>
      <table>
        <thead><tr><th>Visibility</th><th>Count</th></tr></thead>
        <tbody>
          <tr><td>Public</td><td>${apiSurfaceStats.public_count}</td></tr>
          <tr><td>Internal</td><td>${apiSurfaceStats.internal_count}</td></tr>
          <tr><td>Private</td><td>${apiSurfaceStats.private_count}</td></tr>
          <tr><td>Deprecated</td><td>${apiSurfaceStats.deprecated_count}</td></tr>
          <tr><td>Experimental</td><td>${apiSurfaceStats.experimental_count}</td></tr>
          <tr><td>HTTP Routes</td><td>${apiSurfaceStats.route_count}</td></tr>
          <tr><td>Orphan Public</td><td>${apiSurfaceStats.orphan_public_count}</td></tr>
        </tbody>
      </table>
    </div>` : ''}
  </div>

  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    function sendMsg(type) { vscode.postMessage({ type }); }
  </script>
</body></html>`;
    }
    _escHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
    _shortPath(p) {
        const parts = p.split(/[/\\]/);
        return parts.length > 3 ? `…/${parts.slice(-2).join('/')}` : p;
    }
}
exports.RepositoryDashboardPanel = RepositoryDashboardPanel;
RepositoryDashboardPanel.viewType = 'repoIntelligenceDashboard';
RepositoryDashboardPanel._panels = new Map();
//# sourceMappingURL=repositoryDashboard.js.map