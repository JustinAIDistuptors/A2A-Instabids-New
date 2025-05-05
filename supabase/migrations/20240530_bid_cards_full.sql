-- Enable UUIDs once per DB
create extension if not exists "uuid-ossp";

-- ─────────────── BID CARDS TABLE ───────────────
create table if not exists bid_cards (
  id            uuid primary key default uuid_generate_v4(),
  homeowner_id  uuid references users(id)     on delete cascade,
  project_id    uuid references projects(id)  on delete cascade,
  category      text not null check (category in (
                  'repair','renovation','installation',
                  'maintenance','construction','other'
                )),
  job_type      text not null,
  budget_min    numeric,
  budget_max    numeric,
  timeline      text,
  location      text,
  group_bidding boolean default false,
  details       jsonb  default '{}'::jsonb,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- keep updated_at fresh
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now(); return new;
end $$;

create trigger trg_bid_cards_updated
  before update on bid_cards
  for each row execute procedure set_updated_at();

-- ─────────────── RLS + INDEXES ───────────────
alter table bid_cards enable row level security;

-- homeowners full CRUD on own cards
create policy "homeowner CRUD own bid_cards"
  on bid_cards
  using  (auth.uid() = homeowner_id)
  with check (auth.uid() = homeowner_id);

-- contractors may SELECT cards in their categories
create policy "contractor view matching bid_cards"
  on bid_cards for select
  using (
    exists (
      select 1
      from contractor_profiles
      where contractor_profiles.user_id = auth.uid()
        and contractor_profiles.categories ? bid_cards.category
    )
  );

create index if not exists idx_bid_cards_category     on bid_cards(category);
create index if not exists idx_bid_cards_homeowner_id on bid_cards(homeowner_id);
create index if not exists idx_bid_cards_project_id   on bid_cards(project_id);