import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useTemplates } from '../contexts/TemplateContext';
import './layout.css';

export default function Layout() {
  const { templates, activeTemplateId, setActiveTemplateId } = useTemplates();

  return (
    <div className="app-shell">
      <Sidebar />
      
      <div className="main-wrapper">
        <header className="top-bar">
          <div className="top-bar-left">
            <div className="app-status">
              <span className="status-dot online" />
              <span className="status-text">Mira OS · v2.2</span>
            </div>
          </div>
          <div className="top-bar-right">
            <div className="template-selector-wrap">
              <span className="selector-label">Base Prompt:</span>
              <select 
                className="premium-select"
                value={activeTemplateId || ''} 
                onChange={(e) => setActiveTemplateId(e.target.value || null)}
              >
                <option value="">Default Intelligence</option>
                {templates.map(t => (
                  <option key={t._id} value={t._id}>{t.name}</option>
                ))}
              </select>
            </div>
          </div>
        </header>
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
