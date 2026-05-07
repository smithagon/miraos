import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

export interface Template {
  _id: string;
  name: string;
  base_prompt: string;
  is_active: boolean;
  allowed_tools?: string[];
  nl2sql_config?: {
    connection_string: string;
    status: string;
  };
}

interface TemplateContextType {
  templates: Template[];
  activeTemplateId: string | null;
  setActiveTemplateId: (id: string | null) => void;
  refreshTemplates: () => Promise<void>;
}

const TemplateContext = createContext<TemplateContextType | undefined>(undefined);

export const TemplateProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeTemplateId, setActiveTemplateId] = useState<string | null>(localStorage.getItem('activeTemplateId'));

  const refreshTemplates = async () => {
    try {
      const { data } = await api.get<Template[]>('/templates');
      setTemplates(data);
    } catch (err) {
      console.error('Failed to fetch templates', err);
    }
  };

  useEffect(() => {
    refreshTemplates();
  }, []);

  useEffect(() => {
    if (activeTemplateId) {
      localStorage.setItem('activeTemplateId', activeTemplateId);
    } else {
      localStorage.removeItem('activeTemplateId');
    }
  }, [activeTemplateId]);

  return (
    <TemplateContext.Provider value={{ templates, activeTemplateId, setActiveTemplateId, refreshTemplates }}>
      {children}
    </TemplateContext.Provider>
  );
};

export const useTemplates = () => {
  const context = useContext(TemplateContext);
  if (context === undefined) {
    throw new Error('useTemplates must be used within a TemplateProvider');
  }
  return context;
};
