"use strict";
/**
 * Minimal vscode module mock for unit tests running outside the VS Code host.
 *
 * Registered as a module alias so `import * as vscode from 'vscode'`
 * resolves to this file during testing.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.CancellationToken = exports.ConfigurationTarget = exports.ProgressLocation = exports.StatusBarAlignment = exports.TreeItem = exports.TreeItemCollapsibleState = exports.ViewColumn = exports.EventEmitter = exports.ThemeIcon = exports.ThemeColor = exports.Position = exports.Range = exports.CodeLens = exports.Hover = exports.MarkdownString = exports.Uri = exports.commands = exports.languages = exports.window = exports.workspace = void 0;
exports.workspace = {
    getConfiguration: (_section) => ({
        get: (key, defaultValue) => {
            // Tests override global.__vscodeConfig__ to control values
            const overrides = global.__vscodeConfig__ ?? {};
            if (key in overrides) {
                return overrides[key];
            }
            const defaults = {
                backendUrl: 'http://127.0.0.1:8001',
                apiToken: '',
                requestTimeoutMs: 5000,
                activeRepository: 'owner/repo',
                'codeLens.enabled': true,
                'hover.enabled': true,
                autoRefresh: false,
                graphLayout: 'dagre',
                theme: 'auto',
            };
            return (key in defaults ? defaults[key] : defaultValue);
        },
        update: async (_key, _value, _target) => { },
    }),
    asRelativePath: (_uri, _includeWorkspaceFolder) => 'test/file.py',
    getWorkspaceFolder: (_uri) => ({ uri: { toString: () => '/workspace' } }),
    onDidChangeConfiguration: (_handler) => ({ dispose: () => { } }),
    onDidSaveTextDocument: (_handler) => ({ dispose: () => { } }),
};
exports.window = {
    showInformationMessage: async (_msg) => { },
    showErrorMessage: async (_msg) => { },
    showWarningMessage: async (_msg) => { },
    showInputBox: async (_options) => undefined,
    showQuickPick: async (_items, _options) => undefined,
    withProgress: async (_options, task) => task(),
    createOutputChannel: (_name) => ({
        appendLine: (_text) => { },
        show: () => { },
        dispose: () => { },
    }),
    createWebviewPanel: (_viewType, _title, _column, _options) => ({
        webview: {
            html: '',
            onDidReceiveMessage: (_handler) => ({ dispose: () => { } }),
            postMessage: async (_msg) => { },
            asWebviewUri: (uri) => uri,
        },
        reveal: (_column) => { },
        onDidDispose: (_handler) => ({ dispose: () => { } }),
        dispose: () => { },
    }),
    createStatusBarItem: (_alignment, _priority) => ({
        text: '',
        tooltip: '',
        backgroundColor: undefined,
        command: '',
        show: () => { },
        hide: () => { },
        dispose: () => { },
    }),
    createTreeView: (_id, _options) => ({
        reveal: async (_element) => { },
        dispose: () => { },
    }),
    activeTextEditor: undefined,
    registerTreeDataProvider: (_id, _provider) => ({ dispose: () => { } }),
};
exports.languages = {
    registerHoverProvider: (_selector, _provider) => ({ dispose: () => { } }),
    registerCodeLensProvider: (_selector, _provider) => ({ dispose: () => { } }),
};
exports.commands = {
    registerCommand: (_command, _callback) => ({ dispose: () => { } }),
    executeCommand: async (_command, ..._args) => { },
};
exports.Uri = {
    file: (path) => ({ fsPath: path, toString: () => path }),
    joinPath: (base, ...segments) => ({ fsPath: segments.join('/'), toString: () => segments.join('/') }),
};
class MarkdownString {
    constructor() {
        this.value = '';
        this.isTrusted = false;
        this.supportHtml = false;
    }
    appendMarkdown(md) { this.value += md; return this; }
    appendCodeblock(code, _lang) { this.value += code; return this; }
}
exports.MarkdownString = MarkdownString;
class Hover {
    constructor(contents, range) {
        this.contents = contents;
        this.range = range;
    }
}
exports.Hover = Hover;
class CodeLens {
    constructor(range, command) {
        this.range = range;
        this.command = command;
    }
}
exports.CodeLens = CodeLens;
class Range {
    constructor(startLine, startChar, endLine, endChar) {
        this.startLine = startLine;
        this.startChar = startChar;
        this.endLine = endLine;
        this.endChar = endChar;
    }
}
exports.Range = Range;
class Position {
    constructor(line, character) {
        this.line = line;
        this.character = character;
    }
}
exports.Position = Position;
class ThemeColor {
    constructor(id) {
        this.id = id;
    }
}
exports.ThemeColor = ThemeColor;
class ThemeIcon {
    constructor(id, color) {
        this.id = id;
        this.color = color;
    }
}
exports.ThemeIcon = ThemeIcon;
class EventEmitter {
    constructor() {
        this._listeners = [];
    }
    get event() {
        return (listener) => {
            this._listeners.push(listener);
            return { dispose: () => { this._listeners = this._listeners.filter((l) => l !== listener); } };
        };
    }
    fire(e) { this._listeners.forEach((l) => l(e)); }
    dispose() { this._listeners = []; }
}
exports.EventEmitter = EventEmitter;
var ViewColumn;
(function (ViewColumn) {
    ViewColumn[ViewColumn["One"] = 1] = "One";
    ViewColumn[ViewColumn["Beside"] = -2] = "Beside";
})(ViewColumn || (exports.ViewColumn = ViewColumn = {}));
var TreeItemCollapsibleState;
(function (TreeItemCollapsibleState) {
    TreeItemCollapsibleState[TreeItemCollapsibleState["None"] = 0] = "None";
    TreeItemCollapsibleState[TreeItemCollapsibleState["Collapsed"] = 1] = "Collapsed";
    TreeItemCollapsibleState[TreeItemCollapsibleState["Expanded"] = 2] = "Expanded";
})(TreeItemCollapsibleState || (exports.TreeItemCollapsibleState = TreeItemCollapsibleState = {}));
class TreeItem {
    constructor(label, collapsibleState) {
        this.label = label;
        this.collapsibleState = collapsibleState;
    }
}
exports.TreeItem = TreeItem;
var StatusBarAlignment;
(function (StatusBarAlignment) {
    StatusBarAlignment[StatusBarAlignment["Left"] = 1] = "Left";
    StatusBarAlignment[StatusBarAlignment["Right"] = 2] = "Right";
})(StatusBarAlignment || (exports.StatusBarAlignment = StatusBarAlignment = {}));
var ProgressLocation;
(function (ProgressLocation) {
    ProgressLocation[ProgressLocation["Notification"] = 15] = "Notification";
    ProgressLocation[ProgressLocation["SourceControl"] = 1] = "SourceControl";
    ProgressLocation[ProgressLocation["Window"] = 10] = "Window";
})(ProgressLocation || (exports.ProgressLocation = ProgressLocation = {}));
var ConfigurationTarget;
(function (ConfigurationTarget) {
    ConfigurationTarget[ConfigurationTarget["Global"] = 1] = "Global";
    ConfigurationTarget[ConfigurationTarget["Workspace"] = 2] = "Workspace";
    ConfigurationTarget[ConfigurationTarget["WorkspaceFolder"] = 3] = "WorkspaceFolder";
})(ConfigurationTarget || (exports.ConfigurationTarget = ConfigurationTarget = {}));
exports.CancellationToken = {
    isCancellationRequested: false,
    onCancellationRequested: (_handler) => ({ dispose: () => { } }),
};
//# sourceMappingURL=vscode.js.map