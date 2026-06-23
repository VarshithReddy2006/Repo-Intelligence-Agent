"use strict";
/**
 * Shared utilities for webview panels.
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
exports.BASE_CSS = void 0;
exports.getNonce = getNonce;
exports.getWebviewUri = getWebviewUri;
const crypto = __importStar(require("crypto"));
const vscode = __importStar(require("vscode"));
/**
 * Generate a cryptographically random nonce for use in Content-Security-Policy headers.
 */
function getNonce() {
    return crypto.randomBytes(16).toString('hex');
}
/**
 * Build a webview URI for a resource file inside the extension.
 */
function getWebviewUri(webview, extensionUri, ...pathSegments) {
    return webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, ...pathSegments));
}
/**
 * Base CSS variables that match VS Code's theme tokens.
 * Inlined into every webview so panels look native.
 */
exports.BASE_CSS = `
:root {
  --bg: var(--vscode-editor-background);
  --fg: var(--vscode-editor-foreground);
  --border: var(--vscode-panel-border);
  --muted: var(--vscode-descriptionForeground);
  --link: var(--vscode-textLink-foreground);
  --input-bg: var(--vscode-input-background);
  --input-fg: var(--vscode-input-foreground);
  --input-border: var(--vscode-input-border);
  --btn-bg: var(--vscode-button-background);
  --btn-fg: var(--vscode-button-foreground);
  --btn-hover-bg: var(--vscode-button-hoverBackground);
  --badge-bg: var(--vscode-badge-background);
  --badge-fg: var(--vscode-badge-foreground);
  --warn: var(--vscode-editorWarning-foreground);
  --error: var(--vscode-errorForeground);
  --success: var(--vscode-testing-iconPassed);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--fg);
  font-family: var(--vscode-font-family);
  font-size: var(--vscode-font-size);
  line-height: 1.5;
  overflow-x: hidden;
}

a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
th, td {
  text-align: left;
  padding: 4px 8px;
  border-bottom: 1px solid var(--border);
}
th { color: var(--muted); font-weight: 600; }

.badge {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 10px;
  font-size: 11px;
  background: var(--badge-bg);
  color: var(--badge-fg);
}

.badge-risk-low    { background: #1a7f1a; color: #fff; }
.badge-risk-medium { background: #8a7000; color: #fff; }
.badge-risk-high   { background: #a83215; color: #fff; }
.badge-risk-extreme { background: #8b0000; color: #fff; }

.section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin-bottom: 8px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
}
.kpi-card {
  background: var(--vscode-editorWidget-background);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
}
.kpi-value { font-size: 22px; font-weight: 700; }
.kpi-label { font-size: 11px; color: var(--muted); }

button {
  background: var(--btn-bg);
  color: var(--btn-fg);
  border: none;
  border-radius: 4px;
  padding: 5px 12px;
  cursor: pointer;
  font-size: 12px;
}
button:hover { background: var(--btn-hover-bg); }
button:disabled { opacity: 0.5; cursor: not-allowed; }

.error-banner {
  padding: 8px 12px;
  background: var(--vscode-inputValidation-errorBackground);
  border: 1px solid var(--vscode-inputValidation-errorBorder);
  border-radius: 4px;
  color: var(--error);
  font-size: 12px;
  margin: 8px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: var(--muted);
  text-align: center;
  gap: 8px;
}
.empty-state .icon { font-size: 32px; }
`;
//# sourceMappingURL=webview.js.map