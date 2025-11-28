/**
 * Hook for managing session state.
 */

import { useState, useCallback } from 'react';
import type { Session } from '../types';
import * as api from '../api/sessions';

interface UseSessionReturn {
  sessions: Session[];
  currentSession: Session | null;
  loading: boolean;
  error: string | null;
  refreshSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  createSession: (workingDirectory: string, externalId?: string) => Promise<Session>;
  deleteSession: (sessionId: string) => Promise<void>;
}

export function useSession(): UseSessionReturn {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.listSessions();
      setSessions(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  const selectSession = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError(null);
    try {
      const session = await api.getSession(sessionId);
      setCurrentSession(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load session');
    } finally {
      setLoading(false);
    }
  }, []);

  const createSession = useCallback(
    async (workingDirectory: string, externalId?: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.createSession({
          working_directory: workingDirectory,
          external_id: externalId,
        });

        // Refresh the list and select the new session
        await refreshSessions();
        const session = await api.getSession(response.session_id);
        setCurrentSession(session);
        return session;
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to create session');
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [refreshSessions]
  );

  const deleteSession = useCallback(
    async (sessionId: string) => {
      setLoading(true);
      setError(null);
      try {
        await api.deleteSession(sessionId);

        // Clear current session if it was deleted
        if (currentSession?.session_id === sessionId) {
          setCurrentSession(null);
        }

        // Refresh the list
        await refreshSessions();
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to delete session');
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [currentSession, refreshSessions]
  );

  return {
    sessions,
    currentSession,
    loading,
    error,
    refreshSessions,
    selectSession,
    createSession,
    deleteSession,
  };
}
