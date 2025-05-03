import React, { useEffect, useState } from "react";

/**
 * ChatTimeline component displays a conversation history between homeowner and agent
 * 
 * @param {Object} props - Component props
 * @param {string} props.projectId - UUID of the project to display messages for
 * @returns {JSX.Element} Rendered component
 */
export default function ChatTimeline({ projectId }) {
  const [msgs, setMsgs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) return;
    
    setIsLoading(true);
    setError(null);
    
    fetch(`/api/projects/${projectId}/messages`)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to fetch messages: ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        setMsgs(data);
        setIsLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching messages:", err);
        setError(err.message);
        setIsLoading(false);
      });
  }, [projectId]);

  if (isLoading) {
    return <div className="py-4 text-center text-gray-500">Loading conversation...</div>;
  }

  if (error) {
    return <div className="py-4 text-center text-red-500">Error: {error}</div>;
  }

  if (msgs.length === 0) {
    return <div className="py-4 text-center text-gray-500">No messages yet</div>;
  }

  return (
    <div className="space-y-4 py-4">
      {msgs.map((message) => (
        <div 
          key={message.id} 
          className={`flex ${message.role === "agent" ? "justify-end" : "justify-start"}`}
        >
          <div 
            className={`max-w-[80%] px-4 py-2 rounded-lg ${
              message.role === "agent" 
                ? "bg-blue-100 text-blue-900" 
                : "bg-gray-100 text-gray-900"
            }`}
          >
            <div className="text-xs text-gray-500 mb-1">
              {message.role === "agent" ? "Agent" : "You"}
            </div>
            <div className="whitespace-pre-wrap">{message.content}</div>
            <div className="text-xs text-gray-400 mt-1 text-right">
              {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}