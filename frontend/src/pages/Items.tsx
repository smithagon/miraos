import { useState, useEffect } from 'react';
import api from '../services/api';
import './items.css';

interface Item {
  _id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
}

export default function Items() {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [editing, setEditing] = useState<Item | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchItems(); }, []);

  const fetchItems = async () => {
    try { const { data } = await api.get('/items/'); setItems(data); }
    finally { setLoading(false); }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editing) {
      await api.put(`/items/${editing._id}`, { name, description });
      setEditing(null);
    } else {
      await api.post('/items/', { name, description });
    }
    setName(''); setDescription('');
    fetchItems();
  };

  const startEdit = (item: Item) => { setEditing(item); setName(item.name); setDescription(item.description); };

  const deleteItem = async (id: string) => {
    await api.delete(`/items/${id}`);
    fetchItems();
  };

  return (
    <div className="items-page">
      <header className="items-header">
        <h1>Items</h1>
        <span className="item-count">{items.length} total</span>
      </header>

      <div className="items-body">
        <aside className="items-sidebar">
          <h2>{editing ? 'Edit Item' : 'New Item'}</h2>
          <form onSubmit={handleSubmit} className="item-form">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Item name" required />
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" rows={3} />
            <button type="submit" className="submit-btn">{editing ? 'Update' : 'Create'}</button>
            {editing && (
              <button type="button" className="cancel-btn" onClick={() => { setEditing(null); setName(''); setDescription(''); }}>
                Cancel
              </button>
            )}
          </form>
        </aside>

        <div className="items-list">
          {loading ? (
            <p className="state-msg">Loading…</p>
          ) : items.length === 0 ? (
            <p className="state-msg">No items yet. Create your first →</p>
          ) : (
            <div className="items-grid">
              {items.map((item) => (
                <div key={item._id} className="item-card">
                  <div className="item-card-header">
                    <h3>{item.name}</h3>
                    <span className={`badge badge-${item.status}`}>{item.status}</span>
                  </div>
                  {item.description && <p className="item-desc">{item.description}</p>}
                  <div className="item-card-footer">
                    <span className="item-date">{item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}</span>
                    <div className="item-actions">
                      <button onClick={() => startEdit(item)} className="edit-btn">Edit</button>
                      <button onClick={() => deleteItem(item._id)} className="delete-btn">Delete</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
