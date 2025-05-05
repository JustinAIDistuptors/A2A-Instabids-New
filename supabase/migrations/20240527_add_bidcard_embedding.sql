-- Enable pgvector once per DB
create extension if not exists vector;

alter table bid_cards
  add column if not exists job_embed vector(384); -- Gemini text-embedding-004 size

-- Create IVFFLAT index for ANN search
-- ivfflat requires training the index after initial population.
-- The number of lists is typically sqrt(N) for up to 1M rows, N/1000 otherwise.
-- Adjust 'lists = 100' based on expected bid_cards table size.
create index if not exists idx_bid_cards_job_embed
  on bid_cards using ivfflat (job_embed vector_cosine_ops) with (lists = 100);
