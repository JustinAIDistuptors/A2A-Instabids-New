-- Bid Cards Schema Update (May 2025)
-- Creates:
--   • bid_cards - stores bid card information for projects

CREATE TABLE IF NOT EXISTS bid_cards (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  category TEXT NOT NULL,
  job_type TEXT,
  budget_range TEXT,
  timeline TEXT,
  group_bidding BOOLEAN DEFAULT FALSE,
  scope_json JSONB,
  photo_meta JSONB,
  ai_confidence FLOAT,
  status TEXT DEFAULT 'draft',
  created_at TIMESTAMP DEFAULT now()
);

-- Create index for faster lookups by project_id
CREATE INDEX IF NOT EXISTS bid_cards_project_id_idx ON bid_cards(project_id);

-- Add comment to document the table
COMMENT ON TABLE bid_cards IS 'Stores bid card information generated for projects';