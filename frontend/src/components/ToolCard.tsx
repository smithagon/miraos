import { useEffect, useState } from 'react';

function formatToolPayload(raw?: string): string | undefined {
  if (raw == null || raw === '') return raw;
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}

interface ToolCardProps {
  name: string;
  args?: string;
  result?: string;
  status: 'running' | 'completed' | 'failed';
}

export default function ToolCard({ name, args, result, status }: ToolCardProps) {
  const [isOpen, setIsOpen] = useState(status === 'running');

  useEffect(() => {
    if (status === 'running') {
      setIsOpen(true);
    }
  }, [status]);

  const getIcon = () => {
    if (name.includes('sql')) return '📊';
    if (name.includes('command')) return '🐚';
    if (name.includes('file')) return '📄';
    return '🛠';
  };

  const hasBody = Boolean((args && args.trim()) || (result && result.trim()));

  return (
    <details
      className={`tool-card tool-status-${status}`}
      open={isOpen}
      onToggle={(event) => setIsOpen((event.currentTarget as HTMLDetailsElement).open)}
    >
      <summary className="tool-card-summary">
        <span className={`tool-caret ${isOpen ? 'open' : ''}`} aria-hidden="true">
          ▾
        </span>
        <span className="tool-icon">{getIcon()}</span>
        <span className="tool-name">{name}</span>
        <span className="tool-toggle-label">{isOpen ? 'Minimize' : 'Expand'}</span>
        <span className={`tool-status-pill ${status}`}>{status}</span>
      </summary>
      {hasBody ? (
        <div className="tool-card-body">
          {args && args.trim() && (
            <div className="tool-args">
              <p className="label">Arguments</p>
              <pre>
                <code>{formatToolPayload(args) ?? args}</code>
              </pre>
            </div>
          )}

          {result && result.trim() && (
            <div className="tool-result">
              <p className="label">Observation</p>
              <pre>
                <code>{formatToolPayload(result) ?? result}</code>
              </pre>
            </div>
          )}
        </div>
      ) : null}
    </details>
  );
}
