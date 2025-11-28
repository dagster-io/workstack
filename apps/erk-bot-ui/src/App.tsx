/**
 * Root application component.
 */

import { useEffect, useState, useCallback } from 'react';
import { useSession } from './hooks/useSession';
import { useSSE } from './hooks/useSSE';
import { SessionList } from './components/SessionList';
import { SessionView } from './components/SessionView';
import './App.css';

const POLL_INTERVAL_MS = 10000; // 10 seconds

export default function App() {
  const {
    sessions,
    currentSession,
    loading,
    error: sessionError,
    refreshSessions,
    selectSession,
    createSession,
    deleteSession,
  } = useSession();

  const {
    messages,
    streaming,
    error: sseError,
    sendUserMessage,
    clearMessages,
  } = useSSE();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newWorkingDir, setNewWorkingDir] = useState('');

  // Initial load and periodic polling
  useEffect(() => {
    refreshSessions();

    const interval = setInterval(() => {
      refreshSessions();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [refreshSessions]);

  // Clear messages when selecting a new session
  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      clearMessages();
      await selectSession(sessionId);
    },
    [selectSession, clearMessages]
  );

  const handleCreateSession = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!newWorkingDir.trim()) return;

      try {
        await createSession(newWorkingDir.trim());
        setNewWorkingDir('');
        setShowCreateForm(false);
        clearMessages();
      } catch {
        // Error is handled by the hook
      }
    },
    [createSession, newWorkingDir, clearMessages]
  );

  const handleSendMessage = useCallback(
    (message: string) => {
      if (currentSession) {
        sendUserMessage(currentSession.session_id, message);
      }
    },
    [currentSession, sendUserMessage]
  );

  const error = sessionError ?? sseError;

  return (
    <div className="app">
      <header>
        <h1>Erk Bot</h1>
        <button onClick={() => setShowCreateForm(!showCreateForm)}>
          {showCreateForm ? 'Cancel' : 'New Session'}
        </button>
      </header>

      {error && <div className="global-error">{error}</div>}

      {showCreateForm && (
        <form className="create-form" onSubmit={handleCreateSession}>
          <input
            type="text"
            value={newWorkingDir}
            onChange={(e) => setNewWorkingDir(e.target.value)}
            placeholder="Working directory (e.g., /path/to/repo)"
          />
          <button type="submit" disabled={!newWorkingDir.trim()}>
            Create
          </button>
        </form>
      )}

      <main>
        <aside>
          <SessionList
            sessions={sessions}
            currentSessionId={currentSession?.session_id ?? null}
            onSelect={handleSelectSession}
            onDelete={deleteSession}
            onRefresh={refreshSessions}
            loading={loading}
          />
        </aside>

        <section>
          {currentSession ? (
            <SessionView
              session={currentSession}
              messages={messages}
              streaming={streaming}
              error={sseError}
              onSendMessage={handleSendMessage}
            />
          ) : (
            <div className="no-session">
              <p>Select a session or create a new one</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
