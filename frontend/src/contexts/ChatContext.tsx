import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

export interface Session {
  session_id: string;
  title: string;
  updated_at: string | null;
}

interface ChatContextType {
  sessions: Session[];
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  loadSessions: () => Promise<Session[]>;
  deleteSession: (id: string) => Promise<void>;
  createSession: () => Promise<string>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    try {
      const { data } = await api.get<Session[]>('/chat/sessions');
      setSessions(data);
      return data;
    } catch (err) {
      console.error('Failed to load sessions', err);
      return [];
    }
  }, []);

  const deleteSession = async (id: string) => {
    try {
      await api.delete(`/chat/sessions/${id}`);
      const remaining = await loadSessions();
      if (activeId === id) {
        setActiveId(remaining.length > 0 ? remaining[0].session_id : null);
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const createSession = async () => {
    try {
      const { data } = await api.post<{ session_id: string }>('/chat/sessions');
      await loadSessions();
      setActiveId(data.session_id);
      return data.session_id;
    } catch (err) {
      console.error('Failed to create session', err);
      throw err;
    }
  };

  useEffect(() => {
    loadSessions().then(data => {
      if (data.length > 0 && !activeId) {
        setActiveId(data[0].session_id);
      }
    });
  }, [loadSessions]);

  return (
    <ChatContext.Provider value={{ sessions, activeId, setActiveId, loadSessions, deleteSession, createSession }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
