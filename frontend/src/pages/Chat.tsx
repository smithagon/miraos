import { useState, useEffect, useRef } from 'react';
import { useTemplates } from '../contexts/TemplateContext';
import { useChat } from '../contexts/ChatContext';
import TerminalAction from '../components/TerminalAction';
import './chat.css';

interface Msg {
  role: 'user' | 'assistant';
  content: string;
  thought?: string;
}

const WS_BASE = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export default function Chat() {
  const { activeTemplateId } = useTemplates();
  const { activeId, loadSessions } = useChat();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // ── Connect to a session ────────────────────────────────────────────
  const openSession = (sessionId: string) => {
    if (wsRef.current) wsRef.current.close();
    setMessages([]);
    setConnected(false);

    const url = new URL(`${WS_BASE}/chat/ws/${sessionId}`);
    if (activeTemplateId) {
      url.searchParams.append('template_id', activeTemplateId);
    }
    const ws = new WebSocket(url.toString());
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === 'history') { setMessages(data.messages || []); return; }
      if (data.type === 'done') { setIsTyping(false); loadSessions(); return; }
      if (data.type === 'error') {
        setMessages((p) => { const n = [...p]; n[n.length - 1] = { ...n[n.length - 1], content: `⚠ ${data.content}` }; return n; });
        setIsTyping(false);
        return;
      }
      setMessages((prev) => {
        const next = [...prev];
        const last = next[next.length - 1];
        if (last?.role === 'assistant') {
          if (data.type === 'thought') return [...next.slice(0, -1), { ...last, thought: (last.thought || '') + data.content }];
          return [...next.slice(0, -1), { ...last, content: last.content + data.content }];
        }
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

          {messages.map((msg, i) => (
            <div key={i} className={`msg-wrap msg-${msg.role}`}>
              <div className="msg-meta">{msg.role === 'user' ? 'You' : 'Mira'}</div>

              {msg.role === 'assistant' && msg.thought && (
                <details className="thought-block">
                  <summary>Thinking process</summary>
                  <p>{msg.thought}</p>
                </details>
              )}

              {(msg.content || msg.role === 'user') && (
                <div className="msg-bubble">
                  {msg.content || (isTyping && i === messages.length - 1 ? <span className="typing-dot" /> : null)}
                  
                  {/* If assistant suggests a command, show TerminalAction */}
                  {msg.role === 'assistant' && extractCommand(msg.content) && i === messages.length - 1 && !isTyping && (
                    <TerminalAction 
                      command={extractCommand(msg.content)!} 
                      onObservation={handleObservation}
                    />
                  )}
                </div>
              )}
            </div>
          ))}

          {isTyping && messages[messages.length - 1]?.content === '' && !messages[messages.length - 1]?.thought && (
            <div className="typing-indicator"><span /><span /><span /></div>
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
