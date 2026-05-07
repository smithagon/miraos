
interface ToolCardProps {
  name: string;
  args?: string;
  result?: string;
  status: 'running' | 'completed' | 'failed';
}

export default function ToolCard({ name, args, result, status }: ToolCardProps) {
  const getIcon = () => {
    if (name.includes('sql')) return '📊';
    if (name.includes('command')) return '🐚';
    if (name.includes('file')) return '📄';
    return '🛠';
  };

  return (
    <div className={`tool-card tool-status-${status}`}>
      <div className="tool-card-header">
        <span className="tool-icon">{getIcon()}</span>
        <span className="tool-name">{name}</span>
        <span className={`tool-status-pill ${status}`}>{status}</span>
      </div>
      
      {args && (
        <div className="tool-args">
          <pre><code>{args}</code></pre>
        </div>
      )}

      {result && (
        <div className="tool-result">
          <p className="label">Observation:</p>
          <pre><code>{result}</code></pre>
        </div>
      )}
    </div>
  );
}
