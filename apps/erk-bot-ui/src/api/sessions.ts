/**
 * API client for session management.
 */

import type {
  Session,
  CreateSessionRequest,
  CreateSessionResponse,
  SendMessageRequest,
  StreamEvent,
  StreamEventType,
} from '../types';

const API_BASE = '/api/sessions';

export async function createSession(
  request: CreateSessionRequest
): Promise<CreateSessionResponse> {
  const response = await fetch(API_BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to create session: ${response.statusText}`);
  }

  return response.json() as Promise<CreateSessionResponse>;
}

export async function listSessions(): Promise<Session[]> {
  const response = await fetch(API_BASE);

  if (!response.ok) {
    throw new Error(`Failed to list sessions: ${response.statusText}`);
  }

  return response.json() as Promise<Session[]>;
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE}/${sessionId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    throw new Error(`Failed to get session: ${response.statusText}`);
  }

  return response.json() as Promise<Session>;
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/${sessionId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    throw new Error(`Failed to delete session: ${response.statusText}`);
  }
}

/**
 * Send a message and receive SSE stream of events.
 *
 * @param sessionId Session UUID
 * @param message User message
 * @param onEvent Callback for each event
 * @returns Promise that resolves when stream ends
 */
export async function sendMessage(
  sessionId: string,
  message: string,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/${sessionId}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message } satisfies SendMessageRequest),
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    let eventType: StreamEventType | null = null;

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7) as StreamEventType;
      } else if (line.startsWith('data: ') && eventType) {
        const content = line.slice(6).replace(/\\n/g, '\n');
        onEvent({ event_type: eventType, content });
        eventType = null;
      }
    }
  }
}
