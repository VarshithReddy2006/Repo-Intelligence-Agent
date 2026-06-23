/**
 * Interactive Dependency Graph panel.
 *
 * Renders the React Flow compatible graph data returned by
 * GET /api/graph/{owner}/{repo}/full using a lightweight Canvas/SVG
 * implementation inside the webview (no React needed — just the raw data).
 *
 * Features: Pan, Zoom, Search, Highlight neighbors, Focus selected node.
 */

import * as vscode from 'vscode';
import { RepoIntelligenceClient, GraphData, extractErrorMessage } from '../api';
import { getNonce, BASE_CSS } from '../utils/webview';

export class DependencyGraphPanel {
  static readonly viewType = 'repoIntelligenceDepGraph';
  private static _panels = new Map<string, DependencyGraphPanel>();

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
    const existing = DependencyGraphPanel._panels.get(key);
    if (existing) {
      existing._panel.reveal(vscode.ViewColumn.One);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      DependencyGraphPanel.viewType,
      `Dep Graph — ${key}`,
      vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'out')],
      }
    );

    const instance = new DependencyGraphPanel(panel, owner, repo, client);
    DependencyGraphPanel._panels.set(key, instance);
    panel.onDidDispose(() => DependencyGraphPanel._panels.delete(key));
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

    this._panel.webview.html = this._buildHtml(null, null);
    this._panel.webview.onDidReceiveMessage(this._handleMessage.bind(this));
    void this._loadGraph();
  }

  private async _loadGraph(query?: string): Promise<void> {
    try {
      const graph = await this._client.getDependencyGraph(this._owner, this._repo, query);
      void this._panel.webview.postMessage({ type: 'graphData', data: graph });
    } catch (err) {
      void this._panel.webview.postMessage({
        type: 'error',
        message: extractErrorMessage(err),
      });
    }
  }

  private async _handleMessage(msg: {
    type: string;
    query?: string;
    nodeId?: string;
  }): Promise<void> {
    if (msg.type === 'search') {
      await this._loadSearch(msg.query ?? '');
    } else if (msg.type === 'focusNode' && msg.nodeId) {
      await this._loadNeighbors(msg.nodeId);
    } else if (msg.type === 'resetGraph') {
      await this._loadGraph();
    } else if (msg.type === 'traceNode' && msg.nodeId) {
      try {
        const trace = await this._client.getGraphTrace(
          this._owner,
          this._repo,
          msg.nodeId
        );
        void this._panel.webview.postMessage({ type: 'graphData', data: trace });
      } catch (err) {
        void this._panel.webview.postMessage({
          type: 'error',
          message: extractErrorMessage(err),
        });
      }
    }
  }

  private async _loadSearch(query: string): Promise<void> {
    try {
      // Use full graph with query filter
      const graph = await this._client.getDependencyGraph(this._owner, this._repo, query);
      void this._panel.webview.postMessage({ type: 'graphData', data: graph });
    } catch (err) {
      void this._panel.webview.postMessage({
        type: 'error',
        message: extractErrorMessage(err),
      });
    }
  }

  private async _loadNeighbors(nodeId: string): Promise<void> {
    try {
      const neighbors = await this._client.getGraphNeighbors(this._owner, this._repo, nodeId);
      void this._panel.webview.postMessage({ type: 'graphData', data: neighbors });
    } catch (err) {
      void this._panel.webview.postMessage({
        type: 'error',
        message: extractErrorMessage(err),
      });
    }
  }

  private _buildHtml(_graph: GraphData | null, _error: string | null): string {
    const nonce = getNonce();
    const csp = `default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';`;
    const repoId = `${this._owner}/${this._repo}`;

    return /* html */ `<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<title>Dependency Graph — ${repoId}</title>
<style>
${BASE_CSS}
body { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
#toolbar {
  padding: 6px 12px;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
  flex-wrap: wrap;
}
#toolbar h2 { font-size: 13px; font-weight: 600; flex: 1; }
#search {
  background: var(--input-bg);
  color: var(--input-fg);
  border: 1px solid var(--input-border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  width: 200px;
}
#graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  cursor: grab;
}
#graph-container:active { cursor: grabbing; }
#canvas { position: absolute; top: 0; left: 0; }
#tooltip {
  position: fixed;
  background: var(--vscode-editorWidget-background);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 11px;
  pointer-events: none;
  display: none;
  max-width: 300px;
  z-index: 1000;
}
#info-bar {
  padding: 4px 12px;
  border-top: 1px solid var(--border);
  font-size: 11px;
  color: var(--muted);
  flex-shrink: 0;
}
#loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  z-index: 10;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--link);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div id="toolbar">
  <h2>🔗 Dependency Graph — ${repoId}</h2>
  <input id="search" type="text" placeholder="Search nodes…">
  <button onclick="resetGraph()">Reset</button>
  <button onclick="zoomIn()">+</button>
  <button onclick="zoomOut()">−</button>
  <button onclick="fitView()">Fit</button>
</div>
<div id="graph-container">
  <div id="loading-overlay"><div class="spinner"></div></div>
  <canvas id="canvas"></canvas>
</div>
<div id="tooltip"></div>
<div id="info-bar" id="info">Loading graph…</div>

<script nonce="${nonce}">
const vscode = acquireVsCodeApi();

// ── State ───────────────────────────────────────────────────────────────
let nodes = [], edges = [];
let scale = 1, offsetX = 0, offsetY = 0;
let dragging = false, lastMouse = { x: 0, y: 0 };
let hoveredNode = null, selectedNode = null;
const NODE_R = 18;

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const container = document.getElementById('graph-container');
const tooltip = document.getElementById('tooltip');
const infoBar = document.getElementById('info-bar');
const loadingOverlay = document.getElementById('loading-overlay');

// ── Resize ──────────────────────────────────────────────────────────────
function resize() {
  const rect = container.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
  draw();
}
new ResizeObserver(resize).observe(container);
resize();

// ── Layout helpers ──────────────────────────────────────────────────────
function layoutNodes(rawNodes, rawEdges) {
  // Use positions from backend if provided, else simple grid
  const W = canvas.width, H = canvas.height;
  const positioned = rawNodes.map((n, i) => {
    if (n.position && typeof n.position.x === 'number') {
      return { ...n, x: n.position.x, y: n.position.y };
    }
    const cols = Math.ceil(Math.sqrt(rawNodes.length));
    const col = i % cols, row = Math.floor(i / cols);
    return { ...n, x: 80 + col * 150, y: 60 + row * 100 };
  });
  return positioned;
}

// ── Draw ────────────────────────────────────────────────────────────────
function getComputedVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.translate(offsetX, offsetY);
  ctx.scale(scale, scale);

  const fgColor = getComputedVar('--fg') || '#ccc';
  const borderColor = getComputedVar('--border') || '#444';
  const linkColor = getComputedVar('--link') || '#4fc3f7';

  // Edges
  ctx.strokeStyle = borderColor;
  ctx.lineWidth = 1 / scale;
  for (const e of edges) {
    const src = nodes.find(n => n.id === e.source);
    const tgt = nodes.find(n => n.id === e.target);
    if (!src || !tgt) continue;
    ctx.beginPath();
    ctx.moveTo(src.x, src.y);
    ctx.lineTo(tgt.x, tgt.y);
    ctx.stroke();
    // Arrow head
    const angle = Math.atan2(tgt.y - src.y, tgt.x - src.x);
    const ax = tgt.x - NODE_R * Math.cos(angle);
    const ay = tgt.y - NODE_R * Math.sin(angle);
    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(ax - 8/scale * Math.cos(angle - 0.3), ay - 8/scale * Math.sin(angle - 0.3));
    ctx.lineTo(ax - 8/scale * Math.cos(angle + 0.3), ay - 8/scale * Math.sin(angle + 0.3));
    ctx.closePath();
    ctx.fillStyle = borderColor;
    ctx.fill();
  }

  // Nodes
  for (const n of nodes) {
    const isSelected = selectedNode && selectedNode.id === n.id;
    const isHovered = hoveredNode && hoveredNode.id === n.id;
    const isHighlighted = n.data && n.data.highlighted;

    ctx.beginPath();
    ctx.arc(n.x, n.y, NODE_R, 0, Math.PI * 2);
    ctx.fillStyle = isSelected
      ? linkColor
      : isHighlighted
      ? '#f9a825'
      : isHovered
      ? '#555'
      : '#333';
    ctx.fill();
    ctx.strokeStyle = isSelected ? linkColor : borderColor;
    ctx.lineWidth = isSelected ? 2 / scale : 1 / scale;
    ctx.stroke();

    // Label
    ctx.fillStyle = fgColor;
    ctx.font = \`\${10 / scale}px var(--vscode-font-family, monospace)\`;
    ctx.textAlign = 'center';
    const label = (n.data && n.data.label) ? String(n.data.label).slice(0, 18) : n.id.slice(0, 18);
    ctx.fillText(label, n.x, n.y + NODE_R + 12 / scale);
  }

  ctx.restore();
}

// ── Pan & Zoom ──────────────────────────────────────────────────────────
canvas.addEventListener('mousedown', e => {
  dragging = true;
  lastMouse = { x: e.clientX, y: e.clientY };
});
canvas.addEventListener('mousemove', e => {
  if (dragging) {
    offsetX += e.clientX - lastMouse.x;
    offsetY += e.clientY - lastMouse.y;
    lastMouse = { x: e.clientX, y: e.clientY };
    draw();
    return;
  }
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  const node = hitTest(wx, wy);
  if (node !== hoveredNode) {
    hoveredNode = node;
    draw();
  }
  if (node) {
    const label = (node.data && node.data.label) ? node.data.label : node.id;
    tooltip.textContent = label;
    tooltip.style.display = 'block';
    tooltip.style.left = (e.clientX + 12) + 'px';
    tooltip.style.top = (e.clientY - 8) + 'px';
  } else {
    tooltip.style.display = 'none';
  }
});
canvas.addEventListener('mouseup', e => {
  if (!dragging) return;
  dragging = false;
  // If mouse didn't move much, treat as click
  const dx = Math.abs(e.clientX - lastMouse.x), dy = Math.abs(e.clientY - lastMouse.y);
  if (dx < 4 && dy < 4) {
    const [wx, wy] = screenToWorld(e.clientX, e.clientY);
    const node = hitTest(wx, wy);
    if (node) {
      selectedNode = node;
      draw();
      vscode.postMessage({ type: 'focusNode', nodeId: node.id });
    }
  }
});
canvas.addEventListener('mouseleave', () => {
  dragging = false;
  hoveredNode = null;
  tooltip.style.display = 'none';
  draw();
});
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 1.1 : 0.9;
  const [wx, wy] = screenToWorld(e.clientX, e.clientY);
  scale *= factor;
  scale = Math.max(0.05, Math.min(scale, 5));
  offsetX = e.clientX - wx * scale;
  offsetY = e.clientY - wy * scale;
  draw();
}, { passive: false });

function screenToWorld(sx, sy) {
  const rect = canvas.getBoundingClientRect();
  return [(sx - rect.left - offsetX) / scale, (sy - rect.top - offsetY) / scale];
}
function hitTest(wx, wy) {
  for (let i = nodes.length - 1; i >= 0; i--) {
    const n = nodes[i];
    const dx = wx - n.x, dy = wy - n.y;
    if (dx * dx + dy * dy <= NODE_R * NODE_R * 1.5) return n;
  }
  return null;
}

// ── Controls ────────────────────────────────────────────────────────────
function zoomIn()  { scale = Math.min(scale * 1.2, 5); draw(); }
function zoomOut() { scale = Math.max(scale * 0.8, 0.05); draw(); }
function fitView() {
  if (nodes.length === 0) return;
  const xs = nodes.map(n => n.x), ys = nodes.map(n => n.y);
  const minX = Math.min(...xs) - NODE_R * 2, maxX = Math.max(...xs) + NODE_R * 2;
  const minY = Math.min(...ys) - NODE_R * 2, maxY = Math.max(...ys) + NODE_R * 2;
  const W = canvas.width, H = canvas.height;
  const scaleX = W / (maxX - minX), scaleY = H / (maxY - minY);
  scale = Math.min(scaleX, scaleY, 2) * 0.9;
  offsetX = (W - (maxX + minX) * scale) / 2;
  offsetY = (H - (maxY + minY) * scale) / 2;
  draw();
}
function resetGraph() {
  selectedNode = null;
  vscode.postMessage({ type: 'resetGraph' });
}

// ── Search ───────────────────────────────────────────────────────────────
let searchTimer;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  searchTimer = setTimeout(() => {
    vscode.postMessage({ type: 'search', query: q });
  }, 400);
});

// ── Message handling ─────────────────────────────────────────────────────
window.addEventListener('message', e => {
  const msg = e.data;
  if (msg.type === 'graphData') {
    loadingOverlay.style.display = 'none';
    const raw = msg.data;
    nodes = layoutNodes(raw.nodes || [], raw.edges || []);
    edges = raw.edges || [];
    selectedNode = null;
    infoBar.textContent = nodes.length + ' nodes, ' + edges.length + ' edges';
    fitView();
    draw();
  } else if (msg.type === 'error') {
    loadingOverlay.style.display = 'none';
    infoBar.textContent = '⚠ ' + msg.message;
  }
});
</script>
</body></html>`;
  }
}
