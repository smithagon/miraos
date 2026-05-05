import { useState } from 'react';
import { useTemplates, type Template } from '../contexts/TemplateContext';
import api from '../services/api';
import './settings.css';

export default function Settings() {
  const { templates, refreshTemplates } = useTemplates();
  const [editingTemplate, setEditingTemplate] = useState<Partial<Template> | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTemplate?.name || !editingTemplate?.base_prompt) return;

    setIsSaving(true);
    try {
      if (editingTemplate._id) {
        await api.put(`/templates/${editingTemplate._id}`, {
          name: editingTemplate.name,
          base_prompt: editingTemplate.base_prompt,
          is_active: editingTemplate.is_active ?? true,
        });
      } else {
        await api.post('/templates', {
          name: editingTemplate.name,
          base_prompt: editingTemplate.base_prompt,
          is_active: true,
        });
      }
      await refreshTemplates();
      setEditingTemplate(null);
    } catch (err) {
      console.error('Failed to save template', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this template?')) return;
    try {
      await api.delete(`/templates/${id}`);
      await refreshTemplates();
    } catch (err) {
      console.error('Failed to delete template', err);
    }
  };

  return (
    <div className="settings-page">
      <header className="settings-header">
        <div>
          <h1>Base Prompts & Templates</h1>
          <p>Define custom system instructions for different use cases.</p>
        </div>
        <button className="add-btn" onClick={() => setEditingTemplate({ name: '', base_prompt: '' })}>
          ＋ New Template
        </button>
      </header>

      <div className="templates-grid">
        {templates.map((t) => (
          <div key={t._id} className="template-card">
            <div className="template-card-header">
              <h3>{t.name}</h3>
              <div className="template-actions">
                <button onClick={() => setEditingTemplate(t)}>Edit</button>
                <button className="del-btn" onClick={() => handleDelete(t._id)}>Delete</button>
              </div>
            </div>
            <div className="template-preview">
              <p>{t.base_prompt}</p>
            </div>
          </div>
        ))}
        {templates.length === 0 && !editingTemplate && (
          <div className="empty-state">
            <p>No templates defined yet. Create your first one to get started!</p>
          </div>
        )}
      </div>

      {editingTemplate && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>{editingTemplate._id ? 'Edit Template' : 'New Template'}</h2>
            <form onSubmit={handleSave}>
              <div className="form-group">
                <label>Template Name</label>
                <input
                  type="text"
                  value={editingTemplate.name || ''}
                  onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                  placeholder="e.g. Dairy Management"
                  required
                />
              </div>
              <div className="form-group">
                <label>Base Prompt (System Message)</label>
                <textarea
                  value={editingTemplate.base_prompt || ''}
                  onChange={(e) => setEditingTemplate({ ...editingTemplate, base_prompt: e.target.value })}
                  placeholder="You are an expert in dairy farm management. Help the user track milk production..."
                  required
                  rows={8}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={() => setEditingTemplate(null)}>Cancel</button>
                <button type="submit" className="save-btn" disabled={isSaving}>
                  {isSaving ? 'Saving...' : 'Save Template'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
