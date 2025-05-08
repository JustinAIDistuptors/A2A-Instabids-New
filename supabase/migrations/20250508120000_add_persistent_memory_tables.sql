-- Migration: 20250508120000_add_persistent_memory_tables.sql
-- Description: Adds database tables for persistent memory storage
-- Part of sprint/24-slot-memory-integration

-- Run inside a transaction for atomicity
BEGIN;

-- Add vector extension if it doesn't exist (for future vector storage compatibility)
CREATE EXTENSION IF NOT EXISTS vector;

-- Table for storing the complete memory state per user
CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,
    memory_data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT user_memories_user_id_key UNIQUE (user_id)
);

-- Table for detailed interaction history
CREATE TABLE IF NOT EXISTS user_memory_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    interaction_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_memories(user_id) ON DELETE CASCADE
);

-- Index on interaction type for faster filtering
CREATE INDEX IF NOT EXISTS user_memory_interactions_type_idx ON user_memory_interactions(interaction_type);

-- Table for extracted user preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    preference_key TEXT NOT NULL,
    preference_value JSONB NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.5,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES user_memories(user_id) ON DELETE CASCADE,
    CONSTRAINT user_preferences_user_pref_key UNIQUE (user_id, preference_key)
);

-- Enable Row Level Security
ALTER TABLE user_memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_memory_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create policies for user access
CREATE POLICY "Users can only access their own memory data"
    ON user_memories FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users can only access their own interaction data"
    ON user_memory_interactions FOR ALL
    USING (auth.uid()::text = user_id);

CREATE POLICY "Users can only access their own preferences"
    ON user_preferences FOR ALL
    USING (auth.uid()::text = user_id);

-- Add service role policies for system access
CREATE POLICY "Service role can access all memory data"
    ON user_memories FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role can access all interaction data"
    ON user_memory_interactions FOR ALL
    TO service_role
    USING (true);

CREATE POLICY "Service role can access all preferences"
    ON user_preferences FOR ALL
    TO service_role
    USING (true);

COMMIT;