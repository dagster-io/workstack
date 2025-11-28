/**
 * Hook for managing SSE streaming state.
 */

import { useState, useCallback } from 'react';
import type { StreamEvent } from '../types';
import { sendMessage } from '../api/sessions';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface UseSSEReturn {
  messages: Message[];
  streaming: boolean;
  error: string | null;
  sendUserMessage: (sessionId: string, message: string) => Promise<void>;
  clearMessages: () => void;
}

export function useSSE(): UseSSEReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendUserMessage = useCallback(
    async (sessionId: string, message: string) => {
      // Add user message
      setMessages((prev) => [...prev, { role: 'user', content: message }]);
      setStreaming(true);
      setError(null);

      // Start with empty assistant message
      let assistantContent = '';
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      try {
        await sendMessage(sessionId, message, (event: StreamEvent) => {
          if (event.event_type === 'assistant_text') {
            assistantContent += event.content;
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.role === 'assistant') {
                newMessages[newMessages.length - 1] = {
                  ...lastMessage,
                  content: assistantContent,
                };
              }
              return newMessages;
            });
          } else if (event.event_type === 'error') {
            setError(event.content);
          }
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to send message');
      } finally {
        setStreaming(false);
      }
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    streaming,
    error,
    sendUserMessage,
    clearMessages,
  };
}
