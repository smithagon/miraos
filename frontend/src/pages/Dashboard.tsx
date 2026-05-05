import { useState, useEffect } from 'react';
import api from '../services/api';
import { getSocket } from '../services/socket';
import '../styles/dashboard.css';

interface Item {
  _id: string;
  name: string;
  description: string;
  status: string;
  createdAt: string;
}

export default function Dashboard() {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [editing, setEditing] = useState<Item | null>(null);
  const [loading, setLoading] = useState(true);
  const [liveEvent, setLiveEvent] = useState('');

  useEffect(() => {
    fetchItems();
    const socket = getSocket();

    socket.on('itemCreated', (item: Item) => {
      setItems((prev) => [item, ...prev]);
      flash('✦ New item created in real-time!');
    });
    socket.on('itemUpdated', (item: Item) => {
      setItems((prev) => prev.map((i) => (i._id === item._id ? item : i)));
      flash('✦ Item updated in real-time!');
    });
    socket.on('itemDeleted', ({ id }: { id: string }) => {
      setItems((prev) => prev.filter((i) => i._id !== id));
      flash('✦ Item removed in real-time!');
    });

    return () => {
      socket.off('itemCreated');
      socket.off('itemUpdated');
      socket.off('itemDeleted');
    };
  }, []);

  const flash = (msg: string) => {
    setLiveEvent(msg);
    setTimeout(() => setLiveEvent(''), 3000);
  };

  const fetchItems = async () => {
    try {
      const { data } = await api.get('/items');
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editing) {
      await api.put(`/items/${editing._id}`, { name, description });
      setEditing(null);
    } else {
      await api.post('/items', { name, description });
    }
    setName('');
    setDescription('');
    fetchItems();
  };

  const startEdit = (item: Item) => {
    setEditing(item);
    setName(item.name);
    setDescription(item.description);
  };

  const deleteItem = async (id: string) => {
    await api.delete(`/items/${id}`);
    fetchItems();
  };

  return (
    <div className="dashboard">
      <header className="dash-header">
        <div className="dash-logo">⬡ Business OS</div>
        <div className="ws-indicator">
          <span className="ws-dot"></span>Live
        </div>
      </header>

      {liveEvent && <div className="live-badge">{liveEvent}</div>}

      <main className="dash-main">
        <div className="dash-sidebar">
          <h2>{editing ? 'Edit Item' : 'New Item'}</h2>
          <form onSubmit={handleSubmit} className="item-form">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Item name"
              required
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              rows={3}
            />
            <button type="submit" className="submit-btn">
              {editing ? 'Update' : 'Create'}
            </button>
            {editing && (
              <button
                type="button"
                className="cancel-btn"
                onClick={() => { setEditing(null); setName(''); setDescription(''); }}
              >
                Cancel
              </button>
            )}
          </form>
        </div>

        <div className="dash-content">
          <div className="content-header">
            <h2>Items <span className="count">{items.length}</span></h2>
          </div>

          {loading ? (
            <div className="loading">Loading...</div>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <p>No items yet. Create your first one →</p>
            </div>
          ) : (
            <div className="items-grid">
              {items.map((item) => (
                <div key={item._id} className="item-card">
                  <div className="item-header">
                    <h3>{item.name}</h3>
                    <span className={`status-badge status-${item.status}`}>{item.status}</span>
                  </div>
                  {item.description && <p className="item-desc">{item.description}</p>}
                  <div className="item-footer">
                    <span className="item-date">{new Date(item.createdAt).toLocaleDateString()}</span>
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
      </main>
    </div>
  );
}
