/**
 * Component for displaying and managing sessions.
 */

import type { Session } from '../types';

interface SessionListProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
  onRefresh: () => void;
  loading: boolean;
}

export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
  onRefresh,
  loading,
}: SessionListProps) {
  return (
    <div className="session-list">
      <div className="session-list-header">
        <h2>Sessions</h2>
        <button onClick={onRefresh} disabled={loading}>
          Refresh
        </button>
      </div>

      {sessions.length === 0 ? (
        <p className="no-sessions">No sessions yet</p>
      ) : (
        <ul>
          {sessions.map((session) => (
            <li
              key={session.session_id}
              className={
                session.session_id === currentSessionId ? 'selected' : ''
              }
            >
              <button
                className="session-item"
                onClick={() => onSelect(session.session_id)}
              >
                <span className="session-id">
                  {session.session_id.slice(0, 8)}...
                </span>
                <span className="session-dir">{session.working_directory}</span>
              </button>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(session.session_id);
                }}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
