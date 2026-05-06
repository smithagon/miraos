import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import './layout.css';

export default function Layout() {
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
            {/* Template selector removed as it is now session-based */}
          </div>
        </header>
        <main className="content-area">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
