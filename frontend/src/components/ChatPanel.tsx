"use client";

import * as React from 'react';
import { useChat, type Message } from 'ai/react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { ChatMessage } from './chat-message'; // We just created this
import { ScrollArea } from '@/components/ui/scroll-area'; // For the chat log
import { AgentStatusBadge, type AgentStatus } from './agent-status-badge'; // Import badge

export default function ChatPanel() {
  const [chatError, setChatError] = React.useState<string | null>(null); // State for error message
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat', // This will be our Next.js API route
    onError: (err: Error) => {
      console.error("Chat error:", err);
      setChatError(`Sorry, something went wrong: ${err.message}`); // Set error message for UI
    },
    onFinish: () => {
      setChatError(null); // Clear error on successful new message
    }
  });

  // Override handleSubmit to clear error before new submission
  const handleFormSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setChatError(null); // Clear previous errors
    handleSubmit(e); // Call original handleSubmit
  };

  return (
    <div className="flex flex-col w-full max-w-2xl h-[70vh] bg-background rounded-lg shadow-xl">
      {/* Chat Panel Header */}
      <div className="p-4 border-b flex justify-between items-center">
        <h2 className="text-lg font-semibold">InstaBids Chat</h2>
        <AgentStatusBadge status={isLoading ? 'busy' : 'online'} />
      </div>

      <ScrollArea className="flex-grow p-6 space-y-4">
        {messages.length > 0 ? (
          messages.map((m: Message, index: number) => (
            <ChatMessage 
              key={m.id} 
              message={m} 
              isStreaming={isLoading && index === messages.length - 1 && m.role === 'assistant'} 
            />
          ))
        ) : (
          <div className="flex justify-center items-center h-full">
            <p className="text-muted-foreground">Send a message to start the conversation!</p>
          </div>
        )}
      </ScrollArea>
      
      {/* Display error message if it exists */}
      {chatError && (
        <div className="p-4 border-t border-red-500 bg-red-50 text-red-700">
          <p>{chatError}</p>
        </div>
      )}

      <form onSubmit={handleFormSubmit} className="flex items-center p-4 border-t">
        <Input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask InstaBids anything..."
          className="flex-grow mr-2"
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? 'Sending...' : 'Send'}
        </Button>
      </form>
    </div>
  );
}
