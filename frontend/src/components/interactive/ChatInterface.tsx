import React, { useState, useRef, useEffect } from 'react';
import { apiUrl } from '../../lib/api';
import {
  Send,
  MessageSquareCode,
  Sparkles,
  Bot,
  User,
  RefreshCw,
  FileCode,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  /** Sources attached to this assistant message (from the done event). */
  sources?: string[];
  /** 0-100 confidence score attached to this assistant message. */
  confidence?: number;
  /** True when the LLM was unavailable and we fell back to retrieval-only. */
  fallbackMode?: boolean;
  /** True when this is an inline error (no_repo_selected, etc.). */
  isError?: boolean;
}

interface ChatInterfaceProps {
  /**
   * When non-empty (embedded in AnalysisDashboard), this value is used
   * directly and all resolution fallbacks are skipped.
   *
   * When empty (standalone /chat page), the component resolves the repo
   * via: URL params → localStorage → /api/repos/recent.
   */
  repoName: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Collapsible source citation block rendered under each assistant message. */
const SourcesPanel: React.FC<{
  sources: string[];
  confidence: number;
  fallbackMode: boolean;
}> = ({ sources, confidence, fallbackMode }) => {
  const [open, setOpen] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="mt-2 border border-border/60 rounded-md overflow-hidden text-xs font-mono">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-1.5 bg-canvas/40 hover:bg-canvas/60 transition-colors text-text-muted"
      >
        <span className="flex items-center gap-1.5">
          <FileCode className="h-3 w-3 text-primary" />
          <span>
            {sources.length} source{sources.length !== 1 ? 's' : ''}
          </span>
          {fallbackMode && (
            <span className="ml-2 flex items-center gap-1 text-amber-400">
              <AlertTriangle className="h-3 w-3" />
              <span>fallback mode</span>
            </span>
          )}
          {!fallbackMode && confidence > 0 && (
            <span className="ml-2 text-emerald-500">{confidence}% confidence</span>
          )}
        </span>
        {open ? (
          <ChevronUp className="h-3 w-3" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {/* Source list */}
      {open && (
        <ul className="px-3 py-2 space-y-1 bg-canvas/20">
          {sources.map((src) => (
            <li key={src} className="text-text-muted truncate">
              • {src}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ repoName }) => {
  /**
   * Repo resolution strategy:
   *
   * EMBEDDED MODE  (repoName prop is non-empty — inside AnalysisDashboard)
   *   → use prop directly, skip all fallbacks.
   *
   * STANDALONE MODE (repoName prop is empty — /chat page)
   *   Priority 1: URL params ?owner=...&repo=...
   *   Priority 2: localStorage.activeRepo
   *   Priority 3: async GET /api/repos/recent → data[0].name
   */
  const [activeRepo, setActiveRepo] = useState<string>(() => {
    // Embedded mode: prop is the direct, authoritative value.
    if (repoName) return repoName;

    // Standalone mode fallbacks (synchronous part).
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const owner = urlParams.get('owner');
      const repo = urlParams.get('repo');
      if (owner && repo) return `${owner}/${repo}`;

      const stored = localStorage.getItem('activeRepo');
      if (stored) return stored;
    }

    // Will be resolved async (Priority 3).
    return '';
  });

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  /** Shown when the component is in standalone mode and has no repo at all. */
  const [noRepoError, setNoRepoError] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const suggestedQuestions = [
    'What are the main entry points of this codebase?',
    'Are there any circular dependencies?',
    'Which files are most risky to change?',
    'How do I onboard to this codebase?',
  ];

  // ── Priority 3: async fallback — only runs in standalone mode when prop was empty ──
  useEffect(() => {
    // Skip if prop was provided (embedded) or already resolved.
    if (repoName || activeRepo) return;

    fetch(apiUrl('/api/repos/recent'))
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          const name: string = data[0].name;
          setActiveRepo(name);
          if (typeof window !== 'undefined') {
            localStorage.setItem('activeRepo', name);
          }
        } else {
          // Backend has no recent repos — show the "no repo" state.
          setNoRepoError(true);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch recent repos for chat', err);
        setNoRepoError(true);
      });
    // intentionally only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Sync prop changes into activeRepo (e.g. user switches repos in dashboard) ──
  useEffect(() => {
    if (repoName && repoName !== activeRepo) {
      setActiveRepo(repoName);
    }
  }, [repoName, activeRepo]);

  // ── Sync global active-repo events (for standalone /chat page cross-island updates) ──
  useEffect(() => {
    const handleRepoChanged = (e: Event) => {
      const customEvent = e as CustomEvent<string>;
      if (customEvent.detail && customEvent.detail !== activeRepo) {
        setActiveRepo(customEvent.detail);
      }
    };
    const handleRepoCleared = () => {
      setActiveRepo('');
      setNoRepoError(true);
    };

    window.addEventListener('active-repo-changed', handleRepoChanged);
    window.addEventListener('active-repo-cleared', handleRepoCleared);
    return () => {
      window.removeEventListener('active-repo-changed', handleRepoChanged);
      window.removeEventListener('active-repo-cleared', handleRepoCleared);
    };
  }, [activeRepo]);

  // ── Reset greeting whenever the active repo changes ──
  useEffect(() => {
    if (!activeRepo) {
      setMessages([]);
      return;
    }
    setNoRepoError(false);
    setMessages([
      {
        id: 'init',
        sender: 'assistant',
        text: `Hello! I've indexed \`${activeRepo}\`. Ask me anything about its architecture, endpoints, or file structures.`,
      },
    ]);
  }, [activeRepo]);

  // ── Auto-scroll ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Stream a response from /api/chat ──
  const triggerStreamResponse = async (userPrompt: string) => {
    setIsStreaming(true);
    const assistantId = Math.random().toString();

    // Add empty placeholder for the streaming assistant message.
    setMessages((prev) => [
      ...prev,
      { id: assistantId, sender: 'assistant', text: '' },
    ]);

    try {
      const response = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo: activeRepo,
          message: userPrompt,
          history: messages.slice(1).map((m) => ({
            role: m.sender === 'user' ? 'user' : 'model',
            parts: [m.text],
          })),
        }),
      });

      // Handle non-SSE errors (422 Pydantic validation, 500, etc.)
      if (!response.ok) {
        let detail = `Backend error ${response.status}`;
        try {
          const errBody = await response.json();
          if (errBody?.detail) {
            // Pydantic 422 wraps details in an array
            if (Array.isArray(errBody.detail)) {
              detail = errBody.detail.map((d: any) => d.msg).join('; ');
            } else {
              detail = String(errBody.detail);
            }
          }
        } catch {
          /* ignore parse error */
        }
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, text: detail, isError: true }
              : msg,
          ),
        );
        return;
      }

      if (!response.body) throw new Error('ReadableStream not available');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        if (!value) continue;

        const raw = decoder.decode(value);
        const lines = raw.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));

            // Inline SSE error from the backend (no_repo_selected, etc.)
            if (data.error) {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, text: data.message ?? data.error, isError: true }
                    : msg,
                ),
              );
              continue;
            }

            // Streaming text token
            if (data.text) {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, text: msg.text + data.text }
                    : msg,
                ),
              );
            }

            // Terminal done event — attach sources, confidence, fallback flag
            if (data.status === 'done') {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        sources: data.sources ?? [],
                        confidence: data.confidence ?? 0,
                        fallbackMode: data.fallback_mode ?? false,
                      }
                    : msg,
                ),
              );
            }
          } catch {
            // Ignore malformed / partial SSE lines
          }
        }
      }
    } catch (error) {
      console.error('Chat stream error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                text: 'Could not reach the agent backend. Please verify that api.py is running on port 8001.',
                isError: true,
              }
            : msg,
        ),
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || isStreaming) return;

    setMessages((prev) => [
      ...prev,
      { id: Math.random().toString(), sender: 'user', text: textToSend },
    ]);
    setInput('');

    await triggerStreamResponse(textToSend);
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col min-h-[550px] h-full border border-border bg-card/10 rounded-lg overflow-hidden w-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card/40 shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquareCode className="h-4 w-4 text-primary" />
          <span className="font-mono text-sm font-semibold text-text">
            Repository Chat Assistant
          </span>
        </div>
        <span className="text-[10px] font-mono border border-primary/30 text-primary px-2 py-0.5 rounded bg-primary/5 truncate max-w-[180px]">
          {activeRepo || 'no repo selected'}
        </span>
      </div>

      {/* No-repo state (standalone mode, no resolution succeeded) */}
      {noRepoError && (
        <div className="flex-grow flex flex-col items-center justify-center p-8 gap-3 text-center">
          <AlertTriangle className="h-8 w-8 text-amber-400" />
          <p className="text-sm font-mono text-text-muted">
            No repository selected.
          </p>
          <p className="text-xs text-text-muted max-w-xs">
            Analyse a repository first, then return here to chat with its
            codebase.
          </p>
        </div>
      )}

      {/* Message thread */}
      {!noRepoError && (
        <div className="flex-grow overflow-y-auto p-4 space-y-4 font-sans text-sm">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${
                msg.sender === 'user' ? 'ml-auto flex-row-reverse max-w-[85%]' : 'max-w-[92%]'
              }`}
            >
              {/* Avatar */}
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 border ${
                  msg.sender === 'user'
                    ? 'bg-primary/10 border-primary/30 text-primary'
                    : msg.isError
                    ? 'bg-red-500/10 border-red-500/30 text-red-400'
                    : 'bg-card border-border text-text-muted'
                }`}
              >
                {msg.sender === 'user' ? (
                  <User className="h-4 w-4" />
                ) : (
                  <Bot className="h-4 w-4" />
                )}
              </div>

              {/* Bubble + sources */}
              <div className="flex flex-col gap-1 min-w-0">
                <div
                  className={`p-3 rounded-lg border ${
                    msg.sender === 'user'
                      ? 'bg-primary/10 border-primary/20 text-text'
                      : msg.isError
                      ? 'bg-red-500/5 border-red-500/20 text-red-400'
                      : msg.fallbackMode
                      ? 'bg-amber-500/5 border-amber-500/20 text-text opacity-95'
                      : 'bg-card/30 border-border text-text opacity-95'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed break-words">
                    {msg.text}
                  </p>
                </div>

                {/* Sources panel — only for assistant messages with sources */}
                {msg.sender === 'assistant' &&
                  msg.sources &&
                  msg.sources.length > 0 && (
                    <SourcesPanel
                      sources={msg.sources}
                      confidence={msg.confidence ?? 0}
                      fallbackMode={msg.fallbackMode ?? false}
                    />
                  )}
              </div>
            </div>
          ))}

          {isStreaming && (
            <div className="flex items-center gap-2 text-xs text-text-muted font-mono pl-11">
              <RefreshCw className="h-3 w-3 animate-spin text-primary" />
              <span>Agent is thinking...</span>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Suggested questions — shown only after the greeting message */}
      {!noRepoError && messages.length === 1 && (
        <div className="px-4 py-2 bg-canvas/30 border-t border-border shrink-0">
          <p className="text-[10px] uppercase font-mono tracking-wider text-text-muted font-semibold mb-1.5 flex items-center gap-1">
            <Sparkles className="h-3 w-3 text-primary" /> Suggested Questions
          </p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="text-xs bg-card/60 hover:bg-border/60 text-text-muted hover:text-text border border-border px-2.5 py-1 rounded transition-colors font-sans"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input bar */}
      {!noRepoError && (
        <div className="p-3 border-t border-border bg-card/25 shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend(input);
            }}
            className="flex gap-2 items-end"
          >
            <textarea
              value={input}
              rows={1}
              onChange={(e) => {
                setInput(e.target.value);
                // Auto-grow
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
              }}
              onKeyDown={(e) => {
                // Cmd/Ctrl+Enter or plain Enter without Shift submits
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(input);
                }
              }}
              disabled={isStreaming || !activeRepo}
              placeholder={
                activeRepo
                  ? `Ask a question about ${activeRepo}… (Enter to send)`
                  : 'Waiting for repository...'
              }
              aria-label="Chat message"
              className="flex-grow bg-canvas border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-sans text-text placeholder:text-text-muted/50 resize-none overflow-hidden leading-relaxed"
              style={{ minHeight: '38px' }}
            />
            <button
              type="submit"
              disabled={isStreaming || !input.trim() || !activeRepo}
              aria-label="Send message"
              className="bg-primary hover:bg-primary-hover text-primary-foreground font-medium px-3.5 py-2 rounded flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:shadow-ring shrink-0"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
