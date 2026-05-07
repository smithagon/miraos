import { useState, useEffect } from 'react';
import { useTemplates, type Template } from '../contexts/TemplateContext';
import api from '../services/api';
import './settings.css';

// ─── Sub-Tab Types ────────────────────────────────────────────────────────────
type ConfigTab = 'prompt' | 'rag' | 'nl2sql' | 'permissions';

// ─── RAG Tool View ───────────────────────────────────────────────────────────
function RagTool() {
  return (
    <div className="tool-config-view">
      <div className="tool-view-header">
        <div className="tool-icon rag-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 6h16M4 10h16M4 14h10M4 18h6" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="19" cy="17" r="3"/>
            <path d="M21.5 19.5l1.5 1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <h3>Retrieval-Augmented Generation</h3>
          <p>Ground this template's responses in specific knowledge bases and documents.</p>
        </div>
      </div>

      <div className="tool-options-grid">
        <div className="tool-option-card locked">
          <div className="lock-badge">Premium</div>
          <h4>Knowledge Sources</h4>
          <p>Connect PDF, Notion, or S3 buckets to this template.</p>
        </div>
        <div className="tool-option-card locked">
          <div className="lock-badge">Premium</div>
          <h4>Retrieval Strategy</h4>
          <p>Configure chunking and similarity thresholds.</p>
        </div>
      </div>
    </div>
  );
}

// ─── Schema Viewer Component ────────────────────────────────────────────────
function SchemaViewer({ tables, onRefresh }: { tables: any[], onRefresh?: () => void }) {
  const [expandedTable, setExpandedTable] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'cols' | 'data'>('cols');

  return (
    <div className="schema-viewer">
      <div className="schema-viewer-header">
        <h4>Indexed Tables ({tables.length})</h4>
        {onRefresh && (
          <button className="refresh-schema-btn" onClick={onRefresh}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Refresh Schema
          </button>
        )}
      </div>
      <div className="table-grid">
        {tables.map((table) => (
          <div 
            key={table.name} 
            className={`schema-table-card ${expandedTable === table.name ? 'expanded' : ''}`}
            onClick={() => {
              if (expandedTable !== table.name) {
                setExpandedTable(table.name);
                setViewMode('cols');
              } else {
                setExpandedTable(null);
              }
            }}
          >
            <div className="table-card-main">
              <div className="table-info">
                <div className="table-name-row">
                  <span className="table-name">{table.name}</span>
                  <span className="col-count">{table.columns.length} columns • {table.row_count} rows</span>
                </div>
                {table.description && <p className="table-ai-desc">{table.description}</p>}
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: expandedTable === table.name ? 'rotate(180deg)' : '' }}>
                <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            
            {expandedTable === table.name && (
              <div className="table-detail-container" onClick={(e) => e.stopPropagation()}>
                <div className="detail-tabs">
                  <button className={viewMode === 'cols' ? 'active' : ''} onClick={() => setViewMode('cols')}>Structure</button>
                  <button className={viewMode === 'data' ? 'active' : ''} onClick={() => setViewMode('data')}>Sample Data</button>
                </div>

                {viewMode === 'cols' && (
                  <div className="column-list">
                    {table.columns.map((col: any) => (
                      <div key={col.name} className="column-item">
                        <div className="col-core">
                          <span className="col-name">{col.name}</span>
                          <span className="col-type">{col.type}</span>
                        </div>
                        <div className="col-tags">
                          {col.primary_key && <span className="pk-tag">PK</span>}
                          {col.foreign_key && (
                            <div className="fk-link">
                              <span className="fk-tag">FK</span>
                              <span className="fk-arrow">→</span>
                              <span className="fk-target">{col.foreign_key}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {viewMode === 'data' && (
                  <div className="sample-data-view">
                    {table.sample_data && table.sample_data.length > 0 ? (
                      <div className="data-scroll">
                        <table className="sample-table">
                          <thead>
                            <tr>
                              {Object.keys(table.sample_data[0]).map(k => <th key={k}>{k}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {table.sample_data.map((row: any, i: number) => (
                              <tr key={i}>
                                {Object.values(row).map((v: any, j) => <td key={j}>{String(v)}</td>)}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="no-data">No sample data available.</div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── NL2SQL Tool View ────────────────────────────────────────────────────────
function Nl2SqlTool({ template, onUpdate }: { template: Partial<Template>, onUpdate: (updates: any) => void }) {
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [discoveryStatus, setDiscoveryStatus] = useState<string | null>(null);
  const [connString, setConnString] = useState(template.nl2sql_config?.connection_string || '');
  const [schemaMetadata, setSchemaMetadata] = useState<any[]>([]);

  useEffect(() => {
    if (template.nl2sql_config?.status === 'indexed' && connString) {
      fetchMetadata();
    }
  }, [template._id, template.nl2sql_config?.status]);

  const fetchMetadata = async () => {
    if (!connString) return;
    try {
      const res = await api.get('/nl2sql/metadata', { params: { connection_string: connString } });
      setSchemaMetadata(res.data.tables || []);
      if (res.data.status === 'crawled') {
        setDiscoveryStatus('Schema found. AI is generating descriptions...');
      } else if (res.data.status === 'enriched') {
        setDiscoveryStatus('Full AI enrichment complete!');
      }
    } catch (err) {
      console.error('Failed to fetch metadata', err);
    }
  };

  const handleDiscover = async () => {
    if (!connString) return;
    setIsDiscovering(true);
    setDiscoveryStatus('Connecting to database...');
    try {
      await api.post('/nl2sql/discover', {
        name: template.name || 'Default DB',
        connection_string: connString
      });
      
      // Update local state immediately
      onUpdate({
        nl2sql_config: {
          ...template.nl2sql_config,
          connection_string: connString,
          status: 'indexed'
        }
      });
      
      setDiscoveryStatus('Discovery task queued. Refreshing schema...');
      
      // Attempt an immediate fetch (the structure crawl is usually fast)
      setTimeout(fetchMetadata, 2000); 

    } catch (err: any) {
      setDiscoveryStatus(`Error: ${err.response?.data?.detail || 'Failed to index'}`);
    } finally {
      setIsDiscovering(false);
    }
  };

  return (
    <div className="tool-config-view">
      <div className="tool-view-header">
        <div className="tool-icon nl2sql-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"/>
            <path d="M3 5v14c0 1.657 4.03 3 9 3s9-1.343 9-3V5" strokeLinecap="round"/>
            <path d="M3 12c0 1.657 4.03 3 9 3s9-1.343 9-3" strokeLinecap="round"/>
          </svg>
        </div>
        <div>
          <h3>NL2SQL Engine</h3>
          <p>Allow this template to query databases using natural language commands.</p>
        </div>
      </div>

      <div className="tool-config-card">
        <div className="card-section">
          <h4>Database Connection</h4>
          <p className="section-hint">Enter a SQLAlchemy-compatible connection string (e.g., postgresql://user:pass@host:5432/db).</p>
          <div className="input-with-action">
            <input 
              type="password"
              placeholder="postgresql://..." 
              value={connString}
              onChange={(e) => setConnString(e.target.value)}
              className="glass-input"
            />
            <button 
              className={`action-btn ${isDiscovering ? 'loading' : ''}`} 
              onClick={handleDiscover}
              disabled={isDiscovering || !connString}
            >
              {isDiscovering ? 'Discovering...' : 'Connect & Discover'}
            </button>
          </div>
          {discoveryStatus && <div className={`status-message ${discoveryStatus.includes('Error') ? 'error' : 'success'}`}>{discoveryStatus}</div>}
        </div>

        <div className="tool-options-grid mt-32">
          <div className={`tool-option-card ${!template.nl2sql_config?.status ? 'locked' : ''}`}>
            {(!template.nl2sql_config?.status) && <div className="lock-badge">Inactive</div>}
            <h4>Database Schema</h4>
            <p>Tables and columns are automatically indexed for semantic search.</p>
            {template.nl2sql_config?.status === 'indexed' && (
              <div className="schema-badge">
                <span className="dot pulse"></span>
                Active Schema
              </div>
            )}
          </div>
          <div className="tool-option-card">
            <div className="lock-badge">Premium</div>
            <h4>Execution Policy</h4>
            <p>Currently enforced: <strong>Read-Only (SELECT)</strong></p>
          </div>
        </div>

        {template.nl2sql_config?.status === 'indexed' && schemaMetadata.length > 0 && (
          <div className="mt-32">
            <SchemaViewer tables={schemaMetadata} onRefresh={fetchMetadata} />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Permissions Tool View ───────────────────────────────────────────────────
function PermissionsTool({ template, onUpdate }: { template: Partial<Template>, onUpdate: (updates: any) => void }) {
  const availableTools = [
    { id: 'execute_command', name: 'Terminal Execution', desc: 'Allow the agent to run bash commands.', icon: '🐚' },
    { id: 'list_dir', name: 'List Directory', desc: 'Allow the agent to see files in the workspace.', icon: '📁' },
    { id: 'read_file', name: 'Read File', desc: 'Allow the agent to read file contents.', icon: '📄' },
    { id: 'get_db_schema', name: 'DB Schema Discovery', desc: 'Allow the agent to see database structures.', icon: '📊' },
    { id: 'execute_sql', name: 'SQL Execution', desc: 'Allow the agent to run read-only SQL queries.', icon: '⚡' },
  ];

  const allowedTools = template.allowed_tools || [];

  const toggleTool = (id: string) => {
    const next = allowedTools.includes(id)
      ? allowedTools.filter(t => t !== id)
      : [...allowedTools, id];
    onUpdate({ allowed_tools: next });
  };

  return (
    <div className="tool-config-view">
      <div className="tool-view-header">
        <div className="tool-icon permissions-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <div>
          <h3>Agent Permissions</h3>
          <p>Control which tools this agent can use during its autonomous loop.</p>
        </div>
      </div>

      <div className="tool-options-grid mt-32">
        {availableTools.map(tool => (
          <div 
            key={tool.id} 
            className={`tool-option-card selectable ${allowedTools.includes(tool.id) ? 'selected' : ''}`}
            onClick={() => toggleTool(tool.id)}
          >
            <div className="tool-card-top">
              <span className="tool-card-icon">{tool.icon}</span>
              <div className={`checkbox-custom ${allowedTools.includes(tool.id) ? 'checked' : ''}`} />
            </div>
            <h4>{tool.name}</h4>
            <p>{tool.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Settings component ─────────────────────────────────────────────────
export default function Settings() {
  const { templates, refreshTemplates } = useTemplates();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<Partial<Template> | null>(null);
  const [activeSubTab, setActiveSubTab] = useState<ConfigTab>('prompt');
  const [isSaving, setIsSaving] = useState(false);

  // Initial selection (only once on load)
  useEffect(() => {
    if (templates.length > 0 && selectedTemplateId === null && editingTemplate === null) {
      setSelectedTemplateId(templates[0]._id);
      setEditingTemplate(templates[0]);
    }
  }, [templates, selectedTemplateId, editingTemplate]);

  const handleSelectTemplate = (t: Template) => {
    setSelectedTemplateId(t._id);
    setEditingTemplate(t);
  };

  const handleAddNew = () => {
    const newT = { name: 'New Template', base_prompt: '' };
    setSelectedTemplateId(null);
    setEditingTemplate(newT);
    setActiveSubTab('prompt');
  };

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
          allowed_tools: editingTemplate.allowed_tools || [],
          nl2sql_config: editingTemplate.nl2sql_config,
        });
      } else {
        const res = await api.post('/templates', {
          name: editingTemplate.name,
          base_prompt: editingTemplate.base_prompt,
          is_active: true,
          allowed_tools: editingTemplate.allowed_tools || [],
          nl2sql_config: editingTemplate.nl2sql_config,
        });
        setSelectedTemplateId(res.data._id);
      }
      await refreshTemplates();
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
      if (selectedTemplateId === id) {
        setSelectedTemplateId(null);
        setEditingTemplate(null);
      }
    } catch (err) {
      console.error('Failed to delete template', err);
    }
  };

  return (
    <div className="settings-container">
      {/* ── Left Side Panel: Template List ── */}
      <aside className="settings-sidebar">
        <div className="sidebar-header">
          <h2>Settings</h2>
          <button className="new-template-btn" onClick={handleAddNew}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 5v14M5 12h14" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
        <div className="template-list">
          <div className="list-group-label">Templates</div>
          {templates.map((t) => (
            <button
              key={t._id}
              className={`template-item ${selectedTemplateId === t._id ? 'active' : ''}`}
              onClick={() => handleSelectTemplate(t)}
            >
              <div className="template-item-info">
                <span className="name">{t.name}</span>
                <span className="preview">{t.base_prompt.slice(0, 30)}...</span>
              </div>
            </button>
          ))}
          {templates.length === 0 && (
            <div className="empty-sidebar">No templates yet</div>
          )}
        </div>
      </aside>

      {/* ── Main Detail Area ── */}
      <main className="settings-detail">
        {editingTemplate ? (
          <>
            <header className="detail-header">
              <input
                className="template-name-input"
                value={editingTemplate.name || ''}
                onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                placeholder="Template Name"
              />
              <div className="header-actions">
                {editingTemplate._id && (
                  <button className="delete-btn" onClick={() => handleDelete(editingTemplate._id!)}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                )}
                <button className="save-config-btn" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </header>

            <div className="detail-layout">
              {/* ── Sub Side Panel for Selection ── */}
              <nav className="sub-side-panel">
                <div className="sub-nav-group">
                  <div className="sub-nav-label">Core</div>
                  <button
                    className={`sub-nav-item ${activeSubTab === 'prompt' ? 'active' : ''}`}
                    onClick={() => setActiveSubTab('prompt')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    Base Prompt
                  </button>
                </div>

                <div className="sub-nav-group">
                  <div className="sub-nav-label">Tools</div>
                  <button
                    className={`sub-nav-item ${activeSubTab === 'rag' ? 'active' : ''}`}
                    onClick={() => setActiveSubTab('rag')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 2v10M18.5 7.5L12 14M5.5 7.5L12 14" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 17l10 5 10-5" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 12l10 5 10-5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    RAG Tool
                  </button>
                  <button
                    className={`sub-nav-item ${activeSubTab === 'nl2sql' ? 'active' : ''}`}
                    onClick={() => setActiveSubTab('nl2sql')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5M3 5c0 1.66 4 3 9 3s9-1.34 9-3M3 5c0-1.66 4-3 9-3s9 1.34 9 3M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
                    </svg>
                    NL2SQL Tool
                  </button>
                  <button
                    className={`sub-nav-item ${activeSubTab === 'permissions' ? 'active' : ''}`}
                    onClick={() => setActiveSubTab('permissions')}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    Permissions
                  </button>
                </div>
              </nav>

              {/* ── Content Area ── */}
              <div className="config-content-area">
                {activeSubTab === 'prompt' && (
                  <div className="prompt-editor">
                    <label>System Instructions</label>
                    <textarea
                      value={editingTemplate.base_prompt || ''}
                      onChange={(e) => setEditingTemplate({ ...editingTemplate, base_prompt: e.target.value })}
                      placeholder="You are an expert AI assistant..."
                      rows={15}
                    />
                    <p className="hint">This prompt defines the core personality and behavior of the AI when using this template.</p>
                  </div>
                )}
                {activeSubTab === 'rag' && <RagTool />}
                {activeSubTab === 'nl2sql' && (
                  <Nl2SqlTool 
                    template={editingTemplate} 
                    onUpdate={(updates) => setEditingTemplate({ ...editingTemplate, ...updates })}
                  />
                )}
                {activeSubTab === 'permissions' && (
                  <PermissionsTool 
                    template={editingTemplate} 
                    onUpdate={(updates) => setEditingTemplate({ ...editingTemplate, ...updates })}
                  />
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="no-selection">
            <div className="placeholder-icon">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <rect x="3" y="3" width="18" height="18" rx="2" strokeDasharray="4 4"/>
              </svg>
            </div>
            <h3>Select a template to configure</h3>
            <p>Choose an existing template from the sidebar or create a new one to get started.</p>
            <button className="create-first-btn" onClick={handleAddNew}>Create Template</button>
          </div>
        )}
      </main>
    </div>
  );
}
