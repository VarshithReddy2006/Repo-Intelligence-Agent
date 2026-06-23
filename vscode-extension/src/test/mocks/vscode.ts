/**
 * Minimal vscode module mock for unit tests running outside the VS Code host.
 *
 * Registered as a module alias so `import * as vscode from 'vscode'`
 * resolves to this file during testing.
 */

export const workspace = {
  getConfiguration: (_section?: string) => ({
    get: <T>(key: string, defaultValue?: T): T => {
      // Tests override global.__vscodeConfig__ to control values
      const overrides = (global as unknown as Record<string, Record<string, unknown>>).__vscodeConfig__ ?? {};
      if (key in overrides) {
        return overrides[key] as T;
      }
      const defaults: Record<string, unknown> = {
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
      return (key in defaults ? defaults[key] : defaultValue) as T;
    },
    update: async (_key: string, _value: unknown, _target?: unknown) => {},
  }),
  asRelativePath: (_uri: unknown, _includeWorkspaceFolder?: boolean) => 'test/file.py',
  getWorkspaceFolder: (_uri: unknown) => ({ uri: { toString: () => '/workspace' } }),
  onDidChangeConfiguration: (_handler: unknown) => ({ dispose: () => {} }),
  onDidSaveTextDocument: (_handler: unknown) => ({ dispose: () => {} }),
};

export const window = {
  showInformationMessage: async (_msg: string) => {},
  showErrorMessage: async (_msg: string) => {},
  showWarningMessage: async (_msg: string) => {},
  showInputBox: async (_options?: unknown) => undefined as string | undefined,
  showQuickPick: async (_items: unknown, _options?: unknown) => undefined,
  withProgress: async <T>(_options: unknown, task: () => Promise<T>) => task(),
  createOutputChannel: (_name: string) => ({
    appendLine: (_text: string) => {},
    show: () => {},
    dispose: () => {},
  }),
  createWebviewPanel: (_viewType: string, _title: string, _column: unknown, _options?: unknown) => ({
    webview: {
      html: '',
      onDidReceiveMessage: (_handler: unknown) => ({ dispose: () => {} }),
      postMessage: async (_msg: unknown) => {},
      asWebviewUri: (uri: unknown) => uri,
    },
    reveal: (_column: unknown) => {},
    onDidDispose: (_handler: () => void) => ({ dispose: () => {} }),
    dispose: () => {},
  }),
  createStatusBarItem: (_alignment?: unknown, _priority?: number) => ({
    text: '',
    tooltip: '',
    backgroundColor: undefined as unknown,
    command: '' as string | undefined,
    show: () => {},
    hide: () => {},
    dispose: () => {},
  }),
  createTreeView: (_id: string, _options: unknown) => ({
    reveal: async (_element: unknown) => {},
    dispose: () => {},
  }),
  activeTextEditor: undefined as unknown,
  registerTreeDataProvider: (_id: string, _provider: unknown) => ({ dispose: () => {} }),
};

export const languages = {
  registerHoverProvider: (_selector: unknown, _provider: unknown) => ({ dispose: () => {} }),
  registerCodeLensProvider: (_selector: unknown, _provider: unknown) => ({ dispose: () => {} }),
};

export const commands = {
  registerCommand: (_command: string, _callback: (...args: unknown[]) => unknown) => ({ dispose: () => {} }),
  executeCommand: async (_command: string, ..._args: unknown[]) => {},
};

export const Uri = {
  file: (path: string) => ({ fsPath: path, toString: () => path }),
  joinPath: (base: unknown, ...segments: string[]) => ({ fsPath: segments.join('/'), toString: () => segments.join('/') }),
};

export class MarkdownString {
  public value = '';
  public isTrusted = false;
  public supportHtml = false;
  appendMarkdown(md: string) { this.value += md; return this; }
  appendCodeblock(code: string, _lang?: string) { this.value += code; return this; }
}

export class Hover {
  constructor(public contents: unknown, public range?: unknown) {}
}

export class CodeLens {
  constructor(public range: unknown, public command?: unknown) {}
}

export class Range {
  constructor(
    public startLine: number,
    public startChar: number,
    public endLine: number,
    public endChar: number
  ) {}
}

export class Position {
  constructor(public line: number, public character: number) {}
}

export class ThemeColor {
  constructor(public id: string) {}
}

export class ThemeIcon {
  constructor(public id: string, public color?: unknown) {}
}

export class EventEmitter<T> {
  private _listeners: Array<(e: T) => void> = [];
  get event() {
    return (listener: (e: T) => void) => {
      this._listeners.push(listener);
      return { dispose: () => { this._listeners = this._listeners.filter((l) => l !== listener); } };
    };
  }
  fire(e: T) { this._listeners.forEach((l) => l(e)); }
  dispose() { this._listeners = []; }
}

export enum ViewColumn {
  One = 1,
  Beside = -2,
}

export enum TreeItemCollapsibleState {
  None = 0,
  Collapsed = 1,
  Expanded = 2,
}

export class TreeItem {
  public description?: string;
  public tooltip?: string;
  public command?: unknown;
  public iconPath?: unknown;
  public contextValue?: string;
  constructor(public label: string, public collapsibleState?: TreeItemCollapsibleState) {}
}

export enum StatusBarAlignment {
  Left = 1,
  Right = 2,
}

export enum ProgressLocation {
  Notification = 15,
  SourceControl = 1,
  Window = 10,
}

export enum ConfigurationTarget {
  Global = 1,
  Workspace = 2,
  WorkspaceFolder = 3,
}

export const CancellationToken = {
  isCancellationRequested: false,
  onCancellationRequested: (_handler: unknown) => ({ dispose: () => {} }),
};
