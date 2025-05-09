"use client";

import { cn } from "@/lib/utils";

export type AgentStatus = "online" | "offline" | "busy" | "idle" | "error";

interface AgentStatusBadgeProps {
  status: AgentStatus;
}

const statusStyles: Record<AgentStatus, string> = {
  online: "bg-green-500",
  offline: "bg-gray-500",
  busy: "bg-yellow-500 animate-pulse",
  idle: "bg-green-500",
  error: "bg-red-500",
};

const statusText: Record<AgentStatus, string> = {
  online: "Online",
  offline: "Offline",
  busy: "Busy",
  idle: "Idle",
  error: "Error",
};

export function AgentStatusBadge({ status }: AgentStatusBadgeProps) {
  return (
    <div className="flex items-center space-x-2">
      <span
        className={cn(
          "h-3 w-3 rounded-full",
          statusStyles[status]
        )}
        title={statusText[status]}
      />
      <span className="text-sm text-muted-foreground">
        {statusText[status]}
      </span>
    </div>
  );
}
