/**
 * Component for composing and sending messages.
 */

import { useState, useCallback, type FormEvent } from 'react';

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled: boolean;
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (message.trim() && !disabled) {
        onSend(message.trim());
        setMessage('');
      }
    },
    [message, disabled, onSend]
  );

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
        disabled={disabled}
        rows={3}
      />
      <button type="submit" disabled={disabled || !message.trim()}>
        {disabled ? 'Sending...' : 'Send'}
      </button>
    </form>
  );
}
