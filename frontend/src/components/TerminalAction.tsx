import { useState } from 'react';
import api from '../services/api';

interface TerminalActionProps {
  command: string;
  onObservation: (output: string) => void;
}

export default function TerminalAction({ command, onObservation }: TerminalActionProps) {
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [output, setOutput] = useState<string>('');

  const runCommand = async () => {
    setStatus('running');
    try {
      const { data } = await api.post('/system/execute', { command });
      const result = data.stdout || data.stderr || data.error || (data.success ? 'Success (no output)' : 'Failed');
      setOutput(result);
      setStatus('done');
      onObservation(result);
    } catch (err) {
      setStatus('error');
      setOutput('Failed to execute command: ' + String(err));
    }
  };

  return (
    <div className="terminal-action-card">
      <div className="terminal-header">
        <span className="terminal-label">Proposed Action</span>
        <div className="terminal-controls">
          <button 
            className="run-btn" 
            onClick={runCommand} 
            disabled={status === 'running' || status === 'done'}
          >
            {status === 'running' ? 'Running...' : status === 'done' ? 'Executed' : 'Run Action'}
          </button>
        </div>
      </div>
      <div className="terminal-code">
        <code>{command}</code>
      </div>
      {output && (
        <div className="terminal-output">
          <p className="obs-label">Observation:</p>
          <pre>{output}</pre>
        </div>
      )}
    </div>
  );
}
