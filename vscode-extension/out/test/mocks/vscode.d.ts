/**
 * Minimal vscode module mock for unit tests running outside the VS Code host.
 *
 * Registered as a module alias so `import * as vscode from 'vscode'`
 * resolves to this file during testing.
 */
export declare const workspace: {
    getConfiguration: (_section?: string) => {
        get: <T>(key: string, defaultValue?: T) => T;
        update: (_key: string, _value: unknown, _target?: unknown) => Promise<void>;
    };
    asRelativePath: (_uri: unknown, _includeWorkspaceFolder?: boolean) => string;
    getWorkspaceFolder: (_uri: unknown) => {
        uri: {
            toString: () => string;
        };
    };
    onDidChangeConfiguration: (_handler: unknown) => {
        dispose: () => void;
    };
    onDidSaveTextDocument: (_handler: unknown) => {
        dispose: () => void;
    };
};
export declare const window: {
    showInformationMessage: (_msg: string) => Promise<void>;
    showErrorMessage: (_msg: string) => Promise<void>;
    showWarningMessage: (_msg: string) => Promise<void>;
    showInputBox: (_options?: unknown) => Promise<string | undefined>;
    showQuickPick: (_items: unknown, _options?: unknown) => Promise<undefined>;
    withProgress: <T>(_options: unknown, task: () => Promise<T>) => Promise<T>;
    createOutputChannel: (_name: string) => {
        appendLine: (_text: string) => void;
        show: () => void;
        dispose: () => void;
    };
    createWebviewPanel: (_viewType: string, _title: string, _column: unknown, _options?: unknown) => {
        webview: {
            html: string;
            onDidReceiveMessage: (_handler: unknown) => {
                dispose: () => void;
            };
            postMessage: (_msg: unknown) => Promise<void>;
            asWebviewUri: (uri: unknown) => unknown;
        };
        reveal: (_column: unknown) => void;
        onDidDispose: (_handler: () => void) => {
            dispose: () => void;
        };
        dispose: () => void;
    };
    createStatusBarItem: (_alignment?: unknown, _priority?: number) => {
        text: string;
        tooltip: string;
        backgroundColor: unknown;
        command: string | undefined;
        show: () => void;
        hide: () => void;
        dispose: () => void;
    };
    createTreeView: (_id: string, _options: unknown) => {
        reveal: (_element: unknown) => Promise<void>;
        dispose: () => void;
    };
    activeTextEditor: unknown;
    registerTreeDataProvider: (_id: string, _provider: unknown) => {
        dispose: () => void;
    };
};
export declare const languages: {
    registerHoverProvider: (_selector: unknown, _provider: unknown) => {
        dispose: () => void;
    };
    registerCodeLensProvider: (_selector: unknown, _provider: unknown) => {
        dispose: () => void;
    };
};
export declare const commands: {
    registerCommand: (_command: string, _callback: (...args: unknown[]) => unknown) => {
        dispose: () => void;
    };
    executeCommand: (_command: string, ..._args: unknown[]) => Promise<void>;
};
export declare const Uri: {
    file: (path: string) => {
        fsPath: string;
        toString: () => string;
    };
    joinPath: (base: unknown, ...segments: string[]) => {
        fsPath: string;
        toString: () => string;
    };
};
export declare class MarkdownString {
    value: string;
    isTrusted: boolean;
    supportHtml: boolean;
    appendMarkdown(md: string): this;
    appendCodeblock(code: string, _lang?: string): this;
}
export declare class Hover {
    contents: unknown;
    range?: unknown | undefined;
    constructor(contents: unknown, range?: unknown | undefined);
}
export declare class CodeLens {
    range: unknown;
    command?: unknown | undefined;
    constructor(range: unknown, command?: unknown | undefined);
}
export declare class Range {
    startLine: number;
    startChar: number;
    endLine: number;
    endChar: number;
    constructor(startLine: number, startChar: number, endLine: number, endChar: number);
}
export declare class Position {
    line: number;
    character: number;
    constructor(line: number, character: number);
}
export declare class ThemeColor {
    id: string;
    constructor(id: string);
}
export declare class ThemeIcon {
    id: string;
    color?: unknown | undefined;
    constructor(id: string, color?: unknown | undefined);
}
export declare class EventEmitter<T> {
    private _listeners;
    get event(): (listener: (e: T) => void) => {
        dispose: () => void;
    };
    fire(e: T): void;
    dispose(): void;
}
export declare enum ViewColumn {
    One = 1,
    Beside = -2
}
export declare enum TreeItemCollapsibleState {
    None = 0,
    Collapsed = 1,
    Expanded = 2
}
export declare class TreeItem {
    label: string;
    collapsibleState?: TreeItemCollapsibleState | undefined;
    description?: string;
    tooltip?: string;
    command?: unknown;
    iconPath?: unknown;
    contextValue?: string;
    constructor(label: string, collapsibleState?: TreeItemCollapsibleState | undefined);
}
export declare enum StatusBarAlignment {
    Left = 1,
    Right = 2
}
export declare enum ProgressLocation {
    Notification = 15,
    SourceControl = 1,
    Window = 10
}
export declare enum ConfigurationTarget {
    Global = 1,
    Workspace = 2,
    WorkspaceFolder = 3
}
export declare const CancellationToken: {
    isCancellationRequested: boolean;
    onCancellationRequested: (_handler: unknown) => {
        dispose: () => void;
    };
};
//# sourceMappingURL=vscode.d.ts.map