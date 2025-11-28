/**
 * TypeScript types matching the backend models.
 */

export type SessionStatus = 'active';

export interface Session {
  session_id: string;
  external_id: string | null;
  working_directory: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
}

export type StreamEventType =
  | 'assistant_text'
  | 'tool_use'
  | 'tool_result'
  | 'error'
  | 'done';

export interface StreamEvent {
  event_type: StreamEventType;
  content: string;
}

export interface CreateSessionRequest {
  working_directory: string;
  external_id?: string;
}

export interface CreateSessionResponse {
  session_id: string;
  external_id: string | null;
  status: SessionStatus;
}

export interface SendMessageRequest {
  message: string;
}
