import React, { useEffect, useState } from 'react';
import './StatusLine.css';

interface StatusLineProps {
  contextUsed: number;      // in thousands of tokens
  contextMax: number;       // in thousands of tokens
  model?: string;
}

const StatusLine: React.FC<StatusLineProps> = ({
  contextUsed,
  contextMax,
  model = 'kimi-K2.5-thinking'
}) => {
  const [isVisible, setIsVisible] = useState(true);

  const percentage = Math.round((contextUsed / contextMax) * 100);
  const remaining = contextMax - contextUsed;

  // Determine status based on percentage
  const getStatus = (pct: number): 'low' | 'medium' | 'high' => {
    if (pct < 50) return 'low';
    if (pct < 80) return 'medium';
    return 'high';
  };

  const status = getStatus(percentage);

  // Keyboard shortcut to toggle visibility (Ctrl/Cmd + Shift + S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        setIsVisible(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isVisible) {
    return (
      <button
        className="status-line-toggle"
        onClick={() => setIsVisible(true)}
        title="Show status line (Ctrl+Shift+S)"
      >
        <span className="toggle-dot" />
      </button>
    );
  }

  return (
    <div className="status-line">
      <div className="status-left">
        <span className="status-label">Context</span>
        <div className="context-indicator">
          <div className="progress-container">
            <div
              className={`progress-bar ${status}`}
              style={{ width: `${percentage}%` }}
            />
          </div>
          <span className={`percentage-text ${status}`}>
            {percentage}%
          </span>
          <span className="token-details">
            ({contextUsed}k/{contextMax}k)
          </span>
        </div>
      </div>

      <div className="status-right">
        <span className="model-badge">{model}</span>
        <div className="status-dot" title="Connected" />
        <button
          className="close-btn"
          onClick={() => setIsVisible(false)}
          title="Hide (Ctrl+Shift+S)"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default StatusLine;
