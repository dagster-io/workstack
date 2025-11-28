/**
 * Component for rendering a message with streaming indicator.
 */

interface StreamingMessageProps {
  role: 'user' | 'assistant';
  content: string;
  isStreaming: boolean;
}

export function StreamingMessage({
  role,
  content,
  isStreaming,
}: StreamingMessageProps) {
  return (
    <div className={`message ${role}`}>
      <div className="message-role">{role === 'user' ? 'You' : 'Claude'}</div>
      <div className="message-content">
        {content}
        {isStreaming && <span className="cursor">|</span>}
      </div>
    </div>
  );
}
