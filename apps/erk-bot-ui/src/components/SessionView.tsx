/**
 * Component for viewing a single session.
 */

import type { Session } from '../types';
import { MessageInput } from './MessageInput';
import { StreamingMessage } from './StreamingMessage';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface SessionViewProps {
  session: Session;
  messages: Message[];
  streaming: boolean;
  error: string | null;
  onSendMessage: (message: string) => void;
}

export function SessionView({
  session,
  messages,
  streaming,
  error,
  onSendMessage,
}: SessionViewProps) {
  return (
    <div className="session-view">
      <div className="session-header">
        <h2>Session: {session.session_id.slice(0, 8)}...</h2>
        <p className="session-info">
          Working directory: {session.working_directory}
        </p>
      </div>

      <div className="messages">
        {messages.map((message, index) => (
          <StreamingMessage
            key={index}
            role={message.role}
            content={message.content}
            isStreaming={streaming && index === messages.length - 1}
          />
        ))}

        {error && <div className="error-message">{error}</div>}
      </div>

      <MessageInput onSend={onSendMessage} disabled={streaming} />
    </div>
  );
}
