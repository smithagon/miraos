import { useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useChat } from '../contexts/ChatContext';
import { useTemplates } from '../contexts/TemplateContext';
import './sidebar.css';

export default function Sidebar() {
  const { sessions, activeId, setActiveId, createSession, deleteSession } = useChat();
  const { templates } = useTemplates();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedNewTemplate, setSelectedNewTemplate] = useState<string>('');
  const location = useLocation();
  const navigate = useNavigate();
  const isChatPage = location.pathname === '/chat';

  const formatTime = (iso: string | null) => {
    if (!iso) return '';
    const d = new Date(iso);
    const today = new Date();
    if (d.toDateString() === today.toDateString())
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const handleCreateNewChat = async (templateId: string | null) => {
    try {
      await createSession(templateId);
      setSelectedNewTemplate(''); // Reset selector
      if (location.pathname !== '/chat') {
        navigate('/chat');
      }
    } catch (err) {
      console.error('Failed to create chat', err);
    }
  };

  return (
    <aside className={`unified-sidebar ${sidebarOpen ? 'sidebar-open' : 'sidebar-collapsed'}`}>
      {/* Top: Logo & Toggle */}
      <div className="sidebar-top">
        <div className="brand-group">
          <span className="brand-icon">⬡</span>
          {sidebarOpen && <span className="brand-name">Mira</span>}
        </div>
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
        {sidebarOpen && <p className="section-label">Intelligence Mode</p>}
        
        {sidebarOpen && (
          <div className="new-chat-selector">
            <select 
              value={selectedNewTemplate} 
              onChange={(e) => setSelectedNewTemplate(e.target.value)}
              className="template-dropdown"
            >
              <option value="">Default Intelligence</option>
              {templates.map(t => (
                <option key={t._id} value={t._id}>{t.name}</option>
              ))}
            </select>
            <button 
              className="new-chat-btn" 
              onClick={() => handleCreateNewChat(selectedNewTemplate || null)} 
              title="New Chat"
            >
              <span>＋</span>
              <span>New Chat</span>
            </button>
          </div>
        )}

        {!sidebarOpen && (
          <button className="new-chat-btn collapsed" onClick={() => handleCreateNewChat(null)} title="New Chat">
            <span>＋</span>
          </button>
        )}

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
                    <div className="session-title-row">
                      <span className="session-title">{s.title}</span>
                      <span className="session-time">{formatTime(s.updated_at)}</span>
                    </div>
                    {s.template_name && (
                      <span className="session-template-tag">{s.template_name}</span>
                    )}
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
        <div className="sidebar-footer">
          <button
            className="collapse-toggle"
            onClick={() => setSidebarOpen((v) => !v)}
            title={sidebarOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
          >
            {sidebarOpen ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 17l-5-5 5-5M18 17l-5-5 5-5" />
                </svg>
                <span>Minimize Menu</span>
              </>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M13 17l5-5-5-5M6 17l5-5-5-5" />
              </svg>
            )}
          </button>
          {sidebarOpen && <div className="sidebar-version">v2.2</div>}
        </div>
      </div>
    </aside>
  );
}
