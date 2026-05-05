import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useChat } from '../contexts/ChatContext';
import './sidebar.css';

export default function Sidebar() {
  const { sessions, activeId, setActiveId, createSession, deleteSession } = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const isChatPage = location.pathname === '/chat';

  const formatTime = (iso: string | null) => {
    if (!iso) return '';
    const d = new Date(iso);
    const today = new Date();
    if (d.toDateString() === today.toDateString())
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <aside className={`unified-sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-collapsed'}`}>
      {/* Top: Logo & Toggle */}
      <div className="sidebar-top">
        <div className="brand-group">
          <span className="brand-icon">⬡</span>
          {sidebarOpen && <span className="brand-name">Mira</span>}
        </div>
        <button
          className="toggle-btn"
          onClick={() => setSidebarOpen((v) => !v)}
          title={sidebarOpen ? 'Collapse' : 'Expand'}
        >
          {sidebarOpen ? '←' : '→'}
        </button>
      </div>

      {/* Global Navigation */}
      <nav className="global-nav">
        <NavLink to="/chat" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <span className="nav-icon">◎</span>
          {sidebarOpen && <span>Intelligence</span>}
        </NavLink>
      </nav>

      {/* Chat Sessions (Only show detailed list if on chat page or always if desired) */}
      <div className="sessions-section">
        {sidebarOpen && <p className="section-label">Recents</p>}
        
        <button className="new-chat-btn" onClick={() => createSession()} title="New Chat">
          <span>＋</span>
          {sidebarOpen && <span>New Chat</span>}
        </button>

        <div className="sessions-list">
          {sessions.map((s) => (
            <div
              key={s.session_id}
              className={`session-item ${s.session_id === activeId && isChatPage ? 'session-active' : ''}`}
              onClick={() => {
                setActiveId(s.session_id);
              }}
            >
              {sidebarOpen ? (
                <>
                  <div className="session-item-body">
                    <span className="session-title">{s.title}</span>
                    <span className="session-time">{formatTime(s.updated_at)}</span>
                  </div>
                  <button className="session-del" onClick={(e) => { e.stopPropagation(); deleteSession(s.session_id); }} title="Delete">×</button>
                </>
              ) : (
                <div className="session-icon" title={s.title}>
                  {s.title.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Bottom: Settings */}
      <div className="sidebar-bottom">
        <NavLink to="/settings" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
          <span className="nav-icon">⚙</span>
          {sidebarOpen && <span>Settings</span>}
        </NavLink>
        {sidebarOpen && <div className="sidebar-version">v2.2</div>}
      </div>
    </aside>
  );
}
