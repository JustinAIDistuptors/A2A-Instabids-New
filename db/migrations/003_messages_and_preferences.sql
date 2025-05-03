-- Messages and User Preferences Schema Update (May 2025)
-- Creates:
--   • messages - stores conversation messages between homeowners and agents
--   • user_preferences - stores long-term user preferences
-- Adds:
--   • Row Level Security (RLS) policies for data access control

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Messages table for homeowner-agent conversations
CREATE TABLE IF NOT EXISTS messages (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
  role        TEXT CHECK (role IN ('homeowner','agent')),
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Index for faster message lookups by project
CREATE INDEX IF NOT EXISTS idx_messages_project ON messages(project_id);

-- User preferences table for long-term preference storage
CREATE TABLE IF NOT EXISTS user_preferences (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  pref_key    TEXT,
  pref_value  JSONB,
  confidence  REAL DEFAULT 0.5,
  updated_at  TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, pref_key)
);

-- Enable Row Level Security
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Homeowners can only see messages for their own projects
CREATE POLICY "select own messages" ON messages
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects WHERE user_id = auth.uid()
    )
  );

-- RLS Policy: Homeowners can only insert messages for their own projects
CREATE POLICY "insert own messages" ON messages
  FOR INSERT WITH CHECK (
    project_id IN (
      SELECT id FROM projects WHERE user_id = auth.uid()
    ) AND role = 'homeowner'
  );

-- RLS Policy: Users can only see their own preferences
CREATE POLICY "select own preferences" ON user_preferences
  FOR SELECT USING (user_id = auth.uid());

-- RLS Policy: Users can only insert/update their own preferences
CREATE POLICY "manage own preferences" ON user_preferences
  FOR ALL USING (user_id = auth.uid());

-- Note: The service role will need to be used for agent messages and system preference updates
COMMENT ON TABLE messages IS 'Conversation messages between homeowners and AI agents';
COMMENT ON TABLE user_preferences IS 'Long-term user preferences with confidence scores';