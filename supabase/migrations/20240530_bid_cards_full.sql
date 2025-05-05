-- Enable UUIDs once per DB
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────── USERS TABLE (Assumed prerequisite) ───────────────
-- Ensure the users table exists with an 'id' column
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  -- other columns as needed
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────── PROJECTS TABLE (Assumed prerequisite) ───────────────
-- Ensure the projects table exists with an 'id' column
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  -- other columns as needed
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────── CONTRACTOR_PROFILES TABLE (Assumed prerequisite) ───────────────
-- Ensure the contractor_profiles table exists with 'user_id' and 'categories' columns
CREATE TABLE IF NOT EXISTS contractor_profiles (
  user_id UUID PRIMARY KEY,
  categories JSONB DEFAULT '{}'::JSONB,
  -- other columns as needed
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────── BID CARDS TABLE ───────────────
CREATE TABLE IF NOT EXISTS bid_cards (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  homeowner_id  UUID REFERENCES users(id)     ON DELETE CASCADE,
  project_id    UUID REFERENCES projects(id)  ON DELETE CASCADE,
  category      TEXT NOT NULL CHECK (category IN (
                  'repair','renovation','installation',
                  'maintenance','construction','other'
                )),
  job_type      TEXT NOT NULL,
  budget_min    NUMERIC,
  budget_max    NUMERIC,
  timeline      TEXT,
  location      TEXT,
  group_bidding BOOLEAN DEFAULT FALSE,
  details       JSONB  DEFAULT '{}'::JSONB,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────── FUNCTION TO UPDATE 'updated_at' ───────────────
-- Create the function only if it doesn't exist
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc WHERE proname = 'set_updated_at'
  ) THEN
    CREATE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
    BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
  END IF;
END;
$$;

-- ─────────────── TRIGGER TO UPDATE 'updated_at' ───────────────
-- Drop the trigger if it exists to avoid duplication
DROP TRIGGER IF EXISTS trg_bid_cards_updated ON bid_cards;

-- Create the trigger
CREATE TRIGGER trg_bid_cards_updated
  BEFORE UPDATE ON bid_cards
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────── ROW LEVEL SECURITY + INDEXES ───────────────
-- Enable row level security
ALTER TABLE bid_cards ENABLE ROW LEVEL SECURITY;

-- Homeowners full CRUD on own cards
DROP POLICY IF EXISTS "homeowner CRUD own bid_cards" ON bid_cards;
CREATE POLICY "homeowner CRUD own bid_cards"
  ON bid_cards
  USING  (auth.uid() = homeowner_id)
  WITH CHECK (auth.uid() = homeowner_id);

-- Contractors may SELECT cards in their categories
DROP POLICY IF EXISTS "contractor view matching bid_cards" ON bid_cards;
CREATE POLICY "contractor view matching bid_cards"
  ON bid_cards FOR SELECT
  USING (
    EXISTS (
      SELECT 1
      FROM contractor_profiles
      WHERE contractor_profiles.user_id = auth.uid()
        AND contractor_profiles.categories ? bid_cards.category
    )
  );

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_bid_cards_category     ON bid_cards(category);
CREATE INDEX IF NOT EXISTS idx_bid_cards_homeowner_id ON bid_cards(homeowner_id);
CREATE INDEX IF NOT EXISTS idx_bid_cards_project_id   ON bid_cards(project_id);