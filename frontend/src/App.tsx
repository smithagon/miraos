import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Chat from './pages/Chat';
import Settings from './pages/Settings';
import { TemplateProvider } from './contexts/TemplateContext';
import { ChatProvider } from './contexts/ChatContext';

export default function App() {
  return (
    <TemplateProvider>
      <ChatProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ChatProvider>
    </TemplateProvider>
  );
}
