-- Enable uuid & citext once per DB
create extension if not exists "uuid-ossp";
create extension if not exists citext;

-- Prospect contractors we scraped but who have NOT signed-up yet
create table if not exists prospect_contractors (
  id               uuid primary key default uuid_generate_v4(),
  place_id         text, -- Added based on S6 agent logic
  business_name    text, -- Renamed from 'name' for clarity
  phone            citext, -- Use citext for case-insensitive phone matching
  email            citext, -- Use citext for case-insensitive email matching
  website_url      text,
  service_categories text[] default '{}',
  lat              numeric,      -- optional geo (WGS-84)
  lon              numeric,
  source           text,         -- 'google', 'bing', 'manual', etc.
  raw_json         jsonb,       -- Store raw Google Places data
  created_at       timestamptz default now(),
  updated_at       timestamptz default now() -- Add updated_at tracking
);

-- Ensure place_id is unique if it comes from Google Places
create unique index if not exists uq_prospect_place_id on prospect_contractors(place_id) where place_id is not null;
-- Unique index on phone (case-insensitive due to citext)
create unique index if not exists uq_prospect_phone on prospect_contractors(phone) where phone is not null;
-- Unique index on email (case-insensitive due to citext)
create unique index if not exists uq_prospect_email on prospect_contractors(email) where email is not null;

-- Trigger for updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists prospect_contractors_update_updated_at on prospect_contractors;
create trigger prospect_contractors_update_updated_at
before update on prospect_contractors
for each row
execute function update_updated_at_column();

-- An invite = one attempt to get a contractor/prospect to bid
create type invite_status as enum ('queued','sent','responded','failed','opted_out');

create table if not exists contractor_invites (
  id                uuid primary key default uuid_generate_v4(),
  bid_card_id       uuid references bid_cards(id) on delete cascade not null,
  contractor_id     uuid references auth.users(id), -- Reference actual users table
  prospect_id       uuid references prospect_contractors(id),
  channel           text check (channel in ('sms','email','internal')), -- Adjusted channels based on agent logic
  status            invite_status default 'queued' not null,
  attempts          int    default 0 not null,
  last_attempt_at   timestamptz,
  response_payload  jsonb,           -- e.g. Twilio SID, SendGrid Ref, etc.
  created_at        timestamptz default now() not null,
  updated_at        timestamptz default now() not null, -- Add updated_at tracking
  -- Ensure either contractor_id or prospect_id is set, but not both
  constraint chk_invite_target check (
    (contractor_id is not null and prospect_id is null) or 
    (contractor_id is null and prospect_id is not null)
  )
);

create index if not exists idx_contractor_invites_bid_card_id on contractor_invites(bid_card_id);
create index if not exists idx_contractor_invites_status on contractor_invites(status);

-- Trigger for updated_at timestamp
drop trigger if exists contractor_invites_update_updated_at on contractor_invites;
create trigger contractor_invites_update_updated_at
before update on contractor_invites
for each row
execute function update_updated_at_column();

-- allow RLS later (start with disabled for ease of development if needed)
alter table prospect_contractors enable row level security;
alter table prospect_contractors force row level security;

alter table contractor_invites enable row level security;
alter table contractor_invites force row level security;

-- Policies: Start with service_role having full access
drop policy if exists "system can manage prospects" on prospect_contractors;
create policy "system can manage prospects"
  on prospect_contractors for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

drop policy if exists "system can manage invites" on contractor_invites;
create policy "system can manage invites"
  on contractor_invites for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

-- NOTE: RLS for users accessing their own invites/prospects to be added later.