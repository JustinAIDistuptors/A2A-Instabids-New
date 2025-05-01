-- Supabase Schema Init – Required for HomeownerAgent MVP (Apr 2025)
-- Creates:
--   • projects           – core homeowner job tracking
--   • project_images     – uploaded photos (current + dream-style)
--   • memories           – long-term memory store for AI agents

CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  title TEXT,
  description TEXT,
  category TEXT,
  urgency TEXT,
  status TEXT DEFAULT 'draft',
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE project_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id),
  url TEXT NOT NULL,
  type TEXT CHECK (type IN ('current', 'desired'))
);

CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  key TEXT NOT NULL,
  value TEXT,
  updated_at TIMESTAMP DEFAULT now()
);

-- NOTE: A Supabase storage bucket named `project-images` must also be created
-- manually or via API for storing image uploads.
