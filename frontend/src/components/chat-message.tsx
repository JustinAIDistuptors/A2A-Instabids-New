"use client";

import { Message } from 'ai';
import { cn } from '@/lib/utils'; // Assuming you have a utils.ts for Shadcn

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean; // To indicate if the assistant's last message is still streaming
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <div
      className={cn(
        'mb-4 flex',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-lg px-4 py-2',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        )}
      >
        <p className="whitespace-pre-wrap">
          {message.content}
          {isAssistant && isStreaming && (
            <span className="animate-pulse">...</span>
          )}
        </p>
      </div>
    </div>
  );
}
