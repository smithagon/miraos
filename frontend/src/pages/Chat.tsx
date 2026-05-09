import { useState, useEffect, useRef } from 'react';
import { useTemplates } from '../contexts/TemplateContext';
import { useChat } from '../contexts/ChatContext';
import TerminalAction from '../components/TerminalAction';
import ToolCard from '../components/ToolCard';
import ChatMarkdown from '../components/ChatMarkdown';
import './chat.css';

interface ToolStep {
  name: string;
  args?: string;
  result?: string;
  status: 'running' | 'completed' | 'failed';
}

interface Msg {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  thought?: string;
  tool_id?: string;
  steps?: ToolStep[];
}

function normalizeHistoryMessages(raw: unknown): Msg[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item: unknown) => {
    const m = item as Record<string, unknown>;
    const role = m.role === 'user' ? 'user' : 'assistant';
    const rawSteps = m.steps;
    let steps: ToolStep[] | undefined;
    if (Array.isArray(rawSteps)) {
      steps = rawSteps.map((s: unknown) => {
        const t = s as Record<string, unknown>;
        const st = t.status === 'failed' ? 'failed' : t.status === 'running' ? 'running' : 'completed';
        return {
          name: String(t.name ?? 'tool'),
          args: t.args != null ? String(t.args) : undefined,
          result: t.result != null ? String(t.result) : undefined,
          status: st,
        };
      });
    }
    // Keep thought whenever the API sends a non-empty string (avoid dropping saved reasoning).
    const thought =
      typeof m.thought === 'string' && m.thought.trim().length > 0 ? m.thought : undefined;
    return {
      role,
      content: typeof m.content === 'string' ? m.content : '',
      thought,
      tool_id: typeof m.tool_id === 'string' ? m.tool_id : undefined,
      steps: steps && steps.length > 0 ? steps : undefined,
    };
  });
}

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export default function Chat() {
  const { activeTemplateId } = useTemplates();
  const { activeId, loadSessions, sessions } = useChat();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const currentSession = sessions.find(s => s.session_id === activeId);

  // ── Connect to a session ────────────────────────────────────────────
  const openSession = (sessionId: string) => {
    if (wsRef.current) wsRef.current.close();
    setMessages([]);
    setConnected(false);

    const url = new URL(`${WS_BASE}/chat/ws/${sessionId}`);
    
    // Use session-specific template if available, otherwise fallback to global
    const templateToUse = currentSession?.template_id || activeTemplateId;
    if (templateToUse) {
      url.searchParams.append('template_id', templateToUse);
    }
    const ws = new WebSocket(url.toString());
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'history') {
        setMessages(normalizeHistoryMessages(data.messages));
        return;
      }
      if (data.type === 'done') { setIsTyping(false); loadSessions(); return; }
      if (data.type === 'error') {
        setMessages((p) => { const n = [...p]; n[n.length - 1] = { ...n[n.length - 1], content: `⚠ ${data.content}` }; return n; });
        setIsTyping(false);
        return;
      }
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        
        if (data.type === 'call') {
          if (last?.role === 'assistant') {
            const steps = last.steps || [];
            return [...next.slice(0, -1), { 
              ...last, 
              steps: [...steps, { name: data.name, args: data.arguments, status: 'running' }] 
            }];
          }
          return [...next, { role: 'assistant', content: '', steps: [{ name: data.name, args: data.arguments, status: 'running' }] }];
        }

        if (data.type === 'observation') {
          if (last?.role === 'assistant') {
            const steps = [...(last.steps || [])];
            const lastStep = steps[steps.length - 1];
            if (lastStep && lastStep.name === data.name && lastStep.status === 'running') {
              steps[steps.length - 1] = { ...lastStep, result: data.content, status: 'completed' };
            } else {
              // Orphan observation (no matching call in UI — e.g. reconnect) still show as a tool card
              steps.push({
                name: data.name,
                args: undefined,
                result: data.content,
                status: 'completed',
              });
            }
            return [...next.slice(0, -1), { ...last, steps }];
          }
          return [
            ...next,
            {
              role: 'assistant',
              content: '',
              thought: '',
              steps: [{ name: data.name, result: data.content, status: 'completed' }],
            },
          ];
        }

        if (last?.role === 'assistant') {
          if (data.type === 'thought') return [...next.slice(0, -1), { ...last, thought: (last.thought || '') + data.content }];
          if (data.type === 'chat') return [...next.slice(0, -1), { ...last, content: last.content + data.content }];
        }
        
        if (data.type === 'chat') return [...next, { role: 'assistant', content: data.content }];
        if (data.type === 'thought') return [...next, { role: 'assistant', content: '', thought: data.content }];
        
        return next;
      });
    };
  };

  useEffect(() => {
    if (activeId) openSession(activeId);
    else {
      setMessages([]);
      setConnected(false);
      wsRef.current?.close();
    }
  }, [activeId, activeTemplateId]);

  // ── Send message ────────────────────────────────────────────────────
  const send = () => {
    const text = input.trim();
    if (!text || !connected || isTyping) return;
    setMessages((p) => [...p, { role: 'user', content: text }, { role: 'assistant', content: '', thought: '' }]);
    setIsTyping(true);
    setInput('');
    wsRef.current?.send(text);
  };

  // ── Handle Agentic Observation ──────────────────────────────────────
  const handleObservation = (output: string) => {
    const text = `**Observation**:\n\`\`\`\n${output}\n\`\`\``;
    setMessages((p) => [...p, { role: 'user', content: text }, { role: 'assistant', content: '', thought: '' }]);
    setIsTyping(true);
    wsRef.current?.send(text);
  };

  // Helper to extract bash command from content
  const extractCommand = (content: string) => {
    const match = content.match(/```bash\n([\s\S]*?)\n```/) || content.match(/```\n([\s\S]*?)\n```/);
    return match ? match[1].trim() : null;
  };

  // Auto-grow textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  return (
    <div className="chat-root-simple">
      {/* ── Main chat area ──────────────────────────────────────────── */}
      <div className="chat-main-simple">
        {/* Header with Template Info */}
        {activeId && (
          <div className="chat-header-info">
            <span className="mode-pill">
              {currentSession?.template_name || 'Default Intelligence'}
            </span>
          </div>
        )}

        {/* Messages */}
        <div className="chat-messages">
          {!activeId ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">◎</div>
              <p>Select or create a chat to begin.</p>
            </div>
          ) : messages.length === 0 && !isTyping ? (
            <div className="chat-empty">
              <div className="chat-empty-icon">◎</div>
              <p>What's on your mind?</p>
            </div>
          ) : null}

          {messages.map((msg, i) => {
            const isLastAssistant = msg.role === 'assistant' && i === messages.length - 1;
            const hasSteps = !!(msg.steps && msg.steps.length > 0);
            const showAnswerBubble =
              msg.role === 'user' ||
              (msg.role === 'assistant' &&
                (!!msg.content ||
                  (isTyping && isLastAssistant) ||
                  (!!extractCommand(msg.content) && isLastAssistant && !isTyping)));

            return (
              <div key={i} className={`msg-wrap msg-${msg.role}`}>
                <div className="msg-meta">{msg.role === 'user' ? 'You' : 'Mira'}</div>

                {msg.role === 'assistant' && msg.thought && (
                  <details
                    className="thought-block"
                    open={isTyping && isLastAssistant}
                  >
                    <summary>Thinking process</summary>
                    <div className="thought-block-body">
                      <ChatMarkdown content={msg.thought} />
                    </div>
                  </details>
                )}

                {msg.role === 'user' && showAnswerBubble && (
                  <div className="msg-bubble msg-bubble-md">
                    <ChatMarkdown content={msg.content} />
                  </div>
                )}

                {msg.role === 'assistant' && hasSteps && (
                  <details
                    className="msg-tools-section"
                    aria-label="Tool execution"
                    {...(isLastAssistant && isTyping ? { open: true } : {})}
                  >
                    <summary className="msg-tools-summary">
                      Tool execution
                      <span className="msg-tools-count">({msg.steps!.length})</span>
                    </summary>
                    <div className="msg-tools-stack">
                      {msg.steps!.map((step, si) => (
                        <ToolCard
                          key={si}
                          name={step.name}
                          args={step.args}
                          result={step.result}
                          status={step.status}
                        />
                      ))}
                    </div>
                  </details>
                )}

                {msg.role === 'assistant' && showAnswerBubble && (
                  <div className="msg-bubble msg-bubble-answer msg-bubble-md">
                    {msg.content ? <ChatMarkdown content={msg.content} /> : null}
                    {isTyping && isLastAssistant && !msg.content ? <span className="typing-dot" /> : null}
                    {extractCommand(msg.content) && isLastAssistant && !isTyping && (
                      <TerminalAction
                        command={extractCommand(msg.content)!}
                        onObservation={handleObservation}
                      />
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {isTyping &&
            messages[messages.length - 1]?.role !== 'assistant' &&
            messages[messages.length - 1]?.content === '' &&
            !messages[messages.length - 1]?.thought && (
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <div className="chat-input-wrap">
            <textarea
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={handleInput}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={activeId ? 'Message Mira… (Enter ↵ to send)' : 'Select or create a chat first'}
              rows={1}
              disabled={!connected || isTyping || !activeId}
            />
            <button
              className="send-btn"
              onClick={send}
              disabled={!connected || isTyping || !input.trim() || !activeId}
            >↑</button>
          </div>
          <p className="input-hint">Shift+Enter for new line · {connected ? 'Connected' : 'Disconnected'}</p>
        </div>
      </div>
    </div>
  );
}
