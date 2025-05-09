-- Migration: 20250509000000_add_a2a_routing_tables.sql
-- Description: Adds database tables for A2A routing and message tracking
-- Part of sprint/memory-a2a-integration

-- Run inside a transaction for atomicity
BEGIN;

-- Add tables for A2A message routing
CREATE TABLE IF NOT EXISTS agent_routing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL UNIQUE,
    endpoint TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    capabilities JSONB DEFAULT '[]',
    last_active TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Table for message routing logs
CREATE TABLE IF NOT EXISTS message_routing_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    route_status TEXT NOT NULL,
    route_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    FOREIGN KEY (sender_agent_id) REFERENCES agent_routing(agent_id),
    FOREIGN KEY (recipient_agent_id) REFERENCES agent_routing(agent_id)
);

-- Create a more robust agent communication table for tracking messages
-- between agents and conversation state
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL,
    session_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient_agent_id TEXT NOT NULL,
    artifacts JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB,
    FOREIGN KEY (sender_agent_id) REFERENCES agent_routing(agent_id),
    FOREIGN KEY (recipient_agent_id) REFERENCES agent_routing(agent_id)
);

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_agent_routing_agent_id ON agent_routing(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_routing_agent_type ON agent_routing(agent_type);
CREATE INDEX IF NOT EXISTS idx_message_routing_logs_message_id ON message_routing_logs(message_id);
CREATE INDEX IF NOT EXISTS idx_message_routing_logs_task_id ON message_routing_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_task_id ON agent_messages(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_messages_session_id ON agent_messages(session_id);

-- Add a field to user_memories to connect with conversation sessions
ALTER TABLE user_memories ADD COLUMN IF NOT EXISTS session_ids TEXT[] DEFAULT '{}';

-- Enable Row Level Security
ALTER TABLE agent_routing ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_routing_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;

-- Create policies for user access
CREATE POLICY "Service role can access all agent routing data"
    ON agent_routing FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role can access all message routing logs"
    ON message_routing_logs FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role can access all agent messages"
    ON agent_messages FOR ALL
    TO service_role
    USING (true);

COMMIT;
