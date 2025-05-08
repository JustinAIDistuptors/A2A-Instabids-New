-- Bid Cards Schema Update (May 2025)
-- Creates:
--   • bid_cards - stores bid card information for projects

CREATE TABLE IF NOT EXISTS bid_cards (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  homeowner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category TEXT NOT NULL CHECK (category IN ('repair', 'renovation', 'installation', 'maintenance', 'construction', 'other')),
  job_type TEXT,
  budget_range TEXT,
  budget_min DECIMAL(10, 2),
  budget_max DECIMAL(10, 2),
  timeline TEXT,
  group_bidding BOOLEAN DEFAULT FALSE,
  location TEXT,
  scope_json JSONB,
  photo_meta JSONB,
  ai_confidence FLOAT,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'closed', 'canceled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups by project_id
CREATE INDEX IF NOT EXISTS bid_cards_project_id_idx ON bid_cards(project_id);

-- Create index for faster lookups by homeowner_id
CREATE INDEX IF NOT EXISTS bid_cards_homeowner_id_idx ON bid_cards(homeowner_id);

-- Create index for category
CREATE INDEX IF NOT EXISTS bid_cards_category_idx ON bid_cards(category);

-- Create trigger for updated_at
CREATE TRIGGER set_bid_cards_timestamp
BEFORE UPDATE ON bid_cards
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Add comment to document the table
COMMENT ON TABLE bid_cards IS 'Stores bid card information generated for projects';
