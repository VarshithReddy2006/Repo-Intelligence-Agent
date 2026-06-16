import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquareCode, Sparkles, Bot, User, RefreshCw } from 'lucide-react';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
}

interface ChatInterfaceProps {
  repoName: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ repoName }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init',
      sender: 'assistant',
      text: `Hello! I've indexed \`${repoName}\`. Ask me anything about its architecture, endpoints, or file structures.`
    }
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const suggestedQuestions = [
    "How are the agent schemas structured?",
    "Where is the FastAPI router initialized?",
    "Which files do I edit to add a new service?"
  ];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const triggerStreamResponse = async (userPrompt: string) => {
    setIsStreaming(true);
    const newAssistantMessageId = Math.random().toString();
    
    // Add empty response placeholder
    setMessages(prev => [
      ...prev,
      { id: newAssistantMessageId, sender: 'assistant', text: '' }
    ]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo: repoName,
          message: userPrompt,
          history: messages.slice(1).map(m => ({
            role: m.sender === 'user' ? 'user' : 'model',
            parts: [m.text]
          }))
        })
      });

      if (!response.body) throw new Error("ReadableStream not available");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let finished = false;

      while (!finished) {
        const { value, done } = await reader.read();
        finished = done;
        if (value) {
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.text) {
                  setMessages(prev =>
                    prev.map(msg =>
                      msg.id === newAssistantMessageId
                        ? { ...msg, text: msg.text + data.text }
                        : msg
                    )
                  );
                }
              } catch (e) {
                // Ignore incomplete JSON chunks
              }
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === newAssistantMessageId
            ? { ...msg, text: "Error fetching response from agent backend. Please verify that api.py is running." }
            : msg
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || isStreaming) return;

    // Add user message
    setMessages(prev => [
      ...prev,
      { id: Math.random().toString(), sender: 'user', text: textToSend }
    ]);
    setInput('');

    await triggerStreamResponse(textToSend);
  };

  return (
    <div className="flex flex-col h-[550px] border border-border bg-card/10 rounded-lg overflow-hidden w-full max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card/40">
        <div className="flex items-center gap-2">
          <MessageSquareCode className="h-4 w-4 text-primary" />
          <span className="font-mono text-sm font-semibold text-text">Repository Chat Assistant</span>
        </div>
        <span className="text-[10px] font-mono border border-primary/30 text-primary px-2 py-0.5 rounded bg-primary/5">
          {repoName}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-grow overflow-y-auto p-4 space-y-4 font-sans text-sm">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 max-w-[85%] ${msg.sender === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 border ${
              msg.sender === 'user' ? 'bg-primary/10 border-primary/30 text-primary' : 'bg-card border-border text-text-muted'
            }`}>
              {msg.sender === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>

            {/* Bubble */}
            <div className={`p-3 rounded-lg border ${
              msg.sender === 'user' 
                ? 'bg-primary/10 border-primary/20 text-text' 
                : 'bg-card/30 border-border text-text opacity-95'
            }`}>
              <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
            </div>
          </div>
        ))}
        {isStreaming && (
          <div className="flex items-center gap-2 text-xs text-text-muted font-mono pl-11">
            <RefreshCw className="h-3 w-3 animate-spin text-primary" />
            <span>Agent is typing...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggested Questions */}
      {messages.length === 1 && (
        <div className="px-4 py-2 bg-canvas/30 border-t border-border">
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

      {/* Input */}
      <div className="p-3 border-t border-border bg-card/25">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder={`Ask a question about ${repoName}...`}
            className="flex-grow bg-canvas border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-sans text-text placeholder:text-text-muted/50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="bg-primary hover:bg-primary-hover text-text font-medium px-3.5 py-2 rounded flex items-center gap-1.5 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;
