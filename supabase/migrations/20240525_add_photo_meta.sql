-- Enable pgvector once per DB
create extension if not exists vector;

alter table project_photos
  add column if not exists vision_labels jsonb,
  add column if not exists embed vector(256), -- Gemini 1.5 returns 256‑dim clip‑like
  add column if not exists confidence float;

-- index for similarity search
create index if not exists idx_project_photos_embed on project_photos using ivfflat (embed vector_cosine_ops);
--(No trigger needed – created_at remains unchanged.)
